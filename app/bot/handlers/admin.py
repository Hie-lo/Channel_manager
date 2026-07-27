"""
هندلرهای مخصوص ادمین
"""

from telegram import Update
from telegram.ext import ContextTypes

from app.config import settings
from app.utils.logger import log


async def admin_test_publish_job_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    اجرای دستی Job انتشار خودکار
    """
    user = update.effective_user

    if user.id != settings.ADMIN_CHAT_ID:
        return

    msg = await update.message.reply_text("🔄 در حال اجرای Job انتشار خودکار...")

    try:
        from app.tasks.jobs.publish_job import run_auto_publish_job
        stats = await run_auto_publish_job(context.bot)

        # ساخت گزارش
        report = "📊 گزارش اجرای Job انتشار\n"
        report += "━━━━━━━━━━━━━━━\n"

        if "message" in stats:
            report += f"ℹ️ {stats['message']}\n"
        elif "error" in stats:
            report += f"❌ خطا: {stats['error']}\n"
        else:
            report += f"👥 کل مشتریان بررسی شده: {stats['total_customers']}\n"
            report += f"✅ پست موفق: {stats['published_count']}\n"

            if stats['skipped_no_hours'] > 0:
                report += f"⏰ خارج از ساعت مجاز: {stats['skipped_no_hours']}\n"
            if stats['skipped_no_interval'] > 0:
                report += f"⏳ منتظر interval: {stats['skipped_no_interval']}\n"
            if stats['skipped_no_products'] > 0:
                report += f"📭 بدون محصول pending: {stats['skipped_no_products']}\n"
            if stats['skipped_no_channels'] > 0:
                report += f"🚫 بدون کانال: {stats['skipped_no_channels']}\n"
            if stats['skipped_no_subscription'] > 0:
                report += f"💳 بدون اشتراک: {stats['skipped_no_subscription']}\n"
            if stats['skipped_inactive'] > 0:
                report += f"😴 حساب غیرفعال: {stats['skipped_inactive']}\n"
            if stats['failed'] > 0:
                report += f"❌ ارسال ناموفق: {stats['failed']}\n"

            if stats.get('details'):
                report += "\n📝 جزئیات:\n"
                for detail in stats['details'][:10]:  # حداکثر ۱۰
                    report += f"• {detail}\n"

        await msg.edit_text(report)

    except Exception as e:
        log.error(f"خطا در تست Job: {e}", exc_info=True)
        await msg.edit_text(f"❌ خطا: {e}")


async def admin_test_reminder_job_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    اجرای دستی Job یادآوری اشتراک
    """
    user = update.effective_user

    if user.id != settings.ADMIN_CHAT_ID:
        return

    await update.message.reply_text("🔄 در حال اجرای Job یادآوری اشتراک...")

    try:
        from app.tasks.jobs.subscription_job import run_subscription_reminder_job
        await run_subscription_reminder_job(context.bot)
        await update.message.reply_text("✅ Job اجرا شد. لاگ‌ها رو چک کنید.")
    except Exception as e:
        log.error(f"خطا در تست Job: {e}", exc_info=True)
        await update.message.reply_text(f"❌ خطا: {e}")