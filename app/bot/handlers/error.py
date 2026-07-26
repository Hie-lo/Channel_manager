"""
هندلر خطاهای عمومی ربات
هر خطای پیش‌بینی نشده اینجا مدیریت میشه
"""

from telegram import Update
from telegram.ext import ContextTypes

from app.config import settings
from app.utils.logger import log


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندلر مرکزی خطاها"""

    # لاگ خطا
    log.error(f"خطا در پردازش آپدیت: {context.error}", exc_info=context.error)

    # پیام به کاربر (اگر update معتبر باشد)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ متأسفانه خطایی رخ داد.\n"
                "لطفاً دوباره تلاش کنید.\n\n"
                "اگر مشکل ادامه داشت با پشتیبانی تماس بگیرید."
            )
        except Exception as e:
            log.error(f"خطا در ارسال پیام خطا به کاربر: {e}")

    # اطلاع به ادمین
    if settings.ADMIN_CHAT_ID:
        try:
            error_text = str(context.error)[:500]  # حداکثر 500 کاراکتر
            await context.bot.send_message(
                chat_id=settings.ADMIN_CHAT_ID,
                text=(
                    f"⚠️ خطا در ربات\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"📝 خطا: {error_text}\n"
                    f"━━━━━━━━━━━━━━━"
                ),
            )
        except Exception as e:
            log.error(f"خطا در ارسال به ادمین: {e}")