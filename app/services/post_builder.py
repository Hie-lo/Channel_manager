"""
موتور رندر پست

ورودی:
  - product: dict یا ORM Product
  - template: PostTemplate (از دیتابیس)

خروجی:
  - PostRenderResult با متن نهایی، image_url، و وضعیت فیلتر

گسترش‌پذیری:
  قالب به‌صورت JSONB در دیتابیس ذخیره است.
  فیلدهای جدید هر کسب‌وکار را می‌توان در body_fields اضافه کرد
  بدون نیاز به تغییر این فایل.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.database.models import PostTemplate
from app.utils.logger import log


# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PostRenderResult:
    text: str           = ""
    image_url: str | None = None
    # آیا این محصول باید رد شود (طبق فیلترهای قالب)؟
    should_skip: bool   = False
    skip_reason: str    = ""
    # متن عنوان جداگانه (برای استفاده در caption پیشرفته)
    title: str          = ""
    # بدنه بدون پاورقی
    body: str           = ""
    # هشتگ‌ها
    hashtags: str       = ""


# ─────────────────────────────────────────────────────────────────────────────
# ابزارهای کمکی
# ─────────────────────────────────────────────────────────────────────────────

def _get_field_value(product: Any, field_key: str) -> Any:
    """
    دریافت مقدار فیلد از محصول.
    از نقطه برای دسترسی به کلیدهای تودرتو (مثل specs.color) پشتیبانی می‌کند.
    product می‌تواند ORM object یا dict باشد.
    """
    parts = field_key.split(".", 1)
    if isinstance(product, dict):
        val = product.get(parts[0])
    else:
        val = getattr(product, parts[0], None)

    if len(parts) == 2 and isinstance(val, dict):
        val = val.get(parts[1])

    return val


def _format_value(raw_value: Any, fmt: str) -> str:
    """اعمال format string روی مقدار"""
    if raw_value is None or str(raw_value).strip() == "":
        return ""
    try:
        if isinstance(raw_value, (int, float)) and ":," in fmt:
            return fmt.replace("{value:,}", f"{int(raw_value):,}").replace("{value}", str(raw_value))
        return fmt.replace("{value}", str(raw_value))
    except Exception:
        return str(raw_value)


def _normalize_hashtag(text: str) -> str:
    """تبدیل متن به هشتگ مناسب"""
    text = str(text).strip()
    # حذف کاراکترهای غیرمجاز
    text = re.sub(r"[\s\-/\\،,\.]+", "_", text)
    text = re.sub(r"[^\w\u0600-\u06FF_]", "", text)
    return text.strip("_")


# ─────────────────────────────────────────────────────────────────────────────
# رندر عنوان
# ─────────────────────────────────────────────────────────────────────────────

def _render_title(product: Any, template: PostTemplate) -> str:
    """رندر عنوان با placeholder ها"""
    pattern = template.title_pattern or "{product_name}"

    # پیدا کردن تمام placeholder ها
    placeholders = re.findall(r"\{(\w+(?:\.\w+)?)\}", pattern)

    result = pattern
    for ph in placeholders:
        val = _get_field_value(product, ph)
        result = result.replace(f"{{{ph}}}", str(val) if val else "")

    result = result.strip()
    if template.title_bold:
        result = f"<b>{result}</b>"
    return result


# ─────────────────────────────────────────────────────────────────────────────
# رندر بدنه
# ─────────────────────────────────────────────────────────────────────────────

def _render_body(product: Any, template: PostTemplate) -> str:
    """رندر بدنه پست از لیست فیلدها"""
    separator = template.field_separator or "\n"
    lines: list[str] = []

    for field_def in (template.body_fields or []):
        if not field_def.get("enabled", True):
            continue

        key   = field_def.get("key", "")
        label = field_def.get("label", "")
        fmt   = field_def.get("format", "{value}")

        raw_value = _get_field_value(product, key)

        # صفر برای موجودی اگر تنظیم شده باشد
        if key in ("stock_qty", "stock") and isinstance(raw_value, int) and raw_value == 0:
            if field_def.get("hide_if_zero", False):
                continue

        if raw_value is None or str(raw_value).strip() == "":
            continue

        formatted = _format_value(raw_value, fmt)
        if formatted:
            lines.append(f"{label}: {formatted}" if label else formatted)

    return separator.join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# رندر هشتگ‌ها
# ─────────────────────────────────────────────────────────────────────────────

def _render_hashtags(product: Any, template: PostTemplate) -> str:
    tags: list[str] = []

    # هشتگ‌های ثابت
    for tag in (template.static_hashtags or []):
        tags.append(tag.strip())

    # هشتگ‌های پویا
    for dyn in (template.dynamic_hashtags or []):
        field_key = dyn.get("field", "")
        prefix    = dyn.get("prefix", "#")
        val       = _get_field_value(product, field_key)
        if val:
            normalized = _normalize_hashtag(str(val))
            if normalized:
                tags.append(f"{prefix}{normalized}")

    return " ".join(tags)


# ─────────────────────────────────────────────────────────────────────────────
# فیلترها
# ─────────────────────────────────────────────────────────────────────────────

def _should_skip(product: Any, template: PostTemplate) -> tuple[bool, str]:
    """بررسی فیلترها — (should_skip, reason)"""
    stock = _get_field_value(product, "stock_qty")
    price = _get_field_value(product, "price")

    if template.skip_if_out_of_stock:
        try:
            if stock is not None and int(stock) < template.min_stock:
                return True, f"موجودی {stock} کمتر از حداقل {template.min_stock}"
        except (TypeError, ValueError):
            pass

    if template.skip_if_price_zero:
        try:
            if price is not None and float(price) <= 0:
                return True, "قیمت صفر یا منفی"
        except (TypeError, ValueError):
            pass

    return False, ""


# ─────────────────────────────────────────────────────────────────────────────
# ورودی اصلی
# ─────────────────────────────────────────────────────────────────────────────

def render_post(product: Any, template: PostTemplate) -> PostRenderResult:
    """
    رندر کامل یک پست برای یک محصول.

    Args:
        product: ORM Product یا dict با کلیدهای استاندارد
        template: PostTemplate از دیتابیس

    Returns:
        PostRenderResult
    """
    result = PostRenderResult()

    # ─── فیلتر ───
    skip, reason = _should_skip(product, template)
    if skip:
        result.should_skip = True
        result.skip_reason = reason
        return result

    # ─── عنوان ───
    result.title = _render_title(product, template)

    # ─── بدنه ───
    result.body = _render_body(product, template)

    # ─── هشتگ‌ها ───
    result.hashtags = _render_hashtags(product, template)

    # ─── پاورقی ───
    footer_parts: list[str] = []
    if template.contact_text:
        footer_parts.append(template.contact_text)
    if result.hashtags:
        footer_parts.append(result.hashtags)
    footer = "\n".join(footer_parts)

    # ─── متن نهایی ───
    parts = [result.title]
    if result.body:
        parts.append(result.body)
    if footer:
        parts.append(footer)

    result.text = "\n\n".join(p for p in parts if p)

    # ─── تصویر ───
    image_url = _get_field_value(product, "image_url")
    if image_url and template.use_image:
        result.image_url = str(image_url).strip() or None
    elif template.fallback_image_url and template.use_image:
        result.image_url = template.fallback_image_url

    return result


def render_posts_batch(
    products: list[Any],
    template: PostTemplate,
) -> tuple[list[PostRenderResult], list[PostRenderResult]]:
    """
    رندر دسته‌ای محصولات.
    Returns: (rendered_list, skipped_list)
    """
    rendered: list[PostRenderResult] = []
    skipped:  list[PostRenderResult] = []

    for product in products:
        r = render_post(product, template)
        if r.should_skip:
            skipped.append(r)
        else:
            rendered.append(r)

    log.info(f"[PostBuilder] رندر: {len(rendered)} پست، {len(skipped)} رد شد")
    return rendered, skipped


# ─────────────────────────────────────────────────────────────────────────────
# رندر مستقیم از متن خام preset (سیستم جدید — بدون PostTemplate)
# ─────────────────────────────────────────────────────────────────────────────

def render_post_from_text(product: Any, template_text: str) -> str:
    """
    رندر یک متن قالب خام (raw، با {placeholder}) — مثل preset های ادمین یا
    فایل‌های .txt قدیمی.

    برای سازگاری کامل با قالب‌های فعلی، همون رفتار سیستم قدیمی رو داره:
    محتوای specs مستقیم روی سطح بالا مسطح می‌شه (بدون نیاز به {specs.cpu}؛
    فقط {cpu} کافیه)، و چند placeholder محاسبه‌شده (قیمت فرمت‌شده،
    وضعیت موجودی، بلوک توضیحات) هم اضافه می‌شه.

    product می‌تونه ORM Product یا dict باشه.
    """
    if isinstance(product, dict):
        flat: dict[str, Any] = dict(product)
        specs = flat.pop("specs", None) or {}
        price_raw = flat.get("price")
        stock_qty = flat.get("stock_qty", 0)
        is_available = flat.get("is_available", (stock_qty or 0) > 0)
        description_custom = flat.get("description_custom", "")
    else:
        flat = {
            "product_name": getattr(product, "product_name", "") or "",
            "sku": getattr(product, "sku", "") or "",
            "stock_qty": getattr(product, "stock_qty", 0) or 0,
            "image_url": getattr(product, "image_url", "") or "",
        }
        specs = getattr(product, "specs", None) or {}
        price_raw = getattr(product, "price", 0)
        stock_qty = flat["stock_qty"]
        is_available = getattr(product, "is_available", stock_qty > 0)
        description_custom = getattr(product, "description_custom", "") or ""

    # مسطح‌سازی specs روی سطح بالا (دقیقاً مثل سیستم قدیمی .txt)
    flat.update(specs)

    # قیمت فرمت‌شده با کاما
    try:
        price_int = int(float(price_raw)) if price_raw not in (None, "") else 0
    except (TypeError, ValueError):
        price_int = 0
    flat["price"] = f"{price_int:,}" if price_int > 0 else "-"

    # وضعیت موجودی
    flat["stock_status"] = "❌ ناموجود" if (not is_available or (stock_qty or 0) <= 0) else "موجود ✅"

    # بلوک توضیحات (با 📝، بدون تکرار اگه از قبل داشته باشه)
    desc_text = str(description_custom).strip() if description_custom else ""
    if desc_text and not desc_text.startswith("📝"):
        desc_text = f"📝 {desc_text}"
    flat["description_block"] = desc_text
    flat.setdefault("description_custom", description_custom or "")
    
    # ─── Placeholder های جدید AI ───
    if isinstance(product, dict):
        ai_description = product.get("ai_description", "")
        ai_pros = product.get("ai_pros", [])
        ai_cons = product.get("ai_cons", [])
    else:
        ai_description = getattr(product, "ai_description", "") or ""
        ai_pros = getattr(product, "ai_pros", []) or []
        ai_cons = getattr(product, "ai_cons", []) or []
    
    flat["ai_description"] = ai_description
    
    # فرمت ویژگی‌ها/مزایا (با ایموجی پیش‌فرض)
    if ai_pros:
        pros_lines = [f"🔹 {item}" for item in ai_pros]
        flat["ai_features"] = "\n".join(pros_lines)  # برای کامپیوتری
        flat["ai_pros"] = "\n".join(pros_lines)      # برای عمومی
    else:
        flat["ai_features"] = ""
        flat["ai_pros"] = ""
    
    # فرمت معایب
    if ai_cons:
        cons_lines = [f"• {item}" for item in ai_cons]
        flat["ai_cons"] = "\n".join(cons_lines)
    else:
        flat["ai_cons"] = ""
    
    # ─── Placeholder برای contact_id (باید از channel گرفته بشه) ───
    # این placeholder در زمان ارسال به کانال پر می‌شود
    flat.setdefault("contact_id", "")

    placeholders = set(re.findall(r"\{(\w+)\}", template_text))
    result = template_text
    for ph in placeholders:
        val = flat.get(ph)
        replacement = "" if val is None else str(val)
        result = result.replace(f"{{{ph}}}", replacement)
    
    # حذف خطوط خالی اضافی که از placeholder های خالی ایجاد شده
    lines = result.split('\n')
    cleaned_lines = [line for line in lines if line.strip()]
    result = '\n'.join(cleaned_lines)

    return result.strip()