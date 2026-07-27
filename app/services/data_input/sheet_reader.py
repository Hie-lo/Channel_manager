"""
سرویس خواندن Google Sheet چند صفحه‌ای
"""

import re
from pathlib import Path
from dataclasses import dataclass

import gspread
from google.oauth2.service_account import Credentials

from app.business.config import (
    BusinessConfig,
    get_subcategory_by_worksheet,
)
from app.config import settings
from app.services.data_input.excel_reader import (
    ExcelReadResult,
    WorksheetReadResult,
    RowError,
    _parse_field_value,
    _clean_value,
)
from app.utils.logger import log


GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


@dataclass
class SheetConnectionResult:
    success: bool
    sheet_id: str = ""
    sheet_title: str = ""
    worksheet_titles: list = None
    error_message: str = ""

    def __post_init__(self):
        if self.worksheet_titles is None:
            self.worksheet_titles = []


def extract_sheet_id_from_url(url: str) -> str | None:
    """استخراج ID شیت از URL"""
    if not url:
        return None

    url = url.strip()

    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    if match:
        return match.group(1)

    if re.match(r"^[a-zA-Z0-9-_]+$", url) and len(url) > 20:
        return url

    return None


def _get_gspread_client() -> gspread.Client | None:
    """ساخت client"""
    try:
        creds_path = Path(settings.GOOGLE_CREDENTIALS_FILE)

        if not creds_path.exists():
            log.error(f"فایل credentials پیدا نشد: {creds_path}")
            return None

        creds = Credentials.from_service_account_file(
            str(creds_path),
            scopes=GOOGLE_SCOPES,
        )

        client = gspread.authorize(creds)
        return client

    except Exception as e:
        log.error(f"خطا در ساخت gspread client: {e}", exc_info=True)
        return None


def test_sheet_connection(sheet_url_or_id: str) -> SheetConnectionResult:
    """تست اتصال به شیت"""
    sheet_id = extract_sheet_id_from_url(sheet_url_or_id)

    if not sheet_id:
        return SheetConnectionResult(
            success=False,
            error_message="آدرس Google Sheet نامعتبر است",
        )

    client = _get_gspread_client()
    if not client:
        return SheetConnectionResult(
            success=False,
            error_message="خطا در اتصال به Google. لطفاً با پشتیبانی تماس بگیرید",
        )

    try:
        spreadsheet = client.open_by_key(sheet_id)

        worksheet_titles = [ws.title for ws in spreadsheet.worksheets()]

        return SheetConnectionResult(
            success=True,
            sheet_id=sheet_id,
            sheet_title=spreadsheet.title,
            worksheet_titles=worksheet_titles,
        )

    except gspread.SpreadsheetNotFound:
        return SheetConnectionResult(
            success=False,
            error_message=(
                "شیت پیدا نشد یا دسترسی ندارید.\n"
                "لطفاً مطمئن شوید ایمیل ربات را با دسترسی 'Editor' اضافه کرده‌اید."
            ),
        )
    except gspread.APIError as e:
        error_str = str(e)
        if "403" in error_str or "PERMISSION_DENIED" in error_str:
            return SheetConnectionResult(
                success=False,
                error_message=(
                    "دسترسی به شیت وجود ندارد.\n"
                    "لطفاً ایمیل ربات را به عنوان 'Editor' اضافه کنید."
                ),
            )
        return SheetConnectionResult(
            success=False,
            error_message=f"خطای Google API: {error_str[:100]}",
        )
    except Exception as e:
        log.error(f"خطا در تست اتصال: {e}", exc_info=True)
        return SheetConnectionResult(
            success=False,
            error_message=f"خطای غیرمنتظره: {str(e)[:100]}",
        )


