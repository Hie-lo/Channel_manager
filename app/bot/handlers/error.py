"""
هندلر مرکزی خطاها (Error Handler)
"""

from telegram import Update
from telegram.ext import ContextTypes

from app.config import settings
from app.utils.logger import log


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندلر مرکزی خطاها"""

    error = context.error
    log.error(f"خطا در پردازش آپدیت: {type(error).__name__}: {error}", exc_info=error)

    # پیام به کاربر
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ متأسفانه خطایی در پردازش درخواست شما رخ داد.\n"
                "لطفاً دوباره تلاش کنید.\n\n"
                "اگر مشکل ادامه داشت با پشتیبانی تماس بگیرید."
            )
        except Exception as e:
            log.error(f"خطا در ارسال پیام به کاربر: {e}")

    # اطلاع به ادمین
    if settings.ADMIN_CHAT_ID:
        try:
            handler_name = "نامشخص"
            if hasattr(error, "__traceback__") and error.__traceback__:
                import traceback
                tb = traceback.extract_tb(error.__traceback__)
                if tb:
                    last_frame = tb[-1]
                    handler_name = f"{last_frame.filename.split('/')[-1]}:{last_frame.name}:{last_frame.lineno}"

            user_info = "نامشخص"
            if isinstance(update, Update) and update.effective_user:
                u = update.effective_user
                user_info = f"{u.first_name or ''} (id: {u.id})"

            # تشخیص پلتفرم از روی context
            platform_name = "تلگرام"
            if hasattr(context.bot, "base_url"):
                base_url = str(getattr(context.bot, "base_url", "") or "")
                if "bale" in base_url.lower():
                    platform_name = "بله"

            # انتخاب آیدی ادمین مناسب
            admin_id = settings.ADMIN_CHAT_ID
            if platform_name == "بله" and settings.BALE_ADMIN_CHAT_ID:
                admin_id = settings.BALE_ADMIN_CHAT_ID

            error_type = type(error).__name__ if error else "UnknownError"
            error_details = str(error) if error else "بدون جزئیات"

            error_message = (
                f"⚠️ <b>خطا در ربات</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🤖 پلتفرم: {platform_name}\n"
                f"👤 کاربر: {user_info}\n"
                f"📍 محل: {handler_name}\n"
                f"🔴 نوع خطا: {error_type}\n"
                f"📝 شرح: {error_details[:400]}\n"
                f"━━━━━━━━━━━━━━━"
            )

            await context.bot.send_message(
                chat_id=admin_id,
                text=error_message,
                parse_mode="HTML"
            )
        except Exception as send_err:
            log.warning(f"نتوانستیم خطا را به ادمین ارسال کنیم: {send_err}")