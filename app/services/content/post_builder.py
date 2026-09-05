"""
ساخت پست نهایی از قالب و داده محصول
"""

from pathlib import Path
from datetime import datetime

from app.database.models import Product, Business
from app.business.config import (
    BusinessConfig,
    get_subcategory,
    get_subcategory_template_path,
    BUSINESS_DIR,
)
from app.services.content.hashtag_generator import (
    generate_hashtags,
    generate_price_range_hashtag,
    format_hashtags_for_post,
)
from app.utils.logger import log

try:
    import jdatetime
    HAS_JDATETIME = True
except ImportError:
    HAS_JDATETIME = False


def build_post_caption(
    product: Product,
    business_config: BusinessConfig,
    business: Business | None = None,
    preset_template_text: str | None = None,
) -> str:
    """
    ساخت متن کامل کپشن پست.
    اگه preset_template_text داده بشه (preset انتخابی مشتری)، همون استفاده
    می‌شه؛ وگرنه fallback به فایل .txt استاتیک قدیمی (رفتار قبلی، بدون تغییر).
    """
    if preset_template_text:
        from app.services.post_builder import render_post_from_text
        return render_post_from_text(product, preset_template_text, business=business)

    # ─── مسیر قدیمی: فایل .txt ثابت ───
    template = _load_template(product, business_config)
    if not template:
        return _fallback_post(product, business_config)

    values = _prepare_template_values(product, business_config, business)

    try:
        post_text = template.format(**values)
    except KeyError as e:
        log.error(f"کلید ناشناخته در قالب: {e}, sub_category: {product.sub_category_key}")
        return _fallback_post(product, business_config)
    except IndexError as e:
        log.error(f"خطای فرمت در قالب: {e}, sub_category: {product.sub_category_key}")
        log.error(f"Template values keys: {list(values.keys())}")
        log.error(f"Problematic values with braces: {[k for k, v in values.items() if isinstance(v, str) and '{' in str(v)]}") 
        return _fallback_post(product, business_config)

    return _clean_empty_lines(post_text)


def _load_template(product: Product, business_config: BusinessConfig) -> str | None:
    """خواندن قالب بر اساس sub_category محصول"""

    if not product.sub_category_key:
        log.warning(f"محصول {product.sku} sub_category ندارد")
        return None

    template_path = get_subcategory_template_path(
        business_config.key,
        product.sub_category_key,
    )

    if not template_path or not template_path.exists():
        log.error(
            f"قالب پیدا نشد: business={business_config.key}, "
            f"subcategory={product.sub_category_key}"
        )
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

    values = {
        "product_name": product.product_name,
        "sku": product.sku,
        "price": _format_price(int(product.price)),
        "stock_status": _get_stock_status(product),
        "update_date": _format_date(product.updated_at),
    }

    # مقادیر از specs
    if product.specs:
        for key, value in product.specs.items():
            values[key] = str(value) if value else "-"

    # پیدا کردن subcategory برای فیلدهای اختیاری خالی
    subcategory = get_subcategory(business_config.key, product.sub_category_key)
    if subcategory:
        for field in subcategory.fields:
            if field.key not in values and field.key not in [
                "sku", "product_name", "price", "stock", "description", "image_url"
            ]:
                values[field.key] = "-"

    values["description_block"] = _build_description_block(product)

    # 🆕 خروجی AI (ai_description, ai_pros→ai_features, ai_cons) — برای قالب‌های قدیمی که این‌ها رو دارن
    values["ai_description"] = product.ai_description or ""
    values["ai_features"] = "\n".join(f"🔹 {f}" for f in (product.ai_pros or []))
    values["ai_cons"] = "\n".join(f"⚠️ {c}" for c in (product.ai_cons or []))

    # هشتگ‌ها
    hashtags = generate_hashtags(product, business_config)
    values["hashtags"] = format_hashtags_for_post(hashtags)
    values["price_range"] = generate_price_range_hashtag(product)

    # اطلاعات تماس
    if business and business.contact_text:
        values["contact"] = f"سفارش: {business.contact_text}"
    else:
        values["contact"] = "برای سفارش پیام دهید"

    return values


def _format_price(price: int) -> str:
    if price <= 0:
        return "-"
    return f"{price:,}"


def _get_stock_status(product: Product) -> str:
    if not product.is_available or product.stock_qty <= 0:
        return "❌ ناموجود"
    return "موجود ✅"


def _format_date(dt: datetime) -> str:
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
    """
    ساخت بلوک توضیحات
    - اگه متن با ایموجی 📝 شروع میشه (از AI)، همون رو برگردون
    - وگرنه (از اکسل/شیت)، 📝 اضافه کن
    """
    if not product.description_custom:
        return ""

    text = product.description_custom.strip()
    if not text:
        return ""

    # اگه متن با 📝 شروع میشه، خودش داره - دست نزن
    if text.startswith("📝"):
        return text

    # وگرنه 📝 اضافه کن
    return f"📝 {text}"


def _clean_empty_lines(text: str) -> str:
    """حذف خطوط خالی اضافی"""
    lines = text.split("\n")
    result_lines = []

    prev_empty = False
    for line in lines:
        stripped = line.strip()
        if stripped == "":
            if not prev_empty:
                result_lines.append("")
                prev_empty = True
        else:
            result_lines.append(line)
            prev_empty = False

    while result_lines and result_lines[0].strip() == "":
        result_lines.pop(0)
    while result_lines and result_lines[-1].strip() == "":
        result_lines.pop()

    return "\n".join(result_lines)


def _fallback_post(product: Product, business_config: BusinessConfig) -> str:
    """پست ساده در صورت مشکل"""
    price = _format_price(int(product.price))
    stock = _get_stock_status(product)

    return (
        f"{business_config.emoji} {product.product_name}\n\n"
        f"💰 قیمت: {price} تومان\n"
        f"📦 {stock}\n\n"
        f"🔖 کد: {product.sku}"
    )