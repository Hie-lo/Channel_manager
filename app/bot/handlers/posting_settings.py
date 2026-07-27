"""
هندلرهای تنظیمات ارسال پست
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from app.database.connection import AsyncSessionLocal
from app.database.models import CustomerStatus
from app.services.customer_service import get_customer_by_telegram_id
from app.services.posting_settings_service import (
    get_or_create_posting_settings,
    set_auto_publish,
    update_interval,
    update_posting_hours,
    calculate_posts_per_day,
    set_auto_ai_description
)
from app.utils.logger import log


# گزینه‌های از پیش تعریف شده
INTERVAL_OPTIONS = [1, 2, 3, 4, 6, 8, 12, 24]


def _get_settings_keyboard(settings_obj) -> InlineKeyboardMarkup:
    """کیبورد اصلی تنظیمات"""
    auto_status = "🟢 فعال" if settings_obj.auto_publish_enabled else "🔴 غیرفعال"
    ai_status = "🟢 فعال" if settings_obj.auto_ai_description else "🔴 غیرفعال"

    keyboard = [
        [
            InlineKeyboardButton(
                f"حالت ارسال: {auto_status}",
                callback_data="posting_toggle_auto",
            )
        ],
    ]

    if settings_obj.auto_publish_enabled:
        keyboard.append([
            InlineKeyboardButton(
                f"⏱ فاصله: هر {settings_obj.interval_hours} ساعت",
                callback_data="posting_set_interval",
            )
        ])
        keyboard.append([
            InlineKeyboardButton(
                f"🕐 ساعت‌ها: {settings_obj.posting_start_hour}:00 - {settings_obj.posting_end_hour}:00",
                callback_data="posting_set_hours",
            )
        ])

    # دکمه AI خودکار (همیشه)
    keyboard.append([
        InlineKeyboardButton(
            f"🤖 AI خودکار: {ai_status}",
            callback_data="posting_toggle_ai",
        )
    ])

    return InlineKeyboardMarkup(keyboard)


async def posting_settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش منوی تنظیمات ارسال"""

    user = update.effective_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)

        if not customer or customer.customer_status != CustomerStatus.ACTIVE:
            await update.message.reply_text("❌ حساب شما فعال نیست.")
            return

        settings_obj = await get_or_create_posting_settings(session, customer.id)

    text = _build_settings_text(settings_obj)

    await update.message.reply_text(
        text,
        reply_markup=_get_settings_keyboard(settings_obj),
    )


def _build_settings_text(settings_obj) -> str:
    """متن نمایش تنظیمات"""
    auto_text = "🟢 خودکار" if settings_obj.auto_publish_enabled else "🔴 دستی"
    ai_text = "🟢 فعال" if settings_obj.auto_ai_description else "🔴 غیرفعال"

    text = (
        f"⚙️ تنظیمات ارسال پست\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🎯 حالت ارسال: {auto_text}\n"
    )

    if settings_obj.auto_publish_enabled:
        posts_per_day = calculate_posts_per_day(settings_obj)
        text += (
            f"⏱ فاصله بین پست‌ها: هر {settings_obj.interval_hours} ساعت\n"
            f"🕐 ساعت مجاز: {settings_obj.posting_start_hour}:00 تا {settings_obj.posting_end_hour}:00\n"
            f"📊 تقریباً {posts_per_day} پست در روز\n"
        )

    text += (
        f"━━━━━━━━━━━━━━━\n"
        f"🤖 AI خودکار: {ai_text}\n"
    )

    if settings_obj.auto_ai_description:
        text += (
            f"\n💡 موقع ارسال پست، AI خودکار توضیحات\n"
            f"محصولات بدون توضیحات رو تولید می‌کنه.\n"
            f"⚠️ هر تولید = ۱ توکن AI\n"
        )
    else:
        text += (
            f"\n💡 توضیحات محصولات دستی یا از اکسل\n"
            f"استفاده می‌شوند (بدون AI).\n"
        )

    text += (
        f"━━━━━━━━━━━━━━━\n\n"
    )

    if settings_obj.auto_publish_enabled:
        text += (
            f"💡 ربات در ساعت‌های مجاز و طبق فاصله تعیین شده،\n"
            f"محصولات منتشر نشده رو خودکار پست می‌کنه.\n\n"
            f"⚠️ نکته: اگه محصولی قبلاً منتشر شده،\n"
            f"دوباره پست نمیشه (فقط قیمت آپدیت میشه)."
        )
    else:
        text += (
            f"💡 در حالت دستی، شما باید محصولات را\n"
            f"به صورت تک به تک از منوی '📦 مدیریت محصولات' ارسال کنید.\n\n"
            f"برای فعال کردن ارسال خودکار، دکمه بالا رو بزنید."
        )

    return text


