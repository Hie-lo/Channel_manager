"""
هندلر خطاهای عمومی ربات
هر خطای پیش‌بینی نشده اینجا مدیریت میشه
"""

from telegram import Update, error
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

    # اطلاع به ادمین با جزئیات کامل
    if settings.ADMIN_CHAT_ID:
        try:
            # نام تابع/handler که خطا داشت
            handler_name = "نامشخص"
            if hasattr(error, "__traceback__") and error.__traceback__:
                import traceback
                tb = traceback.extract_tb(error.__traceback__)
                if tb:
                    last_frame = tb[-1]
                    handler_name = f"{last_frame.filename.split('/')[-1]}:{last_frame.name}:{last_frame.lineno}"

            # user info
            user_info = "نامشخص"
            if isinstance(update, Update) and update.effective_user:
                u = update.effective_user
                user_info = f"{u.first_name or ''} (id: {u.id})"

            error_text = str(error)[:500]

            # تشخیص پلتفرم از bot
            platform_name = "نامشخص"
            try:
                bot_username = context.bot.username or ""
                if bot_username:
                    platform_name = "تلگرام"  # پیش‌فرض
                # بله معمولاً toکن‌های متفاوتی داره
                if hasattr(context.bot, "base_url"):
                    base_url = str(context.bot.base_url or "")
                    if "bale" in base_url.lower():
                        platform_name = "بله"
                    elif "telegram" in base_url.lower():
                        platform_name = "تلگرام"
            except Exception:
                pass

            error_message = (
                f"⚠️ خطا در ربات\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🤖 پلتفرم: {platform_name}\n"
                f"👤 کاربر: {user_info}\n"
                f"📍 محل: {handler_name}\n"
                f"🔴 نوع: {type(error).__name__}\n"
                f"📝 پیام: {error_text}\n"
                f"━━━━━━━━━━━━━━━"
            )

            # تعیین admin_id بر اساس پلتفرم
            admin_id = settings.ADMIN_CHAT_ID
            if platform_name == "بله" and settings.BALE_ADMIN_CHAT_ID:
                admin_id = settings.BALE_ADMIN_CHAT_ID

            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=error_message,
                )
            except Exception as send_error:
                # اگه ارسال به ادمین هم fail شد، فقط لاگ کن (خودش رو دور نگیر)
                log.warning(
                    f"⚠️ نتونستم به ادمین ({admin_id}) در {platform_name} خطا رو بفرستم: {send_error}"
                )

        except Exception as e:
            log.error(f"خطا در آماده‌سازی پیام ادمین: {e}")