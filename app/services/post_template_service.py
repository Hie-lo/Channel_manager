"""
سرویس مدیریت PostTemplate
ذخیره، بازیابی و ساخت قالب پیش‌فرض برای هر کسب‌وکار.

گسترش‌پذیری:
  برای اضافه کردن کسب‌وکار جدید، فقط یک case در
  get_default_body_fields() و get_default_title_pattern() اضافه کنید.
  تمام منطق موجود بدون تغییر باقی می‌ماند.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import PostTemplate
from app.business.config import BusinessConfig, get_business, SubCategory
from app.utils.time import utc_now_naive
from app.utils.logger import log


# ─────────────────────────────────────────────────────────────────────────────
# قالب‌های پیش‌فرض بر اساس نوع کسب‌وکار
# ─────────────────────────────────────────────────────────────────────────────

def get_default_title_pattern(business_type_key: str) -> str:
    """الگوی عنوان پیش‌فرض بر اساس نوع کسب‌وکار"""
    patterns: dict[str, str] = {
        "clothing_shop": "👕 {brand} | {product_name}",
        "computer_shop": "💻 {brand} {product_name}",
        "mobile_shop":   "📱 {brand} {product_name}",
        "other":         "📦 {product_name}",
    }
    # اگر نوع جدیدی اضافه شد و در دیکشنری نبود، fallback عمومی
    return patterns.get(business_type_key, "📦 {product_name}")


def get_default_body_fields(business_type_key: str, subcategory_key: str = "") -> list[dict]:
    """
    لیست فیلدهای پیش‌فرض بدنه پست.
    هر آیتم: {"key", "label", "format", "enabled"}
    برای اضافه کردن کسب‌وکار جدید یک case اضافه کنید.
    """

    # ─── فیلدهای مشترک همه کسب‌وکارها ───
    common_price = {"key": "price",       "label": "💰 قیمت",    "format": "{value:,} تومان", "enabled": True}
    common_stock = {"key": "stock_qty",   "label": "📦 موجودی",  "format": "{value} عدد",     "enabled": True}
    common_desc  = {"key": "description_manual", "label": "📝 توضیحات", "format": "{value}", "enabled": False}

    if business_type_key == "clothing_shop":
        return [
            common_price,
            {"key": "specs.color",    "label": "🎨 رنگ",         "format": "{value}",         "enabled": True},
            {"key": "specs.size",     "label": "📏 سایز",         "format": "{value}",         "enabled": True},
            {"key": "specs.material", "label": "🧶 جنس",          "format": "{value}",         "enabled": False},
            common_stock,
            common_desc,
        ]

    if business_type_key == "computer_shop":
        base = [common_price, common_stock]
        if subcategory_key == "laptop":
            return [
                common_price,
                {"key": "specs.cpu",     "label": "⚡ پردازنده",  "format": "{value}", "enabled": True},
                {"key": "specs.ram",     "label": "🧠 رم",         "format": "{value}", "enabled": True},
                {"key": "specs.storage", "label": "💾 حافظه",      "format": "{value}", "enabled": True},
                {"key": "specs.gpu",     "label": "🎮 گرافیک",     "format": "{value}", "enabled": True},
                {"key": "specs.screen",  "label": "📐 صفحه‌نمایش", "format": "{value}", "enabled": False},
                common_stock,
                common_desc,
            ]
        if subcategory_key == "monitor":
            return [
                common_price,
                {"key": "specs.screen_size",  "label": "📐 سایز",        "format": "{value}", "enabled": True},
                {"key": "specs.resolution",   "label": "🔍 رزولوشن",      "format": "{value}", "enabled": True},
                {"key": "specs.refresh_rate", "label": "⚡ نرخ رفرش",     "format": "{value}", "enabled": True},
                {"key": "specs.panel_type",   "label": "🎨 نوع پنل",      "format": "{value}", "enabled": False},
                common_stock,
            ]
        return base + [common_desc]

    if business_type_key == "mobile_shop":
        return [
            common_price,
            {"key": "specs.ram",     "label": "🧠 رم",            "format": "{value}", "enabled": True},
            {"key": "specs.storage", "label": "💾 حافظه داخلی",   "format": "{value}", "enabled": True},
            {"key": "specs.color",   "label": "🎨 رنگ",           "format": "{value}", "enabled": True},
            {"key": "specs.camera",  "label": "📸 دوربین",         "format": "{value}", "enabled": False},
            {"key": "specs.battery", "label": "🔋 باتری",          "format": "{value}", "enabled": False},
            common_stock,
            common_desc,
        ]

    # fallback برای هر کسب‌وکاری که در آینده اضافه شود
    return [common_price, common_stock, common_desc]


def get_default_static_hashtags(business_type_key: str) -> list[str]:
    hashtags: dict[str, list[str]] = {
        "clothing_shop": ["#پوشاک", "#لباس", "#مد", "#خرید_آنلاین"],
        "computer_shop": ["#کامپیوتر", "#لپتاپ", "#خرید_لپتاپ"],
        "mobile_shop":   ["#موبایل", "#گوشی", "#خرید_موبایل"],
        "other":         ["#فروشگاه", "#خرید_آنلاین"],
    }
    return hashtags.get(business_type_key, ["#فروشگاه"])


def get_default_dynamic_hashtags(business_type_key: str) -> list[dict]:
    """هشتگ‌های پویا — از مقدار فیلدها ساخته می‌شوند"""
    dynamic: dict[str, list[dict]] = {
        "clothing_shop": [
            {"field": "brand",       "prefix": "#"},
            {"field": "specs.color", "prefix": "#رنگ_"},
        ],
        "computer_shop": [
            {"field": "brand", "prefix": "#"},
        ],
        "mobile_shop": [
            {"field": "brand",       "prefix": "#"},
            {"field": "specs.color", "prefix": "#رنگ_"},
        ],
        "other": [],
    }
    return dynamic.get(business_type_key, [])


# ─────────────────────────────────────────────────────────────────────────────
# CRUD
# ─────────────────────────────────────────────────────────────────────────────

async def get_post_template(
    session: AsyncSession,
    customer_id: int,
) -> PostTemplate | None:
    result = await session.execute(
        select(PostTemplate)
        .where(PostTemplate.customer_id == customer_id)
        .limit(1)
    )
    return result.scalars().first()


async def get_or_create_post_template(
    session: AsyncSession,
    customer_id: int,
    business_type_key: str,
    subcategory_key: str = "",
    contact_text: str | None = None,
) -> PostTemplate:
    """
    دریافت قالب موجود یا ساخت قالب پیش‌فرض برای کسب‌وکار.
    اگر قالب وجود داشته باشد، بدون تغییر برمی‌گردد.
    """
    template = await get_post_template(session, customer_id)
    if template:
        return template

    template = PostTemplate(
        customer_id=customer_id,
        template_name=f"قالب پیش‌فرض",
        title_pattern=get_default_title_pattern(business_type_key),
        title_bold=True,
        body_fields=get_default_body_fields(business_type_key, subcategory_key),
        field_separator="\n",
        skip_if_out_of_stock=True,
        skip_if_price_zero=True,
        min_stock=1,
        use_image=True,
        contact_text=contact_text,
        static_hashtags=get_default_static_hashtags(business_type_key),
        dynamic_hashtags=get_default_dynamic_hashtags(business_type_key),
        layout="text_with_image",
        created_at=utc_now_naive(),
        updated_at=utc_now_naive(),
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    log.info(f"[PostTemplateService] قالب پیش‌فرض ساخته شد: customer={customer_id}, biz={business_type_key}")
    return template


async def update_template_title(
    session: AsyncSession,
    customer_id: int,
    title_pattern: str,
    title_bold: bool | None = None,
) -> PostTemplate | None:
    template = await get_post_template(session, customer_id)
    if not template:
        return None
    template.title_pattern = title_pattern
    if title_bold is not None:
        template.title_bold = title_bold
    template.updated_at = utc_now_naive()
    await session.commit()
    await session.refresh(template)
    return template


async def update_template_body_fields(
    session: AsyncSession,
    customer_id: int,
    body_fields: list[dict],
) -> PostTemplate | None:
    """آپدیت لیست و ترتیب فیلدهای بدنه"""
    template = await get_post_template(session, customer_id)
    if not template:
        return None
    template.body_fields = body_fields
    template.updated_at  = utc_now_naive()
    await session.commit()
    await session.refresh(template)
    return template


async def toggle_body_field(
    session: AsyncSession,
    customer_id: int,
    field_key: str,
) -> PostTemplate | None:
    """فعال/غیرفعال کردن یک فیلد در بدنه"""
    template = await get_post_template(session, customer_id)
    if not template:
        return None

    fields = list(template.body_fields)
    for f in fields:
        if f.get("key") == field_key:
            f["enabled"] = not f.get("enabled", True)
            break

    template.body_fields = fields
    template.updated_at  = utc_now_naive()
    await session.commit()
    await session.refresh(template)
    return template


async def update_template_hashtags(
    session: AsyncSession,
    customer_id: int,
    static_hashtags: list[str] | None = None,
    dynamic_hashtags: list[dict] | None = None,
) -> PostTemplate | None:
    template = await get_post_template(session, customer_id)
    if not template:
        return None
    if static_hashtags is not None:
        template.static_hashtags = static_hashtags
    if dynamic_hashtags is not None:
        template.dynamic_hashtags = dynamic_hashtags
    template.updated_at = utc_now_naive()
    await session.commit()
    await session.refresh(template)
    return template


async def update_template_filters(
    session: AsyncSession,
    customer_id: int,
    skip_if_out_of_stock: bool | None = None,
    skip_if_price_zero: bool | None = None,
    min_stock: int | None = None,
) -> PostTemplate | None:
    template = await get_post_template(session, customer_id)
    if not template:
        return None
    if skip_if_out_of_stock is not None:
        template.skip_if_out_of_stock = skip_if_out_of_stock
    if skip_if_price_zero is not None:
        template.skip_if_price_zero = skip_if_price_zero
    if min_stock is not None:
        template.min_stock = min_stock
    template.updated_at = utc_now_naive()
    await session.commit()
    await session.refresh(template)
    return template


async def update_template_contact(
    session: AsyncSession,
    customer_id: int,
    contact_text: str,
) -> PostTemplate | None:
    template = await get_post_template(session, customer_id)
    if not template:
        return None
    template.contact_text = contact_text
    template.updated_at   = utc_now_naive()
    await session.commit()
    await session.refresh(template)
    return template


async def reset_template_to_default(
    session: AsyncSession,
    customer_id: int,
    business_type_key: str,
    subcategory_key: str = "",
) -> PostTemplate | None:
    """بازنشانی قالب به پیش‌فرض کسب‌وکار"""
    template = await get_post_template(session, customer_id)
    if not template:
        return None
    template.title_pattern    = get_default_title_pattern(business_type_key)
    template.body_fields      = get_default_body_fields(business_type_key, subcategory_key)
    template.static_hashtags  = get_default_static_hashtags(business_type_key)
    template.dynamic_hashtags = get_default_dynamic_hashtags(business_type_key)
    template.updated_at       = utc_now_naive()
    await session.commit()
    await session.refresh(template)
    log.info(f"[PostTemplateService] قالب به پیش‌فرض بازنشانی شد: customer={customer_id}")
    return template
