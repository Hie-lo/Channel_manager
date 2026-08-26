"""
سرویس خواندن فایل اکسل چند شیتی (با پشتیبانی از Smart Matcher و ویزارد مپینگ)
"""

from pathlib import Path
from dataclasses import dataclass, field
from openpyxl import load_workbook
import uuid

from app.business.config import (
    BusinessConfig,
    SubCategory,
    get_subcategory_by_worksheet,
)
from app.utils.logger import log


@dataclass
class RowError:
    row_number: int
    field: str
    message: str
    worksheet: str = ""
    # 💡 افزودن فیلد برای تعیین نوع خطا تا سیستم ویزارد بتواند آن را تشخیص دهد
    error_type: str = "validation"  # می‌تواند "missing_column" یا "validation" باشد


@dataclass
class WorksheetReadResult:
    worksheet_name: str
    subcategory_key: str = ""
    products: list[dict] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)
    total_rows: int = 0
    valid_rows: int = 0


@dataclass
class ExcelReadResult:
    worksheets: list[WorksheetReadResult] = field(default_factory=list)

    @property
    def total_products(self) -> int:
        return sum(len(ws.products) for ws in self.worksheets)

    @property
    def total_rows(self) -> int:
        return sum(ws.total_rows for ws in self.worksheets)

    @property
    def valid_rows(self) -> int:
        return sum(ws.valid_rows for ws in self.worksheets)

    @property
    def all_errors(self) -> list[RowError]:
        errors = []
        for ws in self.worksheets:
            errors.extend(ws.errors)
        return errors

    @property
    def has_errors(self) -> bool:
        return len(self.all_errors) > 0

    @property
    def is_empty(self) -> bool:
        return self.valid_rows == 0

    @property
    def all_products(self) -> list[dict]:
        products = []
        for ws in self.worksheets:
            for p in ws.products:
                p["sub_category_key"] = ws.subcategory_key
                products.append(p)
        return products

    # 💡 این پراپرتی را اضافه کردیم تا هندلرِ ویزارد بتواند فیلدهای گمشده را بیرون بکشد
    @property
    def missing_mapping_data(self) -> list[str]:
        missing_fields = []
        for err in self.all_errors:
            if err.error_type == "missing_column":
                missing_fields.append(err.field)
        return list(set(missing_fields)) # حذف موارد تکراری


def read_excel_file(
    file_path: str | Path,
    business_config: BusinessConfig,
    custom_map: dict[str, int] = None,
    ignored_fields: list[str] = None,
) -> ExcelReadResult:
    """
    خواندن فایل اکسل و تبدیل به لیست محصولات
    """
    result = ExcelReadResult()
    ignored = ignored_fields or []

    try:
        workbook = load_workbook(filename=file_path, data_only=True)
    except Exception as e:
        log.error(f"خطا در باز کردن فایل اکسل: {e}")
        ws_result = WorksheetReadResult(worksheet_name="")
        ws_result.errors.append(RowError(
            row_number=0,
            field="file",
            message=f"فایل قابل خواندن نیست: {str(e)}",
        ))
        result.worksheets.append(ws_result)
        return result

    # پردازش هر sheet
    for sheet_name in workbook.sheetnames:
        # sheet راهنما یا خالی رو نادیده بگیر
        if sheet_name in ("راهنما", "info", "Sheet1", "Sheet2", "Sheet3"):
            continue

        # پیدا کردن زیردسته متناظر
        subcategory = get_subcategory_by_worksheet(business_config.key, sheet_name)
        
        # انعطاف‌پذیری برای کسب‌وکار "سایر" (other)
        if not subcategory and business_config.key == "other":
            if business_config.sub_categories:
                subcategory = business_config.sub_categories[0]
                log.info(f"💡 Sheet '{sheet_name}' برای کسب‌وکار سایر به زیردسته پیش‌فرض متصل شد.")

        if not subcategory:
            log.warning(f"Sheet '{sheet_name}' متعلق به هیچ زیردسته نیست، نادیده گرفته می‌شود")
            continue

        sheet = workbook[sheet_name]
        ws_result = _read_worksheet(sheet, subcategory, custom_map, ignored)
        result.worksheets.append(ws_result)

    log.info(
        f"فایل اکسل خونده شد: {len(result.worksheets)} sheet, "
        f"{result.total_rows} سطر، {result.valid_rows} معتبر"
    )

    return result


