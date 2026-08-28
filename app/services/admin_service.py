"""
سرویس‌های مورد نیاز پنل ادمین
"""

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    Customer,
    CustomerStatus,
    Subscription,
    SubscriptionStatus,
    Product,
    Channel,
    AIToken,
    AIUsageLog,
    TokenSource,
)
from app.utils.time import utc_now_naive
from app.utils.logger import log     # ⬅️ این خط اضافه بشه

# ═══════════════════════════════════════════════
# لیست مشتریان
# ═══════════════════════════════════════════════

async def get_customers_by_status(
    session: AsyncSession,
    status: str,  # "all" | "active" | "pending" | "suspended"
    page: int = 0,
    per_page: int = 10,
) -> tuple[list[Customer], int]:
    """
    گرفتن لیست مشتریان با صفحه‌بندی
    Returns: (customers, total_count)
    """
    query = select(Customer)

    if status == "active":
        query = query.where(Customer.customer_status == CustomerStatus.ACTIVE)
    elif status == "pending":
        query = query.where(Customer.customer_status == CustomerStatus.PENDING)
    elif status == "suspended":
        query = query.where(Customer.customer_status == CustomerStatus.SUSPENDED)
    # "all" هیچ فیلتری نداره

    # شمارش
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total_count = total_result.scalar() or 0

    # گرفتن صفحه
    query = query.order_by(Customer.created_at.desc()).offset(page * per_page).limit(per_page)
    result = await session.execute(query)
    customers = list(result.scalars().all())

    return customers, total_count


async def get_customer_by_id(
    session: AsyncSession,
    customer_id: int,
) -> Customer | None:
    """گرفتن مشتری با ID داخلی"""
    result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    return result.scalar_one_or_none()


# ═══════════════════════════════════════════════
# جزئیات مشتری
# ═══════════════════════════════════════════════

