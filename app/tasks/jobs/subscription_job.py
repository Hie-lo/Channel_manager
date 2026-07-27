"""
Job یادآوری انقضای اشتراک
هر روز ساعت ۱۰ صبح چک می‌کنه کدوم اشتراک‌ها نزدیک انقضا هستن
"""

from datetime import timedelta
from telegram import Bot
from sqlalchemy import select

from app.database.connection import AsyncSessionLocal
from app.database.models import Subscription, SubscriptionStatus, Customer
from app.services.subscription.plans import get_plan
from app.utils.logger import log
from app.utils.time import utc_now_naive


async def run_subscription_reminder_job(bot: Bot) -> None:
    """
    Job یادآوری انقضای اشتراک
    """
    log.info("🔄 [Subscription Reminder Job] شروع...")

    reminders_5days = 0
    reminders_1day = 0
    expired_count = 0

    try:
        async with AsyncSessionLocal() as session:
            # همه اشتراک‌های فعال
            result = await session.execute(
                select(Subscription).where(
                    Subscription.status.in_([
                        SubscriptionStatus.ACTIVE,
                        SubscriptionStatus.GRACE,
                    ])
                )
            )
            subscriptions = list(result.scalars().all())

            now = utc_now_naive()

            for sub in subscriptions:
                # محاسبه روزهای مانده
                days_remaining = (sub.end_at - now).days

                # هشدار ۵ روز مانده
                if days_remaining == 5:
                    await _send_reminder(bot, session, sub, days=5)
                    reminders_5days += 1

                # هشدار ۱ روز مانده
                elif days_remaining == 1:
                    await _send_reminder(bot, session, sub, days=1)
                    reminders_1day += 1

                # اشتراک منقضی شده
                elif days_remaining <= 0:
                    # چک کن هنوز در grace period هست
                    if now < sub.grace_end_at:
                        # هنوز مهلت داره، هشدار مهلت تمدید
                        if sub.status != SubscriptionStatus.GRACE:
                            sub.status = SubscriptionStatus.GRACE
                            await session.commit()
                            await _send_grace_period_notice(bot, sub)
                    else:
                        # مهلت هم تموم شده
                        sub.status = SubscriptionStatus.EXPIRED
                        await session.commit()
                        await _send_expired_notice(bot, sub)
                        expired_count += 1

        log.info(
            f"✅ [Subscription Reminder Job] پایان - "
            f"۵ روزه: {reminders_5days}, ۱ روزه: {reminders_1day}, "
            f"منقضی: {expired_count}"
        )

    except Exception as e:
        log.error(f"❌ [Subscription Reminder Job] خطا: {e}", exc_info=True)


async def _send_reminder(bot: Bot, session, subscription, days: int) -> None:
    """ارسال یادآوری به مشتری"""
    try:
        # گرفتن مشتری
        result = await session.execute(
            select(Customer).where(Customer.id == subscription.customer_id)
        )
        customer = result.scalar_one_or_none()

        if not customer:
            return

        plan = get_plan(subscription.plan_key)

        if days == 5:
            emoji = "⚠️"
            urgency = "یادآوری"
        else:
            emoji = "🔴"
            urgency = "هشدار فوری"

        text = (
            f"{emoji} {urgency} انقضای اشتراک\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📦 پلن: {plan.emoji} {plan.name_fa}\n"
            f"📅 تاریخ انقضا: {subscription.end_at.strftime('%Y/%m/%d')}\n"
            f"⏳ روزهای باقیمانده: {days} روز\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"برای جلوگیری از توقف سرویس،\n"
            f"اشتراک خود را تمدید کنید.\n\n"
            f"از منوی '💳 اشتراک من' تمدید کنید."
        )

        await bot.send_message(chat_id=customer.telegram_user_id, text=text)
        log.info(f"یادآوری {days} روزه به مشتری {customer.telegram_user_id} ارسال شد")

    except Exception as e:
        log.error(f"خطا در ارسال یادآوری: {e}")


async def _send_grace_period_notice(bot: Bot, subscription) -> None:
    """اطلاع رسیدن به دوره مهلت"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Customer).where(Customer.id == subscription.customer_id)
            )
            customer = result.scalar_one_or_none()

            if not customer:
                return

        text = (
            f"⛔ اشتراک شما منقضی شد!\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📅 تاریخ انقضا: {subscription.end_at.strftime('%Y/%m/%d')}\n"
            f"⏰ مهلت تمدید: تا {subscription.grace_end_at.strftime('%Y/%m/%d')}\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"⚠️ سرویس شما موقتاً متوقف شده.\n"
            f"در صورت تمدید در ۲ روز آینده، همه چیز از همان جا ادامه پیدا می‌کند.\n\n"
            f"از منوی '💳 اشتراک من' تمدید کنید."
        )

        await bot.send_message(chat_id=customer.telegram_user_id, text=text)
        log.info(f"اطلاعیه grace period به مشتری {customer.telegram_user_id} ارسال شد")

    except Exception as e:
        log.error(f"خطا در ارسال grace notice: {e}")


async def _send_expired_notice(bot: Bot, subscription) -> None:
    """اطلاع پایان مهلت"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Customer).where(Customer.id == subscription.customer_id)
            )
            customer = result.scalar_one_or_none()

            if not customer:
                return

        text = (
            f"❌ مهلت تمدید تمام شد!\n"
            f"━━━━━━━━━━━━━━━\n"
            f"وضعیت حساب: معلق\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"❗ برای فعال‌سازی مجدد،\n"
            f"لطفاً با پشتیبانی تماس بگیرید یا\n"
            f"اشتراک جدید خریداری کنید.\n\n"
            f"📌 پست‌های قبلی شما در کانال دست‌نخورده باقی می‌مانند.\n"
            f"📌 محصولات و تنظیمات شما در دیتابیس حفظ می‌شوند."
        )

        await bot.send_message(chat_id=customer.telegram_user_id, text=text)
        log.info(f"اطلاعیه انقضا به مشتری {customer.telegram_user_id} ارسال شد")

    except Exception as e:
        log.error(f"خطا در ارسال expired notice: {e}")