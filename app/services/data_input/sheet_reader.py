"""
سرویس خواندن Google Sheet
"""

import re
from pathlib import Path
from dataclasses import dataclass, field

import gspread
from google.oauth2.service_account import Credentials

from app.business.config import BusinessConfig
from app.config import settings
from app.services.data_input.excel_reader import (
    ExcelReadResult,
    RowError,
    _parse_field_value,
    _clean_value,
)
from app.utils.logger import log


# اسکوپ‌های لازم برای Google Sheets و Drive
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


@dataclass
class SheetConnectionResult:
    """نتیجه تست اتصال به شیت"""
    success: bool
    sheet_id: str = ""
    sheet_title: str = ""
    worksheet_title: str = ""
    row_count: int = 0
    error_message: str = ""


def extract_sheet_id_from_url(url: str) -> str | None:
    """
    استخراج ID شیت از URL
    مثال: https://docs.google.com/spreadsheets/d/1abc.../edit → 1abc...
    """
    if not url:
        return None

    url = url.strip()

    # الگوی URL معمولی
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    if match:
        return match.group(1)

    # اگه فقط ID بود
    if re.match(r"^[a-zA-Z0-9-_]+$", url) and len(url) > 20:
        return url

    return None


def _get_gspread_client() -> gspread.Client | None:
    """ساخت client برای اتصال به Google"""
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


def test_sheet_connection(
    sheet_url_or_id: str,
    worksheet_name: str | None = None,
) -> SheetConnectionResult:
    """
    تست اتصال به یک شیت
    برای وقتی مشتری می‌خواد شیت جدید اضافه کنه
    """
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
        # باز کردن شیت
        spreadsheet = client.open_by_key(sheet_id)

        # انتخاب worksheet
        if worksheet_name:
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
            except gspread.WorksheetNotFound:
                return SheetConnectionResult(
                    success=False,
                    sheet_id=sheet_id,
                    sheet_title=spreadsheet.title,
                    error_message=f"صفحه '{worksheet_name}' پیدا نشد",
                )
        else:
            worksheet = spreadsheet.sheet1

        # شمارش ردیف‌ها
        row_count = worksheet.row_count

        return SheetConnectionResult(
            success=True,
            sheet_id=sheet_id,
            sheet_title=spreadsheet.title,
            worksheet_title=worksheet.title,
            row_count=row_count,
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
        log.error(f"خطا در تست اتصال شیت {sheet_id}: {e}", exc_info=True)
        return SheetConnectionResult(
            success=False,
            error_message=f"خطای غیرمنتظره: {str(e)[:100]}",
        )


def read_google_sheet(
    sheet_id: str,
    business_config: BusinessConfig,
    worksheet_name: str | None = None,
) -> ExcelReadResult:
    """
    خواندن Google Sheet و برگرداندن نتیجه به شکل ExcelReadResult
    (سازگار با سیستم موجود)
    """
    result = ExcelReadResult()

    client = _get_gspread_client()
    if not client:
        result.errors.append(RowError(
            row_number=0,
            field="connection",
            message="خطا در اتصال به Google",
        ))
        return result

    try:
        spreadsheet = client.open_by_key(sheet_id)

        if worksheet_name:
            worksheet = spreadsheet.worksheet(worksheet_name)
        else:
            worksheet = spreadsheet.sheet1

        # خواندن همه ردیف‌ها به صورت لیست از لیست
        all_values = worksheet.get_all_values()

        if not all_values:
            result.errors.append(RowError(
                row_number=0,
                field="content",
                message="شیت خالی است",
            ))
            return result

        # ردیف اول = هدر
        headers = [str(cell).strip() for cell in all_values[0]]

        if not any(headers):
            result.errors.append(RowError(
                row_number=1,
                field="header",
                message="ردیف اول (نام ستون‌ها) خالی است",
            ))
            return result

        # نگاشت
        field_map = _build_field_map_sheet(business_config, headers)

        # چک فیلدهای اجباری
        missing_required = _check_missing_required_sheet(business_config, field_map)
        if missing_required:
            for field_name in missing_required:
                result.errors.append(RowError(
                    row_number=1,
                    field=field_name,
                    message=f"ستون '{field_name}' در شیت پیدا نشد (اجباری)",
                ))
            return result

        # پردازش ردیف‌های داده (از ردیف ۲)
        for row_index, row in enumerate(all_values[1:], start=2):
            # چک ردیف خالی
            if all(cell is None or str(cell).strip() == "" for cell in row):
                continue

            result.total_rows += 1

            product_data, row_errors = _parse_sheet_row(
                row=row,
                field_map=field_map,
                business_config=business_config,
                row_number=row_index,
            )

            if row_errors:
                result.errors.extend(row_errors)
            else:
                result.products.append(product_data)
                result.valid_rows += 1

        log.info(
            f"شیت خونده شد: {result.total_rows} سطر، "
            f"{result.valid_rows} معتبر، {len(result.errors)} خطا"
        )

        return result

    except gspread.SpreadsheetNotFound:
        result.errors.append(RowError(
            row_number=0,
            field="sheet",
            message="شیت پیدا نشد",
        ))
        return result
    except Exception as e:
        log.error(f"خطا در خواندن شیت {sheet_id}: {e}", exc_info=True)
        result.errors.append(RowError(
            row_number=0,
            field="general",
            message=f"خطا: {str(e)[:200]}",
        ))
        return result


def _build_field_map_sheet(
    business_config: BusinessConfig,
    headers: list[str],
) -> dict[str, int]:
    """نگاشت فیلدها به شماره ستون"""
    field_map = {}
    for field in business_config.fields:
        try:
            col_index = headers.index(field.excel_column)
            field_map[field.key] = col_index
        except ValueError:
            pass
    return field_map


def _check_missing_required_sheet(
    business_config: BusinessConfig,
    field_map: dict[str, int],
) -> list[str]:
    """چک فیلدهای اجباری"""
    missing = []
    for field in business_config.fields:
        if field.required and field.key not in field_map:
            missing.append(field.excel_column)
    return missing


def _parse_sheet_row(
    row: list,
    field_map: dict[str, int],
    business_config: BusinessConfig,
    row_number: int,
) -> tuple[dict, list[RowError]]:
    """پارس یک ردیف از شیت"""
    product_data = {"row_number": row_number, "specs": {}}
    errors = []

    for field in business_config.fields:
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
            ))
            continue

        parsed_value, parse_error = _parse_field_value(field.key, value, field.excel_column)

        if parse_error:
            errors.append(RowError(
                row_number=row_number,
                field=field.excel_column,
                message=parse_error,
            ))
            continue

        if field.key in ("sku", "product_name", "price", "stock", "description", "image_url"):
            product_data[field.key] = parsed_value
        else:
            product_data["specs"][field.key] = parsed_value

    return product_data, errors