async def get_customer_full_info(
    session: AsyncSession,
    customer_id: int,
) -> dict:
    """
    گرفتن اطلاعات کامل یک مشتری برای نمایش به ادمین
    """
    customer = await get_customer_by_id(session, customer_id)
    if not customer:
        return {}

    # اشتراک فعال
    sub_result = await session.execute(
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
    subscription = sub_result.scalar_one_or_none()

    # تعداد کانال
    channels_result = await session.execute(
        select(func.count()).select_from(Channel).where(
            Channel.customer_id == customer_id
        )
    )
    channels_count = channels_result.scalar() or 0

    # تعداد محصولات
    products_result = await session.execute(
        select(func.count()).select_from(Product).where(
            Product.customer_id == customer_id
        )
    )
    products_count = products_result.scalar() or 0

    # موجودی توکن AI
    now = utc_now_naive()
    ai_tokens_result = await session.execute(
        select(func.sum(AIToken.remaining_amount)).where(
            and_(
                AIToken.customer_id == customer_id,
                # منقضی نشده یا خرید (بدون انقضا)
                (AIToken.expires_at > now) | (AIToken.expires_at.is_(None)),
            )
        )
    )
    ai_tokens = ai_tokens_result.scalar() or 0

    # تعداد استفاده از AI
    ai_usage_result = await session.execute(
        select(func.count()).select_from(AIUsageLog).where(
            AIUsageLog.customer_id == customer_id
        )
    )
    ai_usage_count = ai_usage_result.scalar() or 0

    return {
        "customer": customer,
        "subscription": subscription,
        "channels_count": channels_count,
        "products_count": products_count,
        "ai_tokens_remaining": ai_tokens,
        "ai_usage_count": ai_usage_count,
    }


# ═══════════════════════════════════════════════
# تغییر وضعیت مشتری
# ═══════════════════════════════════════════════

async def suspend_customer(
    session: AsyncSession,
    customer_id: int,
) -> Customer | None:
    """مسدود کردن مشتری"""
    customer = await get_customer_by_id(session, customer_id)
    if not customer:
        return None

    customer.customer_status = CustomerStatus.SUSPENDED
    customer.updated_at = utc_now_naive()
    await session.commit()
    await session.refresh(customer)
    return customer


async def activate_customer(
    session: AsyncSession,
    customer_id: int,
) -> Customer | None:
    """فعال کردن مجدد مشتری"""
    customer = await get_customer_by_id(session, customer_id)
    if not customer:
        return None

    customer.customer_status = CustomerStatus.ACTIVE
    customer.updated_at = utc_now_naive()
    await session.commit()
    await session.refresh(customer)
    return customer


# ═══════════════════════════════════════════════
# آمار کلی سیستم
# ═══════════════════════════════════════════════

async def get_system_stats(session: AsyncSession) -> dict:
    """آمار کلی سیستم"""

    # تعداد مشتریان به تفکیک وضعیت
    active_count_result = await session.execute(
        select(func.count()).select_from(Customer).where(
            Customer.customer_status == CustomerStatus.ACTIVE
        )
    )
    active_count = active_count_result.scalar() or 0

    pending_count_result = await session.execute(
        select(func.count()).select_from(Customer).where(
            Customer.customer_status == CustomerStatus.PENDING
        )
    )
    pending_count = pending_count_result.scalar() or 0

    suspended_count_result = await session.execute(
        select(func.count()).select_from(Customer).where(
            Customer.customer_status == CustomerStatus.SUSPENDED
        )
    )
    suspended_count = suspended_count_result.scalar() or 0

    total_customers = active_count + pending_count + suspended_count

    # تعداد اشتراک‌های فعال
    active_subs_result = await session.execute(
        select(func.count()).select_from(Subscription).where(
            Subscription.status == SubscriptionStatus.ACTIVE
        )
    )
    active_subs = active_subs_result.scalar() or 0

    # اشتراک‌های بر اساس پلن
    subs_by_plan_result = await session.execute(
        select(Subscription.plan_key, func.count()).where(
            Subscription.status == SubscriptionStatus.ACTIVE
        ).group_by(Subscription.plan_key)
    )
    subs_by_plan = dict(subs_by_plan_result.all())

    # تعداد کانال‌های متصل
    channels_result = await session.execute(
        select(func.count()).select_from(Channel)
    )
    channels_count = channels_result.scalar() or 0

    # تعداد کل محصولات
    products_result = await session.execute(
        select(func.count()).select_from(Product)
    )
    products_count = products_result.scalar() or 0

    # مصرف توکن AI کل
    ai_usage_result = await session.execute(
        select(func.count()).select_from(AIUsageLog)
    )
    ai_usage_total = ai_usage_result.scalar() or 0

    return {
        "total_customers": total_customers,
        "active_customers": active_count,
        "pending_customers": pending_count,
        "suspended_customers": suspended_count,
        "active_subscriptions": active_subs,
        "subs_by_plan": subs_by_plan,
        "channels_count": channels_count,
        "products_count": products_count,
        "ai_usage_total": ai_usage_total,
    }


# ═══════════════════════════════════════════════
# آمار AI
# ═══════════════════════════════════════════════

async def get_ai_stats(session: AsyncSession) -> dict:
    """آمار استفاده از AI"""

    # کل استفاده‌ها
    total_result = await session.execute(
        select(func.count()).select_from(AIUsageLog)
    )
    total_usage = total_result.scalar() or 0

    # قبول شده
    accepted_result = await session.execute(
        select(func.count()).select_from(AIUsageLog).where(
            AIUsageLog.accepted == True
        )
    )
    accepted_count = accepted_result.scalar() or 0

    # بر اساس نوع
    by_type_result = await session.execute(
        select(AIUsageLog.usage_type, func.count()).group_by(
            AIUsageLog.usage_type
        )
    )
    by_type = dict(by_type_result.all())

    # کل توکن‌های تخصیص یافته
    monthly_tokens_result = await session.execute(
        select(func.sum(AIToken.total_amount)).where(
            AIToken.source == TokenSource.MONTHLY
        )
    )
    monthly_total = monthly_tokens_result.scalar() or 0

    purchased_tokens_result = await session.execute(
        select(func.sum(AIToken.total_amount)).where(
            AIToken.source == TokenSource.PURCHASED
        )
    )
    purchased_total = purchased_tokens_result.scalar() or 0

    return {
        "total_usage": total_usage,
        "accepted_count": accepted_count,
        "accepted_rate": (accepted_count / total_usage * 100) if total_usage > 0 else 0,
        "by_type": by_type,
        "monthly_tokens_allocated": monthly_total,
        "purchased_tokens_allocated": purchased_total,
    }


# ═══════════════════════════════════════════════
# مشتریان فعال (برای ارسال همگانی)
# ═══════════════════════════════════════════════

async def get_all_active_customers(session: AsyncSession) -> list[Customer]:
    """گرفتن همه مشتریان فعال (برای broadcast)"""
    from app.utils.logger import log

    result = await session.execute(
        select(Customer).where(
            Customer.customer_status == CustomerStatus.ACTIVE
        )
    )
    customers = list(result.scalars().all())

    log.info(f"📊 تعداد مشتریان فعال: {len(customers)}")
    for c in customers:
        log.info(f"   - {c.telegram_user_id} | {c.first_name} | {c.customer_status}")

    return customers

# ═══════════════════════════════════════════════
# مدیریت اشتراک‌ها
# ═══════════════════════════════════════════════

async def get_subscriptions_by_status(
    session: AsyncSession,
    status: str,  # "active" | "pending" | "expired" | "all"
    page: int = 0,
    per_page: int = 10,
) -> tuple[list, int]:
    """
    گرفتن لیست اشتراک‌ها با فیلتر و صفحه‌بندی
    Returns: (subscriptions, total_count)
    """
    query = select(Subscription)

    if status == "active":
        query = query.where(Subscription.status == SubscriptionStatus.ACTIVE)
    elif status == "pending":
        query = query.where(Subscription.status == SubscriptionStatus.PENDING)
    elif status == "expired":
        query = query.where(Subscription.status.in_([
            SubscriptionStatus.EXPIRED,
            SubscriptionStatus.SUSPENDED,
        ]))
    elif status == "grace":
        query = query.where(Subscription.status == SubscriptionStatus.GRACE)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total_count = total_result.scalar() or 0

    query = query.order_by(Subscription.created_at.desc()).offset(page * per_page).limit(per_page)
    result = await session.execute(query)
    subscriptions = list(result.scalars().all())

    return subscriptions, total_count


async def get_subscription_by_id(
    session: AsyncSession,
    subscription_id: int,
) -> Subscription | None:
    """گرفتن اشتراک با آیدی"""
    result = await session.execute(
        select(Subscription).where(Subscription.id == subscription_id)
    )
    return result.scalar_one_or_none()


async def extend_subscription_manual(
    session: AsyncSession,
    subscription_id: int,
    extra_days: int,
) -> Subscription | None:
    """تمدید دستی اشتراک توسط ادمین"""
    from datetime import timedelta
    from app.services.subscription.service import GRACE_PERIOD_DAYS

    subscription = await get_subscription_by_id(session, subscription_id)
    if not subscription:
        return None

    now = utc_now_naive()

    # اگه هنوز فعاله، از تاریخ پایان قبلی اضافه کن
    # اگه منقضی شده، از الان اضافه کن
    if subscription.end_at > now:
        subscription.end_at = subscription.end_at + timedelta(days=extra_days)
    else:
        subscription.end_at = now + timedelta(days=extra_days)

    subscription.grace_end_at = subscription.end_at + timedelta(days=GRACE_PERIOD_DAYS)
    subscription.status = SubscriptionStatus.ACTIVE

    await session.commit()
    await session.refresh(subscription)
    return subscription


async def cancel_subscription(
    session: AsyncSession,
    subscription_id: int,
) -> Subscription | None:
    """لغو دستی اشتراک"""
    subscription = await get_subscription_by_id(session, subscription_id)
    if not subscription:
        return None

    subscription.status = SubscriptionStatus.EXPIRED
    subscription.end_at = utc_now_naive()
    subscription.grace_end_at = utc_now_naive()

    await session.commit()
    await session.refresh(subscription)
    return subscription


async def delete_subscription(
    session: AsyncSession,
    subscription_id: int,
) -> bool:
    """حذف کامل اشتراک (فقط برای PENDING های اشتباه)"""
    subscription = await get_subscription_by_id(session, subscription_id)
    if not subscription:
        return False

    await session.delete(subscription)
    await session.commit()
    return True


async def get_revenue_stats(session: AsyncSession) -> dict:
    """آمار درآمد"""
    from app.services.subscription.plans import get_plan

    # همه اشتراک‌های فعال شده (نه PENDING)
    result = await session.execute(
        select(Subscription).where(
            Subscription.status != SubscriptionStatus.PENDING
        )
    )
    all_subs = list(result.scalars().all())

    total_revenue = 0
    revenue_by_plan = {}

    for sub in all_subs:
        plan = get_plan(sub.plan_key)
        if not plan:
            continue

        # تخمین قیمت بر اساس مدت
        days = (sub.end_at - sub.start_at).days

        if days <= 35:
            price = plan.price_monthly
        elif days <= 100:
            price = plan.price_quarterly
        else:
            price = plan.price_half_yearly

        total_revenue += price

        if sub.plan_key not in revenue_by_plan:
            revenue_by_plan[sub.plan_key] = {"count": 0, "revenue": 0}
        revenue_by_plan[sub.plan_key]["count"] += 1
        revenue_by_plan[sub.plan_key]["revenue"] += price

    return {
        "total_revenue": total_revenue,
        "revenue_by_plan": revenue_by_plan,
        "total_subscriptions": len(all_subs),
    }


async def get_customer_of_subscription(
    session: AsyncSession,
    subscription: Subscription,
) -> Customer | None:
    """گرفتن مشتری صاحب اشتراک"""
    result = await session.execute(
        select(Customer).where(Customer.id == subscription.customer_id)
    )
    return result.scalar_one_or_none()


# ═══════════════════════════════════════════════════════════════
# مدیریت اشتراک توسط ادمین
# ═══════════════════════════════════════════════════════════════

async def grant_subscription_to_customer(
    session,
    customer_id: int,
    plan_key: str,
    days: int,
) -> Subscription | None:
    """
    اعطای اشتراک جدید به مشتری توسط ادمین.
    اگر اشتراک قبلی وجود داشت، لغو و جایگزین می‌شود.
    """
    from datetime import timedelta
    from app.utils.time import utc_now_naive
    from app.database.models import Subscription, SubscriptionStatus, Customer
    from app.services.subscription.service import activate_subscription_features
    from sqlalchemy import select

    # بررسی وجود مشتری
    customer_result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    if not customer:
        log.error(f"[AdminService] مشتری {customer_id} پیدا نشد")
        return None

    # لغو اشتراک‌های قبلی فعال
    existing_result = await session.execute(
        select(Subscription).where(
            Subscription.customer_id == customer_id,
            Subscription.status.in_([
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.GRACE,
            ])
        )
    )
    existing = existing_result.scalars().all()
    for sub in existing:
        sub.status = SubscriptionStatus.EXPIRED
        sub.end_at = utc_now_naive()
        log.info(f"[AdminService] اشتراک قبلی #{sub.id} لغو شد")

    # ساخت اشتراک جدید
    now = utc_now_naive()
    end_at = now + timedelta(days=days)
    grace_end_at = end_at + timedelta(days=7)

    new_sub = Subscription(
        customer_id=customer_id,
        plan_key=plan_key,
        status=SubscriptionStatus.ACTIVE,
        start_at=now,
        end_at=end_at,
        grace_end_at=grace_end_at,
    )
    session.add(new_sub)
    await session.commit()
    await session.refresh(new_sub)

    # فعال‌سازی ویژگی‌ها (توکن AI، فعال کردن مشتری)
    await activate_subscription_features(session, new_sub)

    log.info(
        f"[AdminService] اشتراک جدید #{new_sub.id} به مشتری {customer_id} "
        f"اعطا شد: {plan_key} برای {days} روز"
    )

    return new_sub


async def revoke_customer_subscription(session, customer_id: int) -> bool:
    """
    لغو و حذف همه اشتراک‌های فعال مشتری.
    اشتراک‌ها به Expired تغییر وضعیت می‌دهند.
    """
    from app.utils.time import utc_now_naive
    from app.database.models import Subscription, SubscriptionStatus
    from sqlalchemy import select

    result = await session.execute(
        select(Subscription).where(
            Subscription.customer_id == customer_id,
            Subscription.status.in_([
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.GRACE,
            ])
        )
    )
    subscriptions = result.scalars().all()

    if not subscriptions:
        log.warning(f"[AdminService] مشتری {customer_id} اشتراک فعالی ندارد")
        return False

    for sub in subscriptions:
        sub.status = SubscriptionStatus.EXPIRED
        sub.end_at = utc_now_naive()
        log.info(f"[AdminService] اشتراک #{sub.id} توسط ادمین لغو شد")

    await session.commit()
    return True
