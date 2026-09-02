"""
پنل مدیریت نمونه‌های آماده‌ی پست (Post Template Presets) — فقط ادمین

ادمین از اینجا:
  • برای هر نوع کسب‌وکار، چند نمونه‌ی پست تعریف می‌کند
  • نمونه‌ها را فعال/غیرفعال یا حذف می‌کند
  • متن هر نمونه دقیقاً همون فرمت فایل‌های .txt فعلی‌ست (با {placeholder})
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from app.config import settings
from app.database.connection import AsyncSessionLocal
from app.business.config import get_all_businesses
from app.services.post_preset_service import (
    create_preset,
    get_preset_by_id,
    list_all_presets_for_admin,
    set_preset_active,
    delete_preset,
    rename_preset,
    update_preset_text,
)
from app.bot.states.user_state import (
    UserState,
    set_user_state,
    get_user_state,
    get_user_data,
    clear_user_state,
)
from app.utils.logger import log


def _is_admin(user_id: int) -> bool:
    return user_id == settings.ADMIN_CHAT_ID


# ─────────────────────────────────────────────────────────────────────────────
# ورودی — دکمه "🎨 قالب‌های پست" از منوی ادمین
# ─────────────────────────────────────────────────────────────────────────────

async def admin_presets_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """انتخاب نوع کسب‌وکار برای مدیریت preset هاش"""
    user = update.effective_user
    if not _is_admin(user.id):
        return

    keyboard = _build_business_select_keyboard()
    await update.message.reply_text(
        "🎨 <b>مدیریت نمونه‌های پست</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
        "برای کدوم نوع کسب‌وکار می‌خوای preset ها رو مدیریت کنی؟",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


def _build_business_select_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for biz in get_all_businesses():
        rows.append([InlineKeyboardButton(
            f"{biz.emoji} {biz.name_fa}",
            callback_data=f"padm_biz_{biz.key}",
        )])
    return InlineKeyboardMarkup(rows)


async def admin_presets_biz_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش لیست preset های یک کسب‌وکار"""
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    business_type_key = query.data.replace("padm_biz_", "")

    async with AsyncSessionLocal() as session:
        presets = await list_all_presets_for_admin(session, business_type_key)

    text, keyboard = _build_preset_list_view(business_type_key, presets)
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)


def _build_preset_list_view(business_type_key: str, presets: list) -> tuple[str, InlineKeyboardMarkup]:
    if not presets:
        text = (
            f"🎨 <b>preset های «{business_type_key}»</b>\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"هنوز هیچ نمونه‌ای تعریف نشده."
        )
    else:
        text = (
            f"🎨 <b>preset های «{business_type_key}»</b>\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"روی هر کدوم بزن برای مدیریت.\n"
            f"🟢 = فعال (مشتری می‌بینتش)   🔴 = غیرفعال"
        )

    rows = []
    for p in presets:
        icon = "🟢" if p.is_active else "🔴"
        rows.append([InlineKeyboardButton(
            f"{icon} {p.name_fa}", callback_data=f"padm_view_{p.id}"
        )])
    rows.append([InlineKeyboardButton("➕ افزودن preset جدید", callback_data=f"padm_new_{business_type_key}")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="padm_root")])

    return text, InlineKeyboardMarkup(rows)


