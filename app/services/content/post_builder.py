"""
ساخت پست نهایی از قالب و داده محصول
"""

from pathlib import Path
from datetime import datetime

from app.database.models import Product, Business
from app.business.config import (
    BusinessConfig,
    get_business_template_path,
)
from app.services.content.hashtag_generator import (
    generate_hashtags,
    format_hashtags_for_post,
)
from app.utils.logger import log

try:
    import jdatetime
    HAS_JDATETIME = True
except ImportError:
    HAS_JDATETIME = False


# کاراکترهای Markdown که باید escape بشن در تلگرام
MARKDOWN_ESCAPE_CHARS = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']


def build_post_caption(
    product: Product,
    business_config: BusinessConfig,
    business: Business | None = None,
    include_ai_description: bool = False,
) -> str:
    """
    ساخت متن کامل کپشن پست

    Args:
        product: محصول
        business_config: تنظیمات کسب‌وکار
        business: رکورد کسب‌وکار مشتری (برای contact_text)
        include_ai_description: آیا از AI برای توضیحات استفاده بشه

    Returns:
        متن کامل پست آماده ارسال
    """
    # بارگذاری قالب
    template = _load_template(business_config)
    if not template:
        return _fallback_post(product, business_config)

    # آماده‌سازی مقادیر
    values = _prepare_template_values(product, business_config, business)

    # جایگذاری در قالب
    try:
        post_text = template.format(**values)
    except KeyError as e:
        log.error(f"کلید ناشناخته در قالب: {e}")
        return _fallback_post(product, business_config)

    # پاک کردن خطوط خالی اضافی
    post_text = _clean_empty_lines(post_text)

    return post_text


def _load_template(business_config: BusinessConfig) -> str | None:
    """خواندن قالب از فایل"""
    template_path = get_business_template_path(business_config.key)

    if not template_path or not template_path.exists():
        log.error(f"قالب پیدا نشد: {business_config.key}")
        return None

    try:
        return template_path.read_text(encoding="utf-8")
    except Exception as e:
        log.error(f"خطا در خواندن قالب: {e}")
        return None


def _prepare_template_values(
    product: Product,
    business_config: BusinessConfig,
    business: Business | None,
) -> dict:
    """آماده‌سازی مقادیر برای قالب"""

    # اطلاعات پایه
    values = {
        "product_name": product.product_name,
        "sku": product.sku,
        "price": _format_price(int(product.price)),
        "stock_status": _get_stock_status(product),
        "update_date": _format_date(product.updated_at),
    }

    # مقادیر از specs (برند، cpu، ram، ...)
    if product.specs:
        for key, value in product.specs.items():
            values[key] = str(value) if value else "-"

    # پر کردن فیلدهایی که در specs نبودن با "-"
    for field in business_config.fields:
        if field.key not in values and field.key not in [
            "sku", "product_name", "price", "stock", "description", "image_url"
        ]:
            values[field.key] = "-"

    # توضیحات
    values["description_block"] = _build_description_block(product)

    # هشتگ‌ها
    hashtags = generate_hashtags(product, business_config)
    values["hashtags"] = format_hashtags_for_post(hashtags)

    # اطلاعات تماس
    if business and business.contact_text:
        values["contact"] = f"سفارش: {business.contact_text}"
    else:
        values["contact"] = "برای سفارش پیام دهید"

    return values


def _format_price(price: int) -> str:
    """فرمت قیمت با کاما"""
    if price <= 0:
        return "-"
    return f"{price:,}"


def _get_stock_status(product: Product) -> str:
    """وضعیت موجودی برای نمایش"""
    if not product.is_available or product.stock_qty <= 0:
        return "❌ ناموجود"
    return "موجود ✅"


def _format_date(dt: datetime) -> str:
    """تبدیل تاریخ به شمسی"""
    if not dt:
        return ""

    if HAS_JDATETIME:
        try:
            jdate = jdatetime.datetime.fromgregorian(datetime=dt)
            return jdate.strftime("%Y/%m/%d")
        except Exception:
            pass

    return dt.strftime("%Y/%m/%d")


def _build_description_block(product: Product) -> str:
    """ساخت بلوک توضیحات"""
    if product.description_manual and product.description_manual.strip():
        return f"📝 {product.description_manual.strip()}"
    return ""


def _clean_empty_lines(text: str) -> str:
    """حذف خطوط خالی اضافی و trim"""
    lines = text.split("\n")
    result_lines = []

    prev_empty = False
    for line in lines:
        stripped = line.strip()
        # اگه توضیحات خالی بود، خط جای خالیش رو حذف کن
        if stripped == "":
            if not prev_empty:
                result_lines.append("")
                prev_empty = True
        else:
            result_lines.append(line)
            prev_empty = False

    # حذف خطوط خالی از ابتدا و انتها
    while result_lines and result_lines[0].strip() == "":
        result_lines.pop(0)
    while result_lines and result_lines[-1].strip() == "":
        result_lines.pop()

    return "\n".join(result_lines)


def _fallback_post(product: Product, business_config: BusinessConfig) -> str:
    """در صورت مشکل، یک پست ساده بساز"""
    price = _format_price(int(product.price))
    stock = _get_stock_status(product)

    return (
        f"{business_config.emoji} {product.product_name}\n\n"
        f"💰 قیمت: {price} تومان\n"
        f"📦 {stock}\n\n"
        f"🔖 کد: {product.sku}"
    )