def _read_worksheet(
    sheet,
    subcategory: SubCategory,
    custom_map: dict = None,
    ignored_fields: list = None,
) -> WorksheetReadResult:
    """خواندن یک sheet خاص با استفاده از تعریف subcategory"""
    result = WorksheetReadResult(
        worksheet_name=sheet.title,
        subcategory_key=subcategory.key,
    )

    # خواندن هدر
    headers = []
    for cell in sheet[1]:
        if cell.value:
            headers.append(str(cell.value).strip())
        else:
            headers.append("")

    if not any(headers):
        return result

    ignored = ignored_fields or []

    if not custom_map:
        field_map = _build_field_map(subcategory, headers)
    else:
        field_map = custom_map

    # چک فیلدهای اجباری
    missing_required = _check_missing_required(subcategory, field_map, ignored)
    if missing_required:
        for field_name in missing_required:
            result.errors.append(RowError(
                row_number=1,
                field=field_name,
                message=f"ستون '{field_name}' در sheet '{sheet.title}' پیدا نشد (اجباری)",
                worksheet=sheet.title,
            ))
        return result

    # خواندن ردیف‌های داده
    for row_index, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        if all(cell is None or str(cell).strip() == "" for cell in row):
            continue

        result.total_rows += 1

        product_data, row_errors = _parse_row(
            row=row,
            field_map=field_map,
            subcategory=subcategory,
            row_number=row_index,
            worksheet_name=sheet.title,
            ignored_fields=ignored,
        )

        if row_errors:
            result.errors.extend(row_errors)
        else:
            result.products.append(product_data)
            result.valid_rows += 1

    return result


def _build_field_map(subcategory: SubCategory, headers: list[str]) -> dict[str, int]:
    """نگاشت هوشمند فیلدها برای اکسل"""
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
        if found:
            continue

        for idx, header in enumerate(normalized_headers):
            if target_name in header or header in target_name:
                field_map[field.key] = idx
                break

    return field_map

def _check_missing_required(subcategory: SubCategory, field_map: dict, ignored_fields: list) -> list[str]:
    """چک کن فیلدهای اجباری جا نمونده باشن"""
    missing = []
    ignored = ignored_fields or []
    for field in subcategory.fields:
        if field.required and field.key not in field_map and field.key not in ignored:
            missing.append(field.excel_column)
    return missing

def _parse_row(
    row: tuple,
    field_map: dict[str, int],
    subcategory: SubCategory,
    row_number: int,
    worksheet_name: str,
    ignored_fields: list = None,
) -> tuple[dict, list[RowError]]:
    """پارس یک ردیف"""
    product_data = {"row_number": row_number, "specs": {}}
    errors = []
    ignored = ignored_fields or []

    for field in subcategory.fields:
        if field.key in ignored:
            if field.key == "sku":
                parsed_value = str(uuid.uuid4())[:8].upper()
            elif field.key == "price":
                parsed_value = 0
            elif field.key == "stock":
                parsed_value = 0
            elif field.key == "product_name":
                parsed_value = "محصول بدون نام"
            else:
                parsed_value = ""

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


def _clean_value(value):
    """پاکسازی مقدار سلول"""
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    return value


def _parse_field_value(field_key: str, value, column_name: str) -> tuple:
    """اعتبارسنجی و تبدیل نوع"""
    if value is None or value == "":
        return None, None

    if field_key == "price":
        try:
            if isinstance(value, str):
                value = value.replace(",", "").replace("،", "").strip()
            price = int(float(value))
            if price < 0:
                return None, "قیمت نمی‌تواند منفی باشد"
            return price, None
        except (ValueError, TypeError):
            return None, f"قیمت باید عدد باشد (مقدار: {value})"

    if field_key == "stock":
        try:
            stock = int(float(value))
            if stock < 0:
                return None, "موجودی نمی‌تواند منفی باشد"
            return stock, None
        except (ValueError, TypeError):
            return None, f"موجودی باید عدد باشد (مقدار: {value})"

    if field_key == "sku":
        sku = str(value).strip()
        if not sku:
            return None, "کد محصول نمی‌تواند خالی باشد"
        if len(sku) > 80:
            return None, "کد محصول نباید بیش از ۸۰ کاراکتر باشد"
        return sku, None

    if field_key == "product_name":
        name = str(value).strip()
        if not name:
            return None, "نام محصول نمی‌تواند خالی باشد"
        if len(name) > 250:
            return None, "نام محصول نباید بیش از ۲۵۰ کاراکتر باشد"
        return name, None

    return str(value).strip(), None