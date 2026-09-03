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
from app.business.config import get_business
from app.services.content.hashtag_generator import (
    generate_hashtags,
    format_hashtags_for_post,
)
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

def render_post_from_text(product: Any, template_text: str, business: Any = None) -> str:
    """
    رندر یک متن قالب خام (raw، با {placeholder}) — مثل preset های ادمین یا
    فایل‌های .txt قدیمی.

    محتوای specs مستقیم روی سطح بالا مسطح می‌شه (فقط {cpu} کافیه)،
    و چند placeholder محاسبه‌شده (قیمت، وضعیت موجودی، توضیحات، AI، تماس،
    تاریخ) هم اضافه می‌شه.

    🆕 اگه یک خط شامل placeholder ای باشه که مقدارش خالیه، کل اون خط حذف
    می‌شه. خطوط خالیِ خودِ قالب (که کاربر عمداً گذاشته) دست‌نخورده می‌مونن.

    product می‌تونه ORM Product یا dict باشه. business اختیاریه (برای {contact}).
    """
    if isinstance(product, dict):
        flat: dict[str, Any] = dict(product)
        specs = flat.pop("specs", None) or {}
        price_raw = flat.get("price")
        stock_qty = flat.get("stock_qty", 0)
        is_available = flat.get("is_available", (stock_qty or 0) > 0)
        description_custom = flat.get("description_custom", "")
        ai_description = flat.get("ai_description", "")
        ai_pros = flat.get("ai_pros") or []
        ai_cons = flat.get("ai_cons") or []
        updated_at = flat.get("updated_at")
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
        ai_description = getattr(product, "ai_description", "") or ""
        ai_pros = getattr(product, "ai_pros", None) or []
        ai_cons = getattr(product, "ai_cons", None) or []
        updated_at = getattr(product, "updated_at", None)

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

    # بلوک توضیحات دستی/اکسل (با 📝)
    desc_text = str(description_custom).strip() if description_custom else ""
    if desc_text and not desc_text.startswith("📝"):
        desc_text = f"📝 {desc_text}"
    flat["description_block"] = desc_text
    flat["description_custom"] = description_custom or ""

    # 🆕 خروجی AI — جدا از description_custom
    flat["ai_description"] = ai_description or ""
    flat["ai_features"] = "\n".join(f"🔹 {f}" for f in ai_pros) if ai_pros else ""
    flat["ai_cons"] = "\n".join(f"⚠️ {c}" for c in ai_cons) if ai_cons else ""

    business_key = getattr(business, "business_type_key", None) if business else None
    business_config = get_business(business_key) if business_key else None
    flat["hashtags"] = (
        format_hashtags_for_post(generate_hashtags(product, business_config))
        if business_config and not isinstance(product, dict)
        else ""
    )

    flat["contact_id"] = "{contact_id}"
    flat["contact"] = "{contact}"
    flat["phone"] = "{phone}"

    # مقدار تماس عمومی برای قالب‌هایی که صریحاً business_contact را می‌خواهند
    contact_text = getattr(business, "contact_text", None) if business else None
    flat["business_contact"] = f"سفارش: {contact_text}" if contact_text else "برای سفارش پیام دهید"

    # تاریخ آپدیت (شمسی در صورت وجود jdatetime)
    flat["update_date"] = _format_update_date(updated_at)

    return _render_lines_with_omission(template_text, flat)


def _format_update_date(dt) -> str:
    if not dt:
        return ""
    try:
        import jdatetime
        return jdatetime.datetime.fromgregorian(datetime=dt).strftime("%Y/%m/%d")
    except Exception:
        try:
            return dt.strftime("%Y/%m/%d")
        except Exception:
            return ""


def _render_lines_with_omission(template_text: str, values: dict) -> str:
    """
    جایگزینی placeholder ها خط‌به‌خط. اگه خطی حداقل یک placeholder داشته باشه
    و مقدار یکی از placeholder هاش خالی باشه، کل اون خط حذف می‌شه.
    خطوطی که هیچ placeholder ندارن (چه متن، چه خالیِ عمدی) همیشه نگه داشته
    می‌شن — فاصله‌های خالیِ خودِ قالب هرگز جمع/حذف نمی‌شن.
    """
    output_lines: list[str] = []

    for line in template_text.split("\n"):
        placeholders = re.findall(r"\{(\w+)\}", line)

        if not placeholders:
            output_lines.append(line)
            continue

        has_empty = False
        rendered_line = line
        for ph in placeholders:
            val = values.get(ph)
            if val is None or str(val).strip() == "":
                has_empty = True
                break
            rendered_line = rendered_line.replace(f"{{{ph}}}", str(val))

        if has_empty:
            continue  # کل خط حذف می‌شه (نه جایگزین با خط خالی)

        output_lines.append(rendered_line)

    # فقط خطوط خالیِ ابتدا/انتهای کل متن پاک می‌شن؛ فضای خالی داخل قالب دست‌نخورده می‌مونه
    while output_lines and output_lines[0].strip() == "":
        output_lines.pop(0)
    while output_lines and output_lines[-1].strip() == "":
        output_lines.pop()

    return "\n".join(output_lines)