"""
سرویس مدیریت اشتراک
عملیات دیتابیس مربوط به اشتراک
"""

from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Subscription, SubscriptionStatus
from app.utils.logger import log
from app.utils.time import utc_now_naive


# مدت مهلت تمدید (روز)
GRACE_PERIOD_DAYS = 2


async def get_active_subscription(
    session: AsyncSession,
    customer_id: int,
) -> Subscription | None:
    """گرفتن اشتراک فعال مشتری"""
    result = await session.execute(
        select(Subscription).where(
            and_(
                Subscription.customer_id == customer_id,
                Subscription.status.in_([
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.GRACE,
                ]),
            )
        )
    )
    return result.scalar_one_or_none()


async def get_pending_subscription(
    session: AsyncSession,
    customer_id: int,
) -> Subscription | None:
    """گرفتن اشتراک در انتظار پرداخت"""
    result = await session.execute(
        select(Subscription).where(
            and_(
                Subscription.customer_id == customer_id,
                Subscription.status == SubscriptionStatus.PENDING,
            )
        )
    )
    return result.scalar_one_or_none()


async def create_pending_subscription(
    session: AsyncSession,
    customer_id: int,
    plan_key: str,
    duration_days: int,
) -> Subscription:
    """
    ایجاد یک اشتراک در انتظار پرداخت
    تاریخ‌ها موقتی هستن و بعد از تایید ادمین تنظیم میشن
    """
    now = utc_now_naive()
    subscription = Subscription(
        customer_id=customer_id,
        plan_key=plan_key,
        status=SubscriptionStatus.PENDING,
        start_at=now,  # موقت
        end_at=now + timedelta(days=duration_days),  # موقت
        grace_end_at=now + timedelta(days=duration_days + GRACE_PERIOD_DAYS),  # موقت
        created_at=now,
    )
    session.add(subscription)
    await session.commit()
    await session.refresh(subscription)
    log.info(f"اشتراک PENDING ساخته شد برای مشتری {customer_id}, پلن {plan_key}")
    return subscription


async def activate_subscription(
    session: AsyncSession,
    subscription_id: int,
    duration_days: int,
) -> Subscription | None:
    """
    فعال کردن اشتراک بعد از تایید پرداخت توسط ادمین
    تاریخ‌های شروع و پایان از الان محاسبه میشن
    """
    result = await session.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        return None

    now = utc_now_naive()
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.start_at = now
    subscription.end_at = now + timedelta(days=duration_days)
    subscription.grace_end_at = subscription.end_at + timedelta(days=GRACE_PERIOD_DAYS)

    await session.commit()
    await session.refresh(subscription)
    log.info(f"اشتراک {subscription_id} فعال شد")
    return subscription


async def reject_subscription(
    session: AsyncSession,
    subscription_id: int,
) -> bool:
    """رد کردن اشتراک (وقتی رسید اشتباه بود)"""
    result = await session.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        return False

    await session.delete(subscription)
    await session.commit()
    log.info(f"اشتراک {subscription_id} رد شد")
    return True


async def cancel_pending_subscription(
    session: AsyncSession,
    customer_id: int,
) -> bool:
    """لغو اشتراک در انتظار (توسط خود مشتری)"""
    pending = await get_pending_subscription(session, customer_id)
    if not pending:
        return False

    await session.delete(pending)
    await session.commit()
    log.info(f"اشتراک PENDING مشتری {customer_id} لغو شد")
    return True


def calculate_days_remaining(subscription: Subscription) -> int:
    """محاسبه روزهای باقیمانده اشتراک"""
    if not subscription:
        return 0

    now = utc_now_naive()
    if subscription.end_at <= now:
        return 0

    delta = subscription.end_at - now
    return delta.days


def is_in_grace_period(subscription: Subscription) -> bool:
    """چک می‌کنه اشتراک در مهلت تمدید هست"""
    if not subscription:
        return False

    now = utc_now_naive()
    return subscription.end_at <= now < subscription.grace_end_at


def is_subscription_active(subscription: Subscription | None) -> bool:
    """چک می‌کنه اشتراک فعاله (ACTIVE یا GRACE)"""
    if not subscription:
        return False

    if subscription.status not in [
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.GRACE,
    ]:
        return False

    now = utc_now_naive()
    return now < subscription.grace_end_at