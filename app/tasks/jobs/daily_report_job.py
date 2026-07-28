"""
Job گزارش روزانه به مشتریان
"""

from telegram import Bot
from sqlalchemy import select

from app.database.connection import AsyncSessionLocal
from app.database.models import Customer, CustomerStatus
from app.services.subscription.service import get_active_subscription
from app.services.daily_report_service import (
    build_daily_report,
    format_daily_report,
)
from app.utils.logger import log


async def run_daily_report_job(bot: Bot) -> dict:
    """
    Job گزارش روزانه
    برای همه مشتریان فعال گزارش می‌فرسته
    """
    log.info("🔄 [Daily Report Job] شروع...")

    stats = {
        "total_customers": 0,
        "sent_count": 0,
        "failed_count": 0,
    }

    try:
        async with AsyncSessionLocal() as session:
            # همه مشتری‌های فعال با اشتراک
            result = await session.execute(
                select(Customer).where(
                    Customer.customer_status == CustomerStatus.ACTIVE
                )
            )
            customers = list(result.scalars().all())

            stats["total_customers"] = len(customers)

            for customer in customers:
                try:
                    # چک اشتراک فعال
                    subscription = await get_active_subscription(session, customer.id)
                    if not subscription:
                        continue  # مشتری بدون اشتراک گزارش نگیره

                    # ساخت گزارش
                    report = await build_daily_report(session, customer.id)

                    # اگه هیچ فعالیتی نبود، گزارش نفرست (اختیاری)
                    has_activity = (
                        report["posts_today"] > 0
                        or report["edits_today"] > 0
                        or report["ai_used_today"] > 0
                    )

                    # فقط اگه فعالیت داشت یا محصولات pending داره
                    if not has_activity and report["pending_products"] == 0:
                        continue

                    # ارسال گزارش
                    text = format_daily_report(report, customer.first_name or "")

                    await bot.send_message(
                        chat_id=customer.telegram_user_id,
                        text=text,
                        parse_mode="HTML",
                    )
                    stats["sent_count"] += 1
                    log.info(f"✅ گزارش روزانه ارسال شد به {customer.telegram_user_id}")

                except Exception as e:
                    stats["failed_count"] += 1
                    log.warning(
                        f"خطا در ارسال گزارش به {customer.telegram_user_id}: {e}"
                    )

        log.info(
            f"✅ [Daily Report Job] پایان - "
            f"ارسال: {stats['sent_count']}/{stats['total_customers']}"
        )
        return stats

    except Exception as e:
        log.error(f"❌ [Daily Report Job] خطا: {e}", exc_info=True)
        stats["error"] = str(e)
        return stats