def read_google_sheet(
    sheet_id: str,
    business_config: BusinessConfig,
    worksheet_name: str | None = None,  # حالا نادیده گرفته می‌شه، همه sheet ها خونده میشن
) -> ExcelReadResult:
    """
    خواندن کل Google Sheet (همه worksheet ها)
    """
    result = ExcelReadResult()

    client = _get_gspread_client()
    if not client:
        ws_result = WorksheetReadResult(worksheet_name="")
        ws_result.errors.append(RowError(
            row_number=0,
            field="connection",
            message="خطا در اتصال به Google",
        ))
        result.worksheets.append(ws_result)
        return result

    try:
        spreadsheet = client.open_by_key(sheet_id)

        for worksheet in spreadsheet.worksheets():
            sheet_name = worksheet.title

            # sheet راهنما رو رد کن
            if sheet_name in ("راهنما", "info"):
                continue

            # پیدا کردن زیردسته
            subcategory = get_subcategory_by_worksheet(business_config.key, sheet_name)
            if not subcategory:
                log.warning(f"Sheet '{sheet_name}' متعلق به هیچ زیردسته نیست")
                continue

            # خواندن
            ws_result = _read_worksheet(worksheet, subcategory)
            result.worksheets.append(ws_result)

        log.info(
            f"شیت خونده شد: {len(result.worksheets)} sheet، "
            f"{result.valid_rows} محصول معتبر"
        )

        return result

    except Exception as e:
        log.error(f"خطا در خواندن شیت {sheet_id}: {e}", exc_info=True)
        ws_result = WorksheetReadResult(worksheet_name="")
        ws_result.errors.append(RowError(
            row_number=0,
            field="general",
            message=f"خطا: {str(e)[:200]}",
        ))
        result.worksheets.append(ws_result)
        return result


def _read_worksheet(worksheet, subcategory) -> WorksheetReadResult:
    """خواندن یک worksheet"""
    result = WorksheetReadResult(
        worksheet_name=worksheet.title,
        subcategory_key=subcategory.key,
    )

    all_values = worksheet.get_all_values()

    if not all_values:
        return result

    headers = [str(cell).strip() for cell in all_values[0]]

    if not any(headers):
        return result

    field_map = _build_field_map(subcategory, headers)

    missing_required = _check_missing_required(subcategory, field_map)
    if missing_required:
        for field_name in missing_required:
            result.errors.append(RowError(
                row_number=1,
                field=field_name,
                message=f"ستون '{field_name}' در sheet '{worksheet.title}' پیدا نشد",
                worksheet=worksheet.title,
            ))
        return result

    for row_index, row in enumerate(all_values[1:], start=2):
        if all(cell is None or str(cell).strip() == "" for cell in row):
            continue

        result.total_rows += 1

        product_data, row_errors = _parse_row(
            row=row,
            field_map=field_map,
            subcategory=subcategory,
            row_number=row_index,
            worksheet_name=worksheet.title,
        )

        if row_errors:
            result.errors.extend(row_errors)
        else:
            result.products.append(product_data)
            result.valid_rows += 1

    return result


def _build_field_map(subcategory, headers: list[str]) -> dict[str, int]:
    field_map = {}
    for field in subcategory.fields:
        try:
            col_index = headers.index(field.excel_column)
            field_map[field.key] = col_index
        except ValueError:
            pass
    return field_map


def _check_missing_required(subcategory, field_map) -> list[str]:
    missing = []
    for field in subcategory.fields:
        if field.required and field.key not in field_map:
            missing.append(field.excel_column)
    return missing


def _parse_row(row, field_map, subcategory, row_number, worksheet_name):
    """پارس ردیف"""
    product_data = {"row_number": row_number, "specs": {}}
    errors = []

    for field in subcategory.fields:
        if field.key not in field_map:
            continue

        col_index = field_map[field.key]
        raw_value = row[col_index] if col_index < len(row) else None
        value = _clean_value(raw_value)

        if field.required and (value is None or value == ""):
            errors.append(RowError(
                row_number=row_number,
                field=field.excel_column,
                message=f"مقدار '{field.excel_column}' خالی است",
                worksheet=worksheet_name,
            ))
            continue

        parsed_value, parse_error = _parse_field_value(field.key, value, field.excel_column)

        if parse_error:
            errors.append(RowError(
                row_number=row_number,
                field=field.excel_column,
                message=parse_error,
                worksheet=worksheet_name,
            ))
            continue

        if field.key in ("sku", "product_name", "price", "stock", "description", "image_url"):
            product_data[field.key] = parsed_value
        else:
            product_data["specs"][field.key] = parsed_value

    return product_data, errors