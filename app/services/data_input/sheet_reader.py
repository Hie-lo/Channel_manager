"""
سرویس خواندن Google Sheet چند صفحه‌ای با پشتیبانی از اسمارت‌مچ و ویزارد
"""

import re
from pathlib import Path
from dataclasses import dataclass

import gspread
from google.oauth2.service_account import Credentials

from app.business.config import (
    BusinessConfig,
    SubCategory,
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

    except Exception as e:
        error_str = str(e)
        if "403" in error_str or "PERMISSION_DENIED" in error_str:
            return SheetConnectionResult(
                success=False,
                error_message="دسترسی به شیت وجود ندارد. لطفاً ایمیل ربات را به عنوان 'Editor' اضافه کنید.",
            )
        return SheetConnectionResult(
            success=False,
            error_message=f"خطا در اتصال: {error_str[:150]}",
        )


def read_google_sheet(
    sheet_id: str,
    business_config: BusinessConfig,
    worksheet_name: str | None = None,
    custom_map: dict[str, int] = None,
    ignored_fields: list[str] = None,
    custom_maps: dict = None,  # 💡 اضافه شد جهت پشتیبانی از نام جمع
) -> ExcelReadResult:
    """
    خواندن کل Google Sheet با پشتیبانی کامل از مپینگ سفارشی
    """
    result = ExcelReadResult()
    ignored = ignored_fields or []

    # استفاده از هر کدا‌م که ارسال شده باشد
    effective_map = custom_map or custom_maps

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

            if sheet_name in ("راهنما", "info", "Sheet1", "Sheet2", "Sheet3"):
                continue

            subcategory = get_subcategory_by_worksheet(business_config.key, sheet_name)
            
            if not subcategory and business_config.key == "other":
                if business_config.sub_categories:
                    subcategory = business_config.sub_categories[0]
                    log.info(f"💡 G-Sheet '{sheet_name}' برای کسب‌وکار سایر متصل شد.")

            if not subcategory:
                log.warning(f"G-Sheet '{sheet_name}' متعلق به هیچ زیردسته نیست")
                continue

            # پاس دادن effective_map
            ws_result = _read_worksheet(worksheet, subcategory, effective_map, ignored)
            result.worksheets.append(ws_result)

        log.info(f"شیت خونده شد: {len(result.worksheets)} sheet، {result.valid_rows} محصول معتبر")
        return result

    except Exception as e:
        log.error(f"خطا در خواندن شیت {sheet_id}: {e}", exc_info=True)
        ws_result = WorksheetReadResult(worksheet_name="")
        ws_result.errors.append(RowError(row_number=0, field="general", message=f"خطا: {str(e)[:200]}"))
        result.worksheets.append(ws_result)
        return result


def _read_worksheet(
    worksheet, 
    subcategory: SubCategory,
    custom_map: dict = None,
    ignored_fields: list = None,
) -> WorksheetReadResult:
    """خواندن یک worksheet با پشتیبانی کامل از پارامترهای ویزارد"""
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

    ignored = ignored_fields or []

    if not custom_map:
        field_map = _build_field_map_sheet(subcategory, headers)
    else:
        field_map = custom_map

    missing_required = _check_missing_required_sheet(subcategory, field_map, ignored)
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

        product_data, row_errors = _parse_sheet_row(
            row=row,
            field_map=field_map,
            subcategory=subcategory,
            row_number=row_index,
            worksheet_name=worksheet.title,
            ignored_fields=ignored,
        )

        if row_errors:
            result.errors.extend(row_errors)
        else:
            result.products.append(product_data)
            result.valid_rows += 1

    return result


def _build_field_map_sheet(subcategory: SubCategory, headers: list[str]) -> dict[str, int]:
    field_map = {}
    normalized_headers = [str(h).strip().lower() for h in headers]

    for field in subcategory.fields:
        target_name = field.excel_column.strip().lower()
        if target_name in normalized_headers:
            field_map[field.key] = normalized_headers.index(target_name)
            continue

        found = False
        if hasattr(field, 'aliases') and field.aliases:
            for alias in field.aliases:
                alias_clean = alias.strip().lower()
                if alias_clean in normalized_headers:
                    field_map[field.key] = normalized_headers.index(alias_clean)
                    found = True
                    break
        if found: continue

        for idx, header in enumerate(normalized_headers):
            if target_name in header or header in target_name:
                field_map[field.key] = idx
                break

    return field_map


def _check_missing_required_sheet(subcategory: SubCategory, field_map: dict, ignored_fields: list) -> list[str]:
    missing = []
    ignored = ignored_fields or []
    for field in subcategory.fields:
        if field.required and field.key not in field_map and field.key not in ignored:
            missing.append(field.excel_column)
    return missing


def _parse_sheet_row(row, field_map, subcategory, row_number, worksheet_name, ignored_fields: list = None):
    product_data = {"row_number": row_number, "specs": {}}
    errors = []
    ignored = ignored_fields or []
    import uuid

    for field in subcategory.fields:
        if field.key in ignored:
            if field.key == "sku": parsed_value = str(uuid.uuid4())[:8].upper()
            elif field.key == "price": parsed_value = 0
            elif field.key == "stock": parsed_value = 0
            elif field.key == "product_name": parsed_value = "محصول بدون نام"
            else: parsed_value = ""
            
            if field.key in ("sku", "product_name", "price", "stock", "description", "image_url"):
                product_data[field.key] = parsed_value
            else:
                product_data["specs"][field.key] = parsed_value
            continue

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