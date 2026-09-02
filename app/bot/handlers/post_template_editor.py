"""
انتخاب نمونه‌ی آماده‌ی پست — رابط کاربری اینلاین

مشتری خودش قالب نمی‌سازه؛ فقط از بین preset هایی که ادمین برای
نوع کسب‌وکارش طراحی کرده، یکی رو انتخاب می‌کنه و پیش‌نمایش می‌بینه.
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from app.database.connection import AsyncSessionLocal
from app.database.models import CustomerStatus
from app.services.customer_service import get_customer_by_telegram_id
from app.services.post_preset_service import (
    list_presets_for_customer,
    get_preset_by_id,
    get_selected_preset,
    select_preset_for_customer,
)
from app.utils.logger import log


# نمونه محصول برای پیش‌نمایش (وقتی مشتری هنوز محصولی ثبت نکرده)
_SAMPLE_PRODUCT = {
    "product_name": "محصول نمونه",
    "brand": "برند نمونه",
    "sku": "SAMPLE-001",
    "price": 350000,
    "stock_qty": 5,
    "description_custom": "توضیحات نمونه برای این محصول",
    "image_url": None,
    "specs": {
        "color": "مشکی",
        "size": "M,L,XL",
        "material": "پنبه",
        "cpu": "Intel i7",
        "ram": "16GB",
        "storage": "512GB SSD",
        "gpu": "RTX 3050",
        "screen": "15.6 اینچ",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# ورودی — دکمه "✏️ قالب پست" از منوی تنظیمات (callback_data="tpl_menu")
# ─────────────────────────────────────────────────────────────────────────────

async def post_template_menu_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """نمایش لیست نمونه‌های قابل‌انتخاب"""
    user = update.effective_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer or customer.customer_status != CustomerStatus.ACTIVE:
            await update.message.reply_text("❌ حساب شما فعال نیست.")
            return

        if not customer.business_type_key:
            await update.message.reply_text("❌ کسب‌وکار تنظیم نشده.")
            return

        text, keyboard = await _build_preset_list(session, customer)

    await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


async def post_template_main_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """بازگشت به لیست نمونه‌ها از callback (همون tpl_menu)"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user_id)
        if not customer:
            return
        text, keyboard = await _build_preset_list(session, customer)

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)


async def _build_preset_list(session, customer) -> tuple[str, InlineKeyboardMarkup]:
    """ساخت متن + کیبورد لیست preset ها"""
    presets = await list_presets_for_customer(
        session,
        business_type_key=customer.business_type_key,
        subcategory_key=None,  # عمومی؛ اگه بخوای فیلتر زیردسته‌ای دقیق‌تر، اینجا subcategory بده
    )
    selected = await get_selected_preset(session, customer.id)
    selected_id = selected.id if selected else None

    if not presets:
        text = (
            "📄 <b>انتخاب قالب پست</b>\n"
            "━━━━━━━━━━━━━━━\n\n"
            "فعلاً هیچ نمونه‌ی آماده‌ای برای کسب‌وکار شما تعریف نشده.\n"
            "به‌زودی نمونه‌های جدید اضافه می‌شن."
        )
        return text, InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت", callback_data="posting_back")]
        ])

    text = (
        "📄 <b>انتخاب قالب پست</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
        "یکی از نمونه‌های زیر رو انتخاب کن. با «👁 پیش‌نمایش» می‌تونی "
        "قبل از انتخاب ببینی پست‌هات دقیقاً چه شکلی می‌شن.\n"
        "━━━━━━━━━━━━━━━"
    )

    rows = []
    for preset in presets:
        mark = "✅ " if preset.id == selected_id else ""
        rows.append([
            InlineKeyboardButton(f"{mark}{preset.name_fa}", callback_data=f"tpl_preset_view_{preset.id}")
        ])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="posting_back")])

    return text, InlineKeyboardMarkup(rows)


# ─────────────────────────────────────────────────────────────────────────────
# نمایش جزئیات + پیش‌نمایش یک preset
# ─────────────────────────────────────────────────────────────────────────────

