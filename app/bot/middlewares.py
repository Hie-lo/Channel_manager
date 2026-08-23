"""
لایه امنیتی و میان‌افزارها (Middlewares)
محافظت از ربات در برابر اسپم و حملات DDoS سطح اپلیکیشن
"""

from telegram import Update
from telegram.ext import ContextTypes, ApplicationHandlerStop
from app.utils.security import is_rate_limited
from app.utils.logger import log

# لیست ادمین‌ها برای مستثنی شدن از اسپم‌گارد (اختیاری)
from app.config import settings

async def global_anti_spam_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    این تابع به عنوان اولین گروه اجرا می‌شود (group=-1).
    هرگونه آپدیت (پیام، کالبک، فایل) را مانیتور می‌کند.
    """
    user = update.effective_user
    if not user:
        return

    # ادمین‌ها هیچ‌وقت لیمیت نمی‌شوند
    if user.id == settings.ADMIN_CHAT_ID or (settings.BALE_ADMIN_CHAT_ID and user.id == settings.BALE_ADMIN_CHAT_ID):
        return

    # محدودیت سخت‌گیرانه: حداکثر 8 درخواست در هر 5 ثانیه
    is_spamming = is_rate_limited(user.id, action="global_spam_guard", max_requests=8, time_window_seconds=5)

    if is_spamming:
        # جلوگیری از ارسال بی‌نهایت پیام هشدار
        if not context.user_data.get("spam_warned", False):
            try:
                msg_text = "⚠️ <b>سیستم امنیتی:</b> شما با سرعت زیادی در حال ارسال درخواست هستید. لطفاً ۵ ثانیه صبر کنید."
                if update.callback_query:
                    await update.callback_query.answer("⚠️ لطفاً آرام‌تر کلیک کنید!", show_alert=True)
                elif update.message:
                    await update.message.reply_text(msg_text, parse_mode="HTML")
                
                context.user_data["spam_warned"] = True
            except Exception as e:
                log.debug(f"خطا در ارسال پیام هشدار اسپم: {e}")
        
        log.warning(f"🛡️ [Spam Guard] آپدیت کاربر {user.id} مسدود شد.")
        
        # 🔥 این دستور اجرای تمام Handler های گروه‌های بعدی (0, 1, 2...) را متوقف می‌کند
        raise ApplicationHandlerStop()

    # اگر کاربر آرام شد، هشدار را ریست کن
    if context.user_data.get("spam_warned", False):
        context.user_data["spam_warned"] = False