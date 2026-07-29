"""
هندلرهای پشتیبانی مشتری
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from app.config import settings
from app.database.connection import AsyncSessionLocal
from app.database.models import CustomerStatus
from app.services.customer_service import get_customer_by_telegram_id
from app.bot.states.user_state import (
    UserState,
    set_user_state,
    get_user_state,
    get_user_data,
    clear_user_state,
)
from app.utils.logger import log


def _get_cancel_support_keyboard() -> InlineKeyboardMarkup:
    """کیبورد لغو"""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ لغو", callback_data="support_cancel")
    ]])


def _get_reply_support_keyboard(customer_telegram_id: int) -> InlineKeyboardMarkup:
    """کیبورد پاسخ ادمین"""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "💬 پاسخ",
            callback_data=f"support_reply_{customer_telegram_id}"
        )
    ]])


async def support_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش منوی پشتیبانی"""
    user = update.effective_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)

        if not customer or customer.customer_status != CustomerStatus.ACTIVE:
            await update.message.reply_text("❌ حساب شما فعال نیست. لطفاً /start بزنید.")
            return

    # تنظیم state
    set_user_state(user.id, UserState.WAITING_SUPPORT_MESSAGE)

    await update.message.reply_text(
        "💬 پشتیبانی\n"
        "━━━━━━━━━━━━━━━\n\n"
        "لطفاً سوال یا مشکل خودتون رو در یک پیام بنویسید.\n"
        "پیام مستقیم به پشتیبانی ارسال میشه.\n\n"
        "⚠️ نکات:\n"
        "• هر بار فقط یک پیام ارسال می‌کنید\n"
        "• برای ارسال پیام جدید، دوباره از منو استفاده کنید\n"
        "• پاسخ در همین ربات به شما ارسال میشه\n\n"
        "💡 مطمئن شوید سوالتون واضح و کامل باشه.",
        reply_markup=_get_cancel_support_keyboard(),
    )


async def support_message_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    دریافت پیام پشتیبانی از مشتری
    فقط وقتی state = WAITING_SUPPORT_MESSAGE
    """
    user = update.effective_user

    if get_user_state(user.id) != UserState.WAITING_SUPPORT_MESSAGE:
        return

    message_text = update.message.text

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)

    if not customer:
        await update.message.reply_text("❌ خطا!")
        clear_user_state(user.id)
        return

    # اطلاعات مشتری
    name = customer.first_name or ""
    if customer.last_name:
        name += f" {customer.last_name}"
    username_text = f"@{customer.username}" if customer.username else "ندارد"

    # ارسال به ادمین
    admin_text = (
        f"💬 پیام پشتیبانی جدید\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 مشتری: {name}\n"
        f"🔗 یوزرنیم: {username_text}\n"
        f"🆔 آیدی: {customer.telegram_user_id}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"📝 پیام:\n{message_text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    try:
        await context.bot.send_message(
            chat_id=settings.ADMIN_CHAT_ID,
            text=admin_text,
            reply_markup=_get_reply_support_keyboard(customer.telegram_user_id),
        )

        await update.message.reply_text(
            "✅ پیام شما به پشتیبانی ارسال شد!\n\n"
            "🕐 معمولاً در کمتر از ۱ روز کاری پاسخ می‌گیرید.\n"
            "پاسخ در همین ربات به شما ارسال میشه."
        )
    except Exception as e:
        log.error(f"خطا در ارسال پیام پشتیبانی: {e}")
        await update.message.reply_text(
            "❌ خطا در ارسال پیام!\n"
            "لطفاً دوباره تلاش کنید."
        )

    clear_user_state(user.id)


async def support_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """لغو ارسال پیام پشتیبانی"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    clear_user_state(user.id)

    await query.edit_message_text(
        "❌ لغو شد.\n\n"
        "هر وقت خواستید از منوی '💬 پشتیبانی' استفاده کنید."
    )


async def support_reply_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ادمین می‌خواد پاسخ بده"""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != settings.ADMIN_CHAT_ID:
        return

    customer_telegram_id = int(query.data.replace("support_reply_", ""))

    # ذخیره در state
    set_user_state(
        query.from_user.id,
        UserState.ADMIN_REPLYING_TO_SUPPORT,
        data={"target_customer_telegram_id": customer_telegram_id},
    )

    await query.message.reply_text(
        f"💬 پاسخ به مشتری\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🆔 آیدی: {customer_telegram_id}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"متن پاسخ رو ارسال کنید:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ لغو", callback_data="support_reply_cancel")
        ]]),
    )


async def support_reply_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """لغو پاسخ ادمین"""
    query = update.callback_query
    await query.answer()

    clear_user_state(query.from_user.id)

    await query.edit_message_text("❌ لغو شد.")


async def admin_reply_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    دریافت متن پاسخ ادمین
    فقط وقتی state = ADMIN_REPLYING_TO_SUPPORT
    """
    user = update.effective_user

    if user.id != settings.ADMIN_CHAT_ID:
        return

    if get_user_state(user.id) != UserState.ADMIN_REPLYING_TO_SUPPORT:
        return

    user_data = get_user_data(user.id)
    target_id = user_data.get("target_customer_telegram_id")

    if not target_id:
        await update.message.reply_text("❌ خطا!")
        clear_user_state(user.id)
        return

    reply_text = update.message.text

    # ارسال پاسخ به مشتری
    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=(
                f"💬 پاسخ پشتیبانی\n"
                f"━━━━━━━━━━━━━━━\n"
                f"{reply_text}\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"💡 اگه سوال دیگه‌ای دارید، دوباره از منوی\n"
                f"'💬 پشتیبانی' استفاده کنید."
            ),
        )
        await update.message.reply_text(
            f"✅ پاسخ به مشتری {target_id} ارسال شد."
        )
    except Exception as e:
        log.error(f"خطا در ارسال پاسخ به مشتری: {e}")
        await update.message.reply_text(
            f"❌ خطا در ارسال پاسخ:\n{str(e)[:200]}"
        )

    clear_user_state(user.id)