async def admin_presets_root_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بازگشت به انتخاب نوع کسب‌وکار"""
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    keyboard = _build_business_select_keyboard()
    await query.edit_message_text(
        "🎨 <b>مدیریت نمونه‌های پست</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
        "برای کدوم نوع کسب‌وکار می‌خوای preset ها رو مدیریت کنی؟",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


# ─────────────────────────────────────────────────────────────────────────────
# مشاهده / مدیریت یک preset مشخص
# ─────────────────────────────────────────────────────────────────────────────

async def admin_preset_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    preset_id = int(query.data.replace("padm_view_", ""))

    async with AsyncSessionLocal() as session:
        preset = await get_preset_by_id(session, preset_id)

    if not preset:
        await query.edit_message_text("❌ این preset دیگر وجود ندارد.")
        return

    text = (
        f"📄 <b>{preset.name_fa}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🏢 کسب‌وکار: {preset.business_type_key}\n"
        f"🗂 زیردسته: {preset.subcategory_key or 'همه'}\n"
        f"📊 وضعیت: {'🟢 فعال' if preset.is_active else '🔴 غیرفعال'}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"<b>متن قالب:</b>\n<code>{preset.template_text}</code>"
    )

    toggle_label = "🔴 غیرفعال کن" if preset.is_active else "🟢 فعال کن"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ ویرایش متن", callback_data=f"padm_edit_text_{preset.id}")],
        [InlineKeyboardButton("✏️ تغییر نام", callback_data=f"padm_edit_name_{preset.id}")],
        [InlineKeyboardButton(toggle_label, callback_data=f"padm_toggle_{preset.id}")],
        [InlineKeyboardButton("🗑 حذف preset", callback_data=f"padm_delete_{preset.id}")],
        [InlineKeyboardButton("🔙 بازگشت به لیست", callback_data=f"padm_biz_{preset.business_type_key}")],
    ])

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)


async def admin_preset_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    preset_id = int(query.data.replace("padm_toggle_", ""))

    async with AsyncSessionLocal() as session:
        preset = await get_preset_by_id(session, preset_id)
        if not preset:
            await query.edit_message_text("❌ این preset دیگر وجود ندارد.")
            return
        preset = await set_preset_active(session, preset_id, not preset.is_active)

    # بازگشت به همون صفحه‌ی preset با وضعیت آپدیت‌شده
    update.callback_query.data = f"padm_view_{preset_id}"
    await admin_preset_view_callback(update, context)


async def admin_preset_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    preset_id = int(query.data.replace("padm_delete_", ""))

    async with AsyncSessionLocal() as session:
        preset = await get_preset_by_id(session, preset_id)
        if not preset:
            await query.edit_message_text("❌ این preset دیگر وجود ندارد.")
            return
        business_type_key = preset.business_type_key
        deleted = await delete_preset(session, preset_id)

    if not deleted:
        await query.edit_message_text(
            "⚠️ این preset حذف نشد چون حداقل یک مشتری فعلاً انتخابش کرده.\n"
            "به‌جاش می‌تونی غیرفعالش کنی تا دیگه توی لیست انتخاب مشتری‌های جدید نباشه.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔴 غیرفعال کن", callback_data=f"padm_toggle_{preset_id}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data=f"padm_biz_{business_type_key}")],
            ]),
        )
        return

    async with AsyncSessionLocal() as session:
        presets = await list_all_presets_for_admin(session, business_type_key)
    text, keyboard = _build_preset_list_view(business_type_key, presets)
    await query.edit_message_text(f"✅ حذف شد.\n\n{text}", parse_mode="HTML", reply_markup=keyboard)


# ─────────────────────────────────────────────────────────────────────────────
# افزودن preset جدید
# ─────────────────────────────────────────────────────────────────────────────

async def admin_preset_new_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """شروع فرآیند افزودن preset — گرفتن اسم"""
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    business_type_key = query.data.replace("padm_new_", "")
    set_user_state(
        query.from_user.id,
        UserState.PADM_WAITING_NAME,
        data={"business_type_key": business_type_key},
    )

    await query.edit_message_text(
        f"➕ <b>افزودن preset جدید برای «{business_type_key}»</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"اول یه اسم کوتاه براش بفرست (چیزی که مشتری می‌بینه، مثلاً «حرفه‌ای با گارانتی»).",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ لغو", callback_data=f"padm_biz_{business_type_key}")]
        ]),
    )


async def admin_preset_name_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دریافت اسم preset جدید، سپس درخواست متن قالب"""
    user = update.effective_user
    if get_user_state(user.id) != UserState.PADM_WAITING_NAME:
        return

    name = update.message.text.strip()
    if not name:
        await update.message.reply_text("❌ اسم نمی‌تونه خالی باشه.")
        return

    data = get_user_data(user.id)
    data["name_fa"] = name
    set_user_state(user.id, UserState.PADM_WAITING_TEXT, data=data)

    await update.message.reply_text(
        "📄 <b>حالا متن کامل قالب رو بفرست</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
        "دقیقاً مثل فایل‌های .txt فعلی، با <code>{placeholder}</code> بنویسش.\n"
        "مثال: <code>{product_name}</code>, <code>{price}</code>, "
        "<code>{specs.cpu}</code>, <code>{description_custom}</code>, "
        "<code>{contact}</code>, <code>{hashtags}</code>",
        parse_mode="HTML",
    )


async def admin_preset_text_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دریافت متن قالب و ذخیره‌ی نهایی preset"""
    user = update.effective_user
    if get_user_state(user.id) != UserState.PADM_WAITING_TEXT:
        return

    template_text = update.message.text
    if not template_text or not template_text.strip():
        await update.message.reply_text("❌ متن قالب نمی‌تونه خالی باشه.")
        return

    data = get_user_data(user.id)
    business_type_key = data.get("business_type_key")
    name_fa = data.get("name_fa", "preset بدون‌نام")

    async with AsyncSessionLocal() as session:
        preset = await create_preset(
            session,
            business_type_key=business_type_key,
            name_fa=name_fa,
            template_text=template_text,
        )

    clear_user_state(user.id)
    await update.message.reply_text(
        f"✅ preset «{preset.name_fa}» ساخته شد و همین الان برای مشتری‌ها فعاله."
    )


# ─────────────────────────────────────────────────────────────────────────────
# ویرایش نام / متن یک preset موجود
# ─────────────────────────────────────────────────────────────────────────────

async def admin_preset_edit_name_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    preset_id = int(query.data.replace("padm_edit_name_", ""))
    set_user_state(query.from_user.id, UserState.PADM_WAITING_RENAME, data={"preset_id": preset_id})

    await query.edit_message_text(
        "✏️ اسم جدید رو بفرست:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ لغو", callback_data=f"padm_view_{preset_id}")]
        ]),
    )


async def admin_preset_rename_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if get_user_state(user.id) != UserState.PADM_WAITING_RENAME:
        return

    new_name = update.message.text.strip()
    data = get_user_data(user.id)
    preset_id = data.get("preset_id")

    async with AsyncSessionLocal() as session:
        await rename_preset(session, preset_id, new_name)

    clear_user_state(user.id)
    await update.message.reply_text(f"✅ اسم preset به «{new_name}» تغییر کرد.")


async def admin_preset_edit_text_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not _is_admin(query.from_user.id):
        return

    preset_id = int(query.data.replace("padm_edit_text_", ""))
    set_user_state(query.from_user.id, UserState.PADM_WAITING_EDIT_TEXT, data={"preset_id": preset_id})

    await query.edit_message_text(
        "✏️ متن جدید کامل قالب رو بفرست (جایگزین متن قبلی می‌شه):",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ لغو", callback_data=f"padm_view_{preset_id}")]
        ]),
    )


async def admin_preset_edit_text_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if get_user_state(user.id) != UserState.PADM_WAITING_EDIT_TEXT:
        return

    new_text = update.message.text
    data = get_user_data(user.id)
    preset_id = data.get("preset_id")

    async with AsyncSessionLocal() as session:
        await update_preset_text(session, preset_id, new_text)

    clear_user_state(user.id)
    await update.message.reply_text("✅ متن preset آپدیت شد.")