async def posting_toggle_auto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تغییر حالت ارسال (دستی ↔ خودکار)"""

    query = update.callback_query
    await query.answer()

    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            return

        settings_obj = await get_or_create_posting_settings(session, customer.id)
        new_state = not settings_obj.auto_publish_enabled
        settings_obj = await set_auto_publish(session, customer.id, new_state)

    text = _build_settings_text(settings_obj)

    if new_state:
        text += "\n\n✅ ارسال خودکار فعال شد!"
    else:
        text += "\n\n🔴 ارسال خودکار غیرفعال شد."

    await query.edit_message_text(
        text,
        reply_markup=_get_settings_keyboard(settings_obj),
    )


async def posting_set_interval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش گزینه‌های فاصله ارسال"""

    query = update.callback_query
    await query.answer()

    keyboard = []
    for hours in INTERVAL_OPTIONS:
        keyboard.append([
            InlineKeyboardButton(
                f"هر {hours} ساعت",
                callback_data=f"posting_interval_{hours}",
            )
        ])
    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت", callback_data="posting_back"),
    ])

    await query.edit_message_text(
        "⏱ فاصله بین پست‌ها را انتخاب کنید:\n\n"
        "💡 توصیه: هر ۳-۶ ساعت مناسبه\n"
        "کمتر = پست بیشتر ولی خستگی مخاطب\n"
        "بیشتر = پست کمتر ولی بازدید بهتر",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def posting_interval_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """کاربر یکی از گزینه‌های فاصله رو انتخاب کرد"""

    query = update.callback_query
    await query.answer()

    user = query.from_user
    hours = int(query.data.replace("posting_interval_", ""))

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            return

        settings_obj = await update_interval(session, customer.id, hours)

    text = _build_settings_text(settings_obj)
    text += f"\n\n✅ فاصله ارسال به {hours} ساعت تنظیم شد!"

    await query.edit_message_text(
        text,
        reply_markup=_get_settings_keyboard(settings_obj),
    )


async def posting_set_hours_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش گزینه‌های ساعت مجاز"""

    query = update.callback_query
    await query.answer()

    # پیشنهادهای رایج
    presets = [
        ("🌅 صبح تا شب (9-22)", 9, 22),
        ("🌄 صبح زود تا شب (7-23)", 7, 23),
        ("☀️ ظهر تا شب (12-22)", 12, 22),
        ("🌞 تمام روز (0-24)", 0, 24),
        ("🕐 ساعات کاری (9-18)", 9, 18),
    ]

    keyboard = []
    for label, start, end in presets:
        keyboard.append([
            InlineKeyboardButton(
                label,
                callback_data=f"posting_hours_{start}_{end}",
            )
        ])
    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت", callback_data="posting_back"),
    ])

    await query.edit_message_text(
        "🕐 ساعت‌های مجاز ارسال را انتخاب کنید:\n\n"
        "💡 ربات فقط در این ساعت‌ها پست ارسال می‌کنه",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def posting_hours_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """کاربر ساعت مجاز رو انتخاب کرد"""

    query = update.callback_query
    await query.answer()

    user = query.from_user
    # posting_hours_9_22
    parts = query.data.replace("posting_hours_", "").split("_")
    start_hour = int(parts[0])
    end_hour = int(parts[1])

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            return

        settings_obj = await update_posting_hours(session, customer.id, start_hour, end_hour)

    text = _build_settings_text(settings_obj)
    text += f"\n\n✅ ساعت‌های ارسال به {start_hour}:00 - {end_hour}:00 تنظیم شد!"

    await query.edit_message_text(
        text,
        reply_markup=_get_settings_keyboard(settings_obj),
    )


async def posting_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بازگشت به منوی اصلی تنظیمات"""

    query = update.callback_query
    await query.answer()

    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            return

        settings_obj = await get_or_create_posting_settings(session, customer.id)

    await query.edit_message_text(
        _build_settings_text(settings_obj),
        reply_markup=_get_settings_keyboard(settings_obj),
    )

async def posting_toggle_ai_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تغییر حالت AI خودکار"""

    query = update.callback_query
    await query.answer()

    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            return

        settings_obj = await get_or_create_posting_settings(session, customer.id)
        new_state = not settings_obj.auto_ai_description
        settings_obj = await set_auto_ai_description(session, customer.id, new_state)

    text = _build_settings_text(settings_obj)

    if new_state:
        text += (
            f"\n\n✅ AI خودکار فعال شد!\n"
            f"━━━━━━━━━━━━━━━\n"
            f"⚠️ توجهات مهم:\n"
            f"• هر تولید = ۱ توکن AI\n"
            f"• برای محصولاتی که توضیحات ندارن اجرا میشه\n"
            f"• AI ممکنه اشتباه یا خطای جزئی داشته باشه\n"
            f"• اگه توکن کافی نداشتی، پست بدون AI میره\n"
            f"• متن‌های AI بعد از تولید ذخیره می‌شن\n\n"
            f"💡 توصیه: قبل از استفاده، توکن کافی داشته باش."
        )
    else:
        text += "\n\n🔴 AI خودکار غیرفعال شد."

    await query.edit_message_text(
        text,
        reply_markup=_get_settings_keyboard(settings_obj),
    )