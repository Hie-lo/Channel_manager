"""
سرویس خواندن فایل اکسل
"""

from pathlib import Path
from dataclasses import dataclass, field
from openpyxl import load_workbook

from app.business.config import BusinessConfig
from app.utils.logger import log


@dataclass
class RowError:
    """خطا در یک ردیف"""
    row_number: int
    field: str
    message: str


@dataclass
class ExcelReadResult:
    """نتیجه خواندن فایل اکسل"""
    products: list[dict] = field(default_factory=list)
    errors: list[RowError] = field(default_factory=list)
    total_rows: int = 0
    valid_rows: int = 0

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def is_empty(self) -> bool:
        return self.valid_rows == 0


def read_excel_file(
    file_path: str | Path,
    business_config: BusinessConfig,
) -> ExcelReadResult:
    """
    خواندن فایل اکسل و تبدیل به لیست محصولات

    Args:
        file_path: مسیر فایل اکسل
        business_config: تنظیمات کسب‌وکار (برای شناخت ستون‌ها)

    Returns:
        ExcelReadResult حاوی محصولات، خطاها و آمار
    """
    result = ExcelReadResult()

    try:
        workbook = load_workbook(filename=file_path, data_only=True)
    except Exception as e:
        log.error(f"خطا در باز کردن فایل اکسل: {e}")
        result.errors.append(RowError(
            row_number=0,
            field="file",
            message=f"فایل قابل خواندن نیست: {str(e)}"
        ))
        return result

    # اولین شیت
    sheet = workbook.active

    # خواندن سطر اول (هدر)
    headers = []
    for cell in sheet[1]:
        if cell.value:
            headers.append(str(cell.value).strip())
        else:
            headers.append("")

    if not headers:
        result.errors.append(RowError(
            row_number=1,
            field="header",
            message="ردیف اول (نام ستون‌ها) خالی است"
        ))
        return result

    # نگاشت نام ستون فارسی به کلید فنی
    field_map = _build_field_map(business_config, headers)

    # چک کن فیلدهای اجباری در هدر هستن
    missing_required = _check_missing_required_fields(business_config, field_map)
    if missing_required:
        for field_name in missing_required:
            result.errors.append(RowError(
                row_number=1,
                field=field_name,
                message=f"ستون '{field_name}' در فایل پیدا نشد (اجباری)"
            ))
        return result

    # خواندن ردیف‌های داده (از سطر ۲)
    for row_index, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        # چک کن ردیف خالی نباشه
        if all(cell is None or str(cell).strip() == "" for cell in row):
            continue

        result.total_rows += 1

        # تبدیل ردیف به dict
        product_data, row_errors = _parse_row(
            row=row,
            headers=headers,
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
        f"فایل اکسل خونده شد: {result.total_rows} سطر، "
        f"{result.valid_rows} معتبر، {len(result.errors)} خطا"
    )

    return result


def _build_field_map(
    business_config: BusinessConfig,
    headers: list[str],
) -> dict[str, int]:
    """
    نگاشت field_key به شماره ستون
    مثال: {"sku": 0, "product_name": 1, ...}
    """
    field_map = {}

    for field in business_config.fields:
        excel_col_name = field.excel_column
        try:
            col_index = headers.index(excel_col_name)
            field_map[field.key] = col_index
        except ValueError:
            # ستون پیدا نشد
            pass

    return field_map


def _check_missing_required_fields(
    business_config: BusinessConfig,
    field_map: dict[str, int],
) -> list[str]:
    """چک کن فیلدهای اجباری در فایل هستن"""
    missing = []
    for field in business_config.fields:
        if field.required and field.key not in field_map:
            missing.append(field.excel_column)
    return missing


def _parse_row(
    row: tuple,
    headers: list[str],
    field_map: dict[str, int],
    business_config: BusinessConfig,
    row_number: int,
) -> tuple[dict, list[RowError]]:
    """
    پارس یک ردیف به dict محصول
    """
    product_data = {"row_number": row_number, "specs": {}}
    errors = []

    for field in business_config.fields:
        if field.key not in field_map:
            continue

        col_index = field_map[field.key]
        raw_value = row[col_index] if col_index < len(row) else None

        # پاکسازی مقدار
        value = _clean_value(raw_value)

        # چک اجباری بودن
        if field.required and (value is None or value == ""):
            errors.append(RowError(
                row_number=row_number,
                field=field.excel_column,
                message=f"مقدار '{field.excel_column}' خالی است"
            ))
            continue

        # اعتبارسنجی و تبدیل نوع
        parsed_value, parse_error = _parse_field_value(field.key, value, field.excel_column)

        if parse_error:
            errors.append(RowError(
                row_number=row_number,
                field=field.excel_column,
                message=parse_error,
            ))
            continue

        # ذخیره در product_data
        if field.key in ("sku", "product_name", "price", "stock", "description", "image_url"):
            # فیلدهای اصلی
            product_data[field.key] = parsed_value
        else:
            # فیلدهای مشخصات فنی
            product_data["specs"][field.key] = parsed_value

    return product_data, errors


def _clean_value(value):
    """پاکسازی مقدار سلول اکسل"""
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value if value else None
    return value


def _parse_field_value(field_key: str, value, column_name: str) -> tuple:
    """
    اعتبارسنجی و تبدیل نوع مقدار
    Returns: (parsed_value, error_message)
    """
    if value is None or value == "":
        return None, None

    # قیمت باید عدد باشه
    if field_key == "price":
        try:
            # اگه رشته با کاما بود، پاک کن
            if isinstance(value, str):
                value = value.replace(",", "").replace("،", "").strip()
            price = int(float(value))
            if price < 0:
                return None, "قیمت نمی‌تواند منفی باشد"
            return price, None
        except (ValueError, TypeError):
            return None, f"قیمت باید عدد باشد (مقدار: {value})"

    # موجودی باید عدد باشه
    if field_key == "stock":
        try:
            stock = int(float(value))
            if stock < 0:
                return None, "موجودی نمی‌تواند منفی باشد"
            return stock, None
        except (ValueError, TypeError):
            return None, f"موجودی باید عدد باشد (مقدار: {value})"

    # SKU باید string باشه
    if field_key == "sku":
        sku = str(value).strip()
        if not sku:
            return None, "کد محصول نمی‌تواند خالی باشد"
        if len(sku) > 80:
            return None, "کد محصول نباید بیش از ۸۰ کاراکتر باشد"
        return sku, None

    # نام محصول
    if field_key == "product_name":
        name = str(value).strip()
        if not name:
            return None, "نام محصول نمی‌تواند خالی باشد"
        if len(name) > 250:
            return None, "نام محصول نباید بیش از ۲۵۰ کاراکتر باشد"
        return name, None

    # بقیه فیلدها به صورت string
    return str(value).strip(), None