"""
ویرایشگر قالب پست — رابط کاربری اینلاین

منوی اصلی:
  • نمایش پیش‌نمایش قالب فعلی
  • ویرایش عنوان
  • فعال/غیرفعال کردن فیلدهای بدنه
  • ویرایش هشتگ‌های ثابت
  • ویرایش متن تماس
  • بازنشانی به پیش‌فرض

تمام تغییرات در PostTemplate دیتابیس ذخیره می‌شوند.
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from app.database.connection import AsyncSessionLocal
from app.database.models import CustomerStatus
from app.services.customer_service import get_customer_by_telegram_id
from app.services.post_template_service import (
    get_or_create_post_template,
    toggle_body_field,
    update_template_title,
    update_template_hashtags,
    update_template_contact,
    reset_template_to_default,
    get_post_template,
)
from app.services.business_service import get_business_config_for_customer
from app.bot.states.user_state import (
    UserState,
    set_user_state,
    get_user_state,
    get_user_data,
    clear_user_state,
)
from app.utils.logger import log


# ─────────────────────────────────────────────────────────────────────────────
# ورودی — دکمه "✏️ قالب پست" از منوی تنظیمات
# ─────────────────────────────────────────────────────────────────────────────

async def post_template_menu_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """نمایش منوی ویرایش قالب پست"""
    user = update.effective_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer or customer.customer_status != CustomerStatus.ACTIVE:
            await update.message.reply_text("❌ حساب شما فعال نیست.")
            return

        business_config = get_business_config_for_customer(customer)
        if not business_config:
            await update.message.reply_text("❌ کسب‌وکار تنظیم نشده.")
            return

        template = await get_or_create_post_template(
            session=session,
            customer_id=customer.id,
            business_type_key=customer.business_type_key or "other",
            contact_text=None,
        )

    text, keyboard = _build_main_menu(template)
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


# ─────────────────────────────────────────────────────────────────────────────
# منوی اصلی
# ─────────────────────────────────────────────────────────────────────────────

def _build_main_menu(template) -> tuple[str, InlineKeyboardMarkup]:
    body_count    = sum(1 for f in template.body_fields if f.get("enabled", True))
    hashtag_count = len(template.static_hashtags or [])

    text = (
        f"✏️ <b>ویرایش قالب پست</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"📌 <b>عنوان:</b> <code>{template.title_pattern}</code>\n"
        f"📝 <b>فیلدهای فعال:</b> {body_count} فیلد\n"
        f"#️⃣ <b>هشتگ‌های ثابت:</b> {hashtag_count} عدد\n"
        f"📞 <b>متن تماس:</b> {'دارد' if template.contact_text else 'ندارد'}\n"
        f"━━━━━━━━━━━━━━━"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📌 ویرایش عنوان",       callback_data="tpl_edit_title")],
        [InlineKeyboardButton("📝 فیلدهای بدنه",       callback_data="tpl_edit_fields")],
        [InlineKeyboardButton("#️⃣ هشتگ‌های ثابت",    callback_data="tpl_edit_hashtags")],
        [InlineKeyboardButton("📞 متن تماس",           callback_data="tpl_edit_contact")],
        [InlineKeyboardButton("👁 پیش‌نمایش",          callback_data="tpl_preview")],
        [InlineKeyboardButton("🔄 بازنشانی به پیش‌فرض", callback_data="tpl_reset")],
        [InlineKeyboardButton("🔙 بازگشت",             callback_data="posting_back")],
    ])

    return text, keyboard


async def post_template_main_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user_id)
        if not customer:
            return
        template = await get_or_create_post_template(
            session, customer.id, customer.business_type_key or "other"
        )

    text, keyboard = _build_main_menu(template)
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)


# ─────────────────────────────────────────────────────────────────────────────
# ویرایش عنوان
# ─────────────────────────────────────────────────────────────────────────────

async def tpl_edit_title_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    set_user_state(user_id, UserState.TPL_WAITING_TITLE)

    await query.edit_message_text(
        "📌 <b>ویرایش عنوان پست</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
        "الگوی عنوان جدید را بنویسید.\n\n"
        "📋 <b>placeholder های مجاز:</b>\n"
        "• <code>{product_name}</code> — نام محصول\n"
        "• <code>{brand}</code> — برند\n"
        "• <code>{price}</code> — قیمت\n\n"
        "مثال: <code>🧥 {brand} | {product_name}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ لغو", callback_data="tpl_menu")]
        ]),
    )


async def tpl_title_received_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """دریافت عنوان جدید از کاربر"""
    user = update.effective_user
    if get_user_state(user.id) != UserState.TPL_WAITING_TITLE:
        return

    new_title = update.message.text.strip()
    if not new_title:
        await update.message.reply_text("❌ عنوان نمی‌تواند خالی باشد.")
        return

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            return
        await update_template_title(session, customer.id, new_title)
        template = await get_post_template(session, customer.id)

    clear_user_state(user.id)
    text, keyboard = _build_main_menu(template)
    await update.message.reply_text(
        f"✅ عنوان ذخیره شد.\n\n{text}",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


# ─────────────────────────────────────────────────────────────────────────────
# فعال/غیرفعال فیلدهای بدنه
# ─────────────────────────────────────────────────────────────────────────────

async def tpl_edit_fields_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user_id)
        if not customer:
            return
        template = await get_or_create_post_template(
            session, customer.id, customer.business_type_key or "other"
        )

    keyboard = _build_fields_keyboard(template)
    await query.edit_message_text(
        "📝 <b>فیلدهای بدنه پست</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
        "روی هر فیلد بزنید تا فعال/غیرفعال شود:\n"
        "🟢 = فعال   🔴 = غیرفعال",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


def _build_fields_keyboard(template) -> InlineKeyboardMarkup:
    rows = []
    for f in (template.body_fields or []):
        key     = f.get("key", "")
        label   = f.get("label", key)
        enabled = f.get("enabled", True)
        icon    = "🟢" if enabled else "🔴"
        rows.append([InlineKeyboardButton(
            f"{icon} {label}",
            callback_data=f"tpl_toggle_{key[:40]}"
        )])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="tpl_menu")])
    return InlineKeyboardMarkup(rows)


async def tpl_toggle_field_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    field_key = query.data.replace("tpl_toggle_", "")

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user_id)
        if not customer:
            return
        template = await toggle_body_field(session, customer.id, field_key)

    if template:
        keyboard = _build_fields_keyboard(template)
        await query.edit_message_reply_markup(reply_markup=keyboard)


# ─────────────────────────────────────────────────────────────────────────────
# ویرایش هشتگ‌های ثابت
# ─────────────────────────────────────────────────────────────────────────────

async def tpl_edit_hashtags_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    set_user_state(user_id, UserState.TPL_WAITING_HASHTAGS)

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user_id)
        template = await get_post_template(session, customer.id) if customer else None

    current = " ".join(template.static_hashtags) if template and template.static_hashtags else "—"

    await query.edit_message_text(
        f"#️⃣ <b>ویرایش هشتگ‌های ثابت</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"هشتگ‌های فعلی:\n<code>{current}</code>\n\n"
        f"هشتگ‌های جدید را (با فاصله جدا شده) بنویسید:\n"
        f"مثال: <code>#پوشاک #لباس #مد</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ لغو", callback_data="tpl_menu")]
        ]),
    )


async def tpl_hashtags_received_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = update.effective_user
    if get_user_state(user.id) != UserState.TPL_WAITING_HASHTAGS:
        return

    raw = update.message.text.strip()
    hashtags = [t.strip() for t in raw.split() if t.strip().startswith("#")]

    if not hashtags:
        await update.message.reply_text(
            "❌ هیچ هشتگ معتبری پیدا نشد.\n"
            "هشتگ‌ها باید با # شروع شوند."
        )
        return

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            return
        await update_template_hashtags(session, customer.id, static_hashtags=hashtags)
        template = await get_post_template(session, customer.id)

    clear_user_state(user.id)
    text, keyboard = _build_main_menu(template)
    await update.message.reply_text(
        f"✅ هشتگ‌ها ذخیره شدند.\n\n{text}",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


# ─────────────────────────────────────────────────────────────────────────────
# ویرایش متن تماس
# ─────────────────────────────────────────────────────────────────────────────

async def tpl_edit_contact_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    set_user_state(user_id, UserState.TPL_WAITING_CONTACT)

    await query.edit_message_text(
        "📞 <b>ویرایش متن تماس</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
        "متن تماس را بنویسید.\n"
        "مثال: <code>📞 برای سفارش پیام دهید | @myshop</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑 حذف متن تماس", callback_data="tpl_clear_contact")],
            [InlineKeyboardButton("❌ لغو",           callback_data="tpl_menu")],
        ]),
    )


async def tpl_contact_received_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = update.effective_user
    if get_user_state(user.id) != UserState.TPL_WAITING_CONTACT:
        return

    contact = update.message.text.strip()

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            return
        await update_template_contact(session, customer.id, contact)
        template = await get_post_template(session, customer.id)

    clear_user_state(user.id)
    text, keyboard = _build_main_menu(template)
    await update.message.reply_text(
        f"✅ متن تماس ذخیره شد.\n\n{text}",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def tpl_clear_contact_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    clear_user_state(user_id)

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user_id)
        if not customer:
            return
        await update_template_contact(session, customer.id, "")
        template = await get_post_template(session, customer.id)

    text, keyboard = _build_main_menu(template)
    await query.edit_message_text(
        f"✅ متن تماس حذف شد.\n\n{text}",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


# ─────────────────────────────────────────────────────────────────────────────
# پیش‌نمایش
# ─────────────────────────────────────────────────────────────────────────────

async def tpl_preview_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user_id)
        if not customer:
            return
        template = await get_or_create_post_template(
            session, customer.id, customer.business_type_key or "other"
        )

    # محصول نمونه
    from app.services.post_builder import render_post
    sample_product = {
        "product_name":     "محصول نمونه",
        "brand":            "برند نمونه",
        "price":            350000,
        "stock_qty":        5,
        "description_manual": "توضیحات نمونه برای این محصول",
        "image_url":        None,
        "specs": {
            "color":    "مشکی",
            "size":     "M,L,XL",
            "material": "پنبه",
            "cpu":      "Intel i7",
            "ram":      "16GB",
            "storage":  "512GB SSD",
        },
    }

    result = render_post(sample_product, template)

    await query.edit_message_text(
        f"👁 <b>پیش‌نمایش پست نمونه</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"{result.text}\n\n"
        f"━━━━━━━━━━━━━━━",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت", callback_data="tpl_menu")]
        ]),
    )


# ─────────────────────────────────────────────────────────────────────────────
# بازنشانی
# ─────────────────────────────────────────────────────────────────────────────

async def tpl_reset_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🔄 <b>بازنشانی قالب</b>\n\n"
        "آیا مطمئن هستید؟ تمام تغییرات از بین می‌روند.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ بله، بازنشانی", callback_data="tpl_reset_confirm"),
                InlineKeyboardButton("❌ نه",           callback_data="tpl_menu"),
            ]
        ]),
    )


async def tpl_reset_confirm_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user_id)
        if not customer:
            return
        template = await reset_template_to_default(
            session, customer.id, customer.business_type_key or "other"
        )

    text, keyboard = _build_main_menu(template)
    await query.edit_message_text(
        f"✅ قالب به پیش‌فرض بازنشانی شد.\n\n{text}",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
