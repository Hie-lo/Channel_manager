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
    این تابع قبل از تمام هندلرها در گروه 1- اجرا می‌شود.
    هرگونه آپدیت (پیام متنی، کلیک روی دکمه، ارسال فایل) را اسکن می‌کند.
    """
    user = update.effective_user
    if not user:
        return

    # 🛡️ قانون امنیتی سخت‌گیرانه: حداکثر ۵ درخواست در ۳ ثانیه برای هر کاربر
    is_spamming = is_rate_limited(
        user_id=user.id, 
        action="global_anti_spam", 
        max_requests=5, 
        time_window_seconds=3
    )

    if is_spamming:
        log.warning(f"🛡️ [Anti-Spam Guard] درخواست‌های کاربر {user.id} ({user.first_name}) مسدود شد.")

        # ارسال پیام هشدار (فقط یک‌بار در هر پنجره اسپم)
        if not context.user_data.get("spam_warning_sent", False):
            try:
                msg_text = (
                    "⛔ <b>سیستم امنیتی (Anti-Spam)</b>\n"
                    "━━━━━━━━━━━━━━━\n"
                    "درخواست‌های شما با سرعت بیش از حد مجاز ارسال شده‌اند.\n"
                    "لطفاً <b>۳ ثانیه</b> منتظر بمانید."
                )
                if update.callback_query:
                    await update.callback_query.answer("⚠️ اسپم شناسایی شد! ۳ ثانیه صبر کنید.", show_alert=True)
                elif update.message:
                    await update.message.reply_text(msg_text, parse_mode="HTML")
                
                context.user_data["spam_warning_sent"] = True
            except Exception as e:
                log.debug(f"خطا در ارسال پیام هشدار اسپم: {e}")

        # 🔥 توقف کامل پردازش: تلگرام/بله اجازه اجرای هیچ هندلری را برای این آپدیت نخواهند داد
        raise ApplicationHandlerStop()

    # اگر کاربر سرعتش را کم کرد، پرچم هشدار پاک می‌شود
    if context.user_data.get("spam_warning_sent", False):
        context.user_data["spam_warning_sent"] = False