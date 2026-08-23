"""
لایه امنیتی و میان‌افزارها (Middlewares)
محافظت از ربات در برابر اسپم و حملات DDoS سطح اپلیکیشن
"""

from telegram import Update
from telegram.ext import ContextTypes, ApplicationHandlerStop
from app.utils.security import is_rate_limited
from app.utils.logger import log

async def global_anti_spam_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    این تابع قبل از تمام هندلرهای دیگر اجرا می‌شود.
    اگر کاربر اسپم کند، اجرای بقیه هندلرها متوقف می‌شود.
    """
    user = update.effective_user
    if not user:
        return

    # قانون امنیتی: حداکثر ۱۲ درخواست (پیام/کلیک) در هر ۱۰ ثانیه برای هر کاربر
    is_spamming = is_rate_limited(user.id, action="global_spam_guard", max_requests=12, time_window_seconds=10)

    if is_spamming:
        # اگر کاربر در حال اسپم است
        if not context.user_data.get("spam_warned", False):
            try:
                # فقط یک‌بار هشدار می‌دهیم تا خودش تبدیل به اسپم نشود
                if update.message:
                    await update.message.reply_text("⚠️ <b>سیستم امنیتی:</b> شما با سرعت زیادی در حال ارسال درخواست هستید. لطفاً چند ثانیه صبر کنید.", parse_mode="HTML")
                elif update.callback_query:
                    await update.callback_query.answer("⚠️ لطفاً آرام‌تر کلیک کنید!", show_alert=True)
                
                context.user_data["spam_warned"] = True
            except Exception:
                pass
        
        log.warning(f"🛡️ [Spam Guard] درخواست‌های کاربر {user.id} مسدود شد.")
        
        # ⛔ متوقف کردن چرخه آپدیت تلگرام (هیچ هندلر دیگری اجرا نخواهد شد)
        raise ApplicationHandlerStop()

    # اگر کاربر اسپم نمی‌کند، وضعیت هشدار را ریست می‌کنیم
    if context.user_data.get("spam_warned", False):
        context.user_data["spam_warned"] = False