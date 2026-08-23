"""
میان‌افزار ضد اسپم سراسری (Global Anti-Spam Middleware)
"""
from telegram import Update
from telegram.ext import ContextTypes, ApplicationHandlerStop
from app.utils.security import check_user_spam
from app.utils.logger import log


async def global_anti_spam_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    بررسی تمامی آپدیت‌ها قبل از رسیدن به هندلرها
    """
    user = update.effective_user
    if not user:
        return

    is_blocked, remaining_seconds = check_user_spam(user.id)

    if is_blocked:
        log.warning(f"🛡️ [Spam Blocked] آپدیت کاربر {user.id} ({user.first_name}) مسدود شد. زمان باقیمانده: {remaining_seconds}s")

        # ارسال هشدار به کاربر (فقط یک‌بار در طول زمان جریمه)
        if not context.user_data.get("spam_blocked_notice_sent", False):
            try:
                msg = (
                    f"⛔ <b>سیستم امنیتی (Anti-Spam)</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"شما بیش از حد مجاز کلیک/پیام فرستاده‌اید.\n"
                    f"حساب شما به مدت <b>{remaining_seconds} ثانیه</b> فریز شد.\n"
                    f"لطفاً صبور باشید."
                )
                if update.callback_query:
                    await update.callback_query.answer(f"⚠️ حساب شما {remaining_seconds} ثانیه فریز شد!", show_alert=True)
                elif update.message:
                    await update.message.reply_text(msg, parse_mode="HTML")
                
                context.user_data["spam_blocked_notice_sent"] = True
            except Exception as e:
                log.debug(f"خطا در ارسال پیام هشدار اسپم: {e}")

        # ⛔ متوقف کردن کامل زنجیره هندلرها
        raise ApplicationHandlerStop()

    # اگر کاربر مسدود نیست، پرچم هشدار را ریست کن
    if context.user_data.get("spam_blocked_notice_sent", False):
        context.user_data["spam_blocked_notice_sent"] = False