async def tpl_preset_view_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """نمایش دکمه‌های پیش‌نمایش/انتخاب برای یک preset مشخص"""
    query = update.callback_query
    await query.answer()

    preset_id = int(query.data.replace("tpl_preset_view_", ""))

    async with AsyncSessionLocal() as session:
        preset = await get_preset_by_id(session, preset_id)

    if not preset:
        await query.edit_message_text("❌ این نمونه دیگر در دسترس نیست.")
        return

    await query.edit_message_text(
        f"📄 <b>{preset.name_fa}</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"برای دیدن شکل واقعی پست، پیش‌نمایش رو بزن.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👁 پیش‌نمایش", callback_data=f"tpl_preset_preview_{preset.id}")],
            [InlineKeyboardButton("✅ انتخاب این قالب", callback_data=f"tpl_preset_select_{preset.id}")],
            [InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="tpl_menu")],
        ]),
    )


async def tpl_preset_preview_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """رندر preset روی یک محصول نمونه (یا محصول واقعی مشتری اگر داشته باشد)"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    preset_id = int(query.data.replace("tpl_preset_preview_", ""))

    async with AsyncSessionLocal() as session:
        preset = await get_preset_by_id(session, preset_id)
        if not preset:
            await query.edit_message_text("❌ این نمونه دیگر در دسترس نیست.")
            return

        customer = await get_customer_by_telegram_id(session, user_id)

        # اگه محصول واقعی داشته باشه، پیش‌نمایش با داده‌ی واقعی دقیق‌تره
        sample_data = _SAMPLE_PRODUCT
        if customer:
            from app.services.product_service import get_all_products_by_customer
            products = await get_all_products_by_customer(session, customer.id)
            if products:
                p = products[0]
                sample_data = {
                    "product_name": p.product_name,
                    "brand": (p.specs or {}).get("brand", "برند نمونه"),
                    "sku": p.sku,
                    "price": int(p.price),
                    "stock_qty": p.stock_qty,
                    "description_custom": p.description_custom or _SAMPLE_PRODUCT["description_custom"],
                    "image_url": p.image_url,
                    "specs": p.specs or _SAMPLE_PRODUCT["specs"],
                }

    # 🔗 نکته: render_post باید بتونه مستقیم از روی template_text خام preset رندر کنه،
    # نه از روی مدل PostTemplate قدیمی. دقیقاً همینجا باید به post_builder.py وصل بشه.
    from app.services.post_builder import render_post_from_text

    try:
        rendered_text = render_post_from_text(sample_data, preset.template_text)
    except Exception as e:
        log.error(f"خطا در رندر preset {preset_id}: {e}", exc_info=True)
        rendered_text = f"⚠️ خطا در پیش‌نمایش این قالب: {str(e)[:150]}"

    await query.edit_message_text(
        f"👁 <b>پیش‌نمایش: {preset.name_fa}</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"{rendered_text}\n\n"
        f"━━━━━━━━━━━━━━━",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ انتخاب این قالب", callback_data=f"tpl_preset_select_{preset.id}")],
            [InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="tpl_menu")],
        ]),
    )


# ─────────────────────────────────────────────────────────────────────────────
# انتخاب نهایی preset
# ─────────────────────────────────────────────────────────────────────────────

async def tpl_preset_select_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    preset_id = int(query.data.replace("tpl_preset_select_", ""))

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user_id)
        if not customer:
            return

        preset = await get_preset_by_id(session, preset_id)
        if not preset or not preset.is_active:
            await query.edit_message_text("❌ این نمونه دیگر در دسترس نیست.")
            return

        await select_preset_for_customer(session, customer.id, preset_id)

    await query.edit_message_text(
        f"✅ قالب «{preset.name_fa}» برای پست‌های شما انتخاب شد.\n\n"
        f"از این به بعد محصولات با همین ساختار پست می‌شن.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت به تنظیمات", callback_data="posting_back")]
        ]),
    )