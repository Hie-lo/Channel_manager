"""
هندلرهای مخصوص ادمین
"""

from telegram import Update
from telegram.ext import ContextTypes

from app.config import settings
from app.utils.logger import log


async def admin_test_publish_job_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """اجرای دستی Job انتشار خودکار"""
    user = update.effective_user

    if user.id != settings.ADMIN_CHAT_ID:
        return

    msg = await update.message.reply_text("🔄 در حال اجرای Job انتشار خودکار...")

    try:
        from app.tasks.jobs.publish_job import run_auto_publish_job
        stats = await run_auto_publish_job(context.bot)

        report = "📊 گزارش اجرای Job انتشار\n"
        report += "━━━━━━━━━━━━━━━\n"

        if "message" in stats:
            report += f"ℹ️ {stats['message']}\n"
        elif "error" in stats:
            report += f"❌ خطا: {stats['error']}\n"
        else:
            report += f"👥 کل مشتریان بررسی شده: {stats['total_customers']}\n"
            report += f"✅ پست موفق: {stats['published_count']}\n"

            if stats.get('skipped_no_hours', 0) > 0:
                report += f"⏰ خارج از ساعت مجاز: {stats['skipped_no_hours']}\n"
            if stats.get('skipped_no_interval', 0) > 0:
                report += f"⏳ منتظر interval: {stats['skipped_no_interval']}\n"
            if stats.get('skipped_no_products', 0) > 0:
                report += f"📭 بدون محصول pending: {stats['skipped_no_products']}\n"
            if stats.get('skipped_no_channels', 0) > 0:
                report += f"🚫 بدون کانال: {stats['skipped_no_channels']}\n"
            if stats.get('skipped_no_subscription', 0) > 0:
                report += f"💳 بدون اشتراک: {stats['skipped_no_subscription']}\n"
            if stats.get('skipped_inactive', 0) > 0:
                report += f"😴 حساب غیرفعال: {stats['skipped_inactive']}\n"
            if stats.get('failed', 0) > 0:
                report += f"❌ ارسال ناموفق: {stats['failed']}\n"

            if stats.get('details'):
                report += "\n📝 جزئیات:\n"
                for detail in stats['details'][:10]:
                    report += f"• {detail}\n"

        await msg.edit_text(report)

    except Exception as e:
        log.error(f"خطا در تست Job: {e}", exc_info=True)
        await msg.edit_text(f"❌ خطا: {e}")


async def admin_test_reminder_job_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """اجرای دستی Job یادآوری اشتراک"""
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


async def admin_test_sheet_sync_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """اجرای دستی Job همگام‌سازی شیت"""
    user = update.effective_user

    if user.id != settings.ADMIN_CHAT_ID:
        return

    msg = await update.message.reply_text("🔄 در حال اجرای Job همگام‌سازی...")

    try:
        from app.tasks.jobs.sheet_sync_job import run_sheet_sync_job
        stats = await run_sheet_sync_job(context.bot)

        report = "📊 گزارش همگام‌سازی\n━━━━━━━━━━━━━━━\n"

        if "message" in stats:
            report += f"ℹ️ {stats['message']}\n"
        elif "error" in stats:
            report += f"❌ خطا: {stats['error']}\n"
        else:
            report += f"👥 کل مشتریان: {stats['total_customers']}\n"
            report += f"✅ موفق: {stats['success_count']}\n"
            report += f"❌ ناموفق: {stats['failed_count']}\n"

            if stats.get('details'):
                report += "\n📝 جزئیات:\n"
                for detail in stats['details'][:10]:
                    report += f"• {detail}\n"

        await msg.edit_text(report)

    except Exception as e:
        log.error(f"خطا در تست sync: {e}", exc_info=True)
        await msg.edit_text(f"❌ خطا: {e}")


async def admin_test_daily_report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """اجرای دستی گزارش روزانه"""
    user = update.effective_user
    if user.id != settings.ADMIN_CHAT_ID:
        return

    msg = await update.message.reply_text("🔄 در حال اجرای Job گزارش روزانه...")

    try:
        from app.tasks.jobs.daily_report_job import run_daily_report_job
        stats = await run_daily_report_job(context.bot)

        report = "📊 گزارش اجرای Job روزانه\n━━━━━━━━━━━━━━━\n"

        if "error" in stats:
            report += f"❌ خطا: {stats['error']}\n"
        else:
            report += f"👥 کل مشتریان بررسی شده: {stats['total_customers']}\n"
            report += f"✅ گزارش ارسال شد: {stats['sent_count']}\n"
            report += f"❌ ناموفق: {stats['failed_count']}\n"

        await msg.edit_text(report)

    except Exception as e:
        log.error(f"خطا در تست Job: {e}", exc_info=True)
        await msg.edit_text(f"❌ خطا: {e}")

async def admin_force_ai_test_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    تست AI برای اولین محصول PENDING بدون توضیحات
    استفاده: /force_ai_test
    """
    user = update.effective_user
    if user.id != settings.ADMIN_CHAT_ID:
        return

    msg = await update.message.reply_text("🔄 در حال جستجوی محصول تست...")

    from app.database.connection import AsyncSessionLocal
    from app.database.models import Product, ProductPublishStatus
    from app.services.ai.service import generate_product_description
    from app.services.business_service import get_business_config_for_customer
    from app.services.customer_service import get_customer_by_telegram_id
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        # پیدا کن یه محصول PENDING بدون توضیحات
        result = await session.execute(
            select(Product).where(
                Product.publish_status == ProductPublishStatus.PENDING,
                Product.description_manual.is_(None),
                Product.is_available == True,
            ).limit(1)
        )
        product = result.scalar_one_or_none()

        if not product:
            await msg.edit_text(
                "❌ محصول PENDING بدون توضیحات پیدا نشد!\n\n"
                "💡 یه محصول جدید بدون description آپلود کن یا "
                "توضیحات یه محصول موجود رو پاک کن."
            )
            return

        # گرفتن customer برای business_config
        customer_result = await session.execute(
            select(Customer := __import__(
                'app.database.models', fromlist=['Customer']
            ).Customer).where(
                __import__('app.database.models', fromlist=['Customer']).Customer.id == product.customer_id
            )
        )
        customer = customer_result.scalar_one_or_none()

        if not customer:
            await msg.edit_text("❌ مشتری محصول پیدا نشد!")
            return

        business_config = get_business_config_for_customer(customer)

    if not business_config:
        await msg.edit_text("❌ business_config پیدا نشد!")
        return

    await msg.edit_text(
        f"🤖 در حال تست AI برای:\n"
        f"محصول: {product.product_name}\n"
        f"SKU: {product.sku}\n"
        f"مشتری: {customer.first_name}"
    )

    try:
        ai_result = await generate_product_description(
            product=product,
            business_config=business_config,
            mode="new",
        )

        if ai_result.success:
            await msg.edit_text(
                f"✅ AI موفق!\n"
                f"━━━━━━━━━━━━━━━\n"
                f"محصول: {product.product_name}\n"
                f"مشتری: {customer.first_name}\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"نتیجه:\n\n{ai_result.formatted_text[:1500]}"
            )
        else:
            await msg.edit_text(
                f"❌ AI ناموفق!\n"
                f"دلیل: {ai_result.error_message}"
            )

    except Exception as e:
        log.error(f"خطا در force AI test: {e}", exc_info=True)
        await msg.edit_text(f"❌ خطا: {str(e)[:300]}")