"""
سرویس ساخت گزارش روزانه فعالیت مشتری
"""

from datetime import timedelta
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    Customer,
    CustomerStatus,
    Product,
    PostedMessage,
    AIUsageLog,
    ProductPublishStatus,
    Subscription,
    SubscriptionStatus,
)
from app.services.subscription.service import get_active_subscription
from app.utils.time import utc_now_naive


async def build_daily_report(
    session: AsyncSession,
    customer_id: int,
) -> dict:
    """
    ساخت گزارش روزانه یک مشتری
    فعالیت‌های ۲۴ ساعت اخیر رو جمع می‌کنه
    """
    now = utc_now_naive()
    yesterday = now - timedelta(hours=24)

    # اطلاعات کلی محصولات
    total_products_result = await session.execute(
        select(func.count()).select_from(Product).where(
            Product.customer_id == customer_id
        )
    )
    total_products = total_products_result.scalar() or 0

    available_result = await session.execute(
        select(func.count()).select_from(Product).where(
            and_(
                Product.customer_id == customer_id,
                Product.is_available == True,
            )
        )
    )
    available_products = available_result.scalar() or 0

    unavailable_products = total_products - available_products

    # پست‌های ارسال شده امروز
    posts_today_result = await session.execute(
        select(func.count()).select_from(PostedMessage).where(
            and_(
                PostedMessage.created_at >= yesterday,
            )
        ).join(
            Product, Product.id == PostedMessage.product_id
        ).where(
            Product.customer_id == customer_id
        )
    )
    posts_today = posts_today_result.scalar() or 0

    # پست‌های ویرایش شده امروز
    edits_today_result = await session.execute(
        select(func.count()).select_from(PostedMessage).where(
            and_(
                PostedMessage.updated_at >= yesterday,
                PostedMessage.created_at < yesterday,  # ساخت قبلی، ولی آپدیت امروز
            )
        ).join(
            Product, Product.id == PostedMessage.product_id
        ).where(
            Product.customer_id == customer_id
        )
    )
    edits_today = edits_today_result.scalar() or 0

    # محصولات pending
    pending_result = await session.execute(
        select(func.count()).select_from(Product).where(
            and_(
                Product.customer_id == customer_id,
                Product.publish_status == ProductPublishStatus.PENDING,
                Product.is_available == True,
            )
        )
    )
    pending_products = pending_result.scalar() or 0

    # مصرف AI امروز
    ai_today_result = await session.execute(
        select(func.count()).select_from(AIUsageLog).where(
            and_(
                AIUsageLog.customer_id == customer_id,
                AIUsageLog.created_at >= yesterday,
            )
        )
    )
    ai_today = ai_today_result.scalar() or 0

    # اشتراک
    subscription = await get_active_subscription(session, customer_id)
    days_remaining = 0
    if subscription:
        delta = subscription.end_at - now
        days_remaining = max(0, delta.days)

    return {
        "total_products": total_products,
        "available_products": available_products,
        "unavailable_products": unavailable_products,
        "posts_today": posts_today,
        "edits_today": edits_today,
        "pending_products": pending_products,
        "ai_used_today": ai_today,
        "subscription": subscription,
        "days_remaining": days_remaining,
    }


def format_daily_report(report: dict, customer_name: str = "") -> str:
    """فرمت گزارش برای ارسال به مشتری"""

    hello = f"سلام {customer_name} 👋\n" if customer_name else "سلام 👋\n"

    text = (
        f"{hello}"
        f"📊 <b>گزارش فعالیت ۲۴ ساعت اخیر</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"📦 <b>وضعیت محصولات:</b>\n"
        f"├── کل: {report['total_products']}\n"
        f"├── ✅ موجود: {report['available_products']}\n"
        f"├── ❌ ناموجود: {report['unavailable_products']}\n"
        f"└── ⏳ منتظر انتشار: {report['pending_products']}\n\n"
        f"📢 <b>فعالیت امروز:</b>\n"
        f"├── 📤 پست جدید: {report['posts_today']}\n"
        f"├── ✏️ ویرایش پست: {report['edits_today']}\n"
        f"└── 🤖 استفاده از AI: {report['ai_used_today']} بار\n\n"
    )

    # اشتراک
    if report["subscription"]:
        text += (
            f"💳 <b>اشتراک:</b>\n"
            f"└── ⏳ {report['days_remaining']} روز باقیمانده\n\n"
        )
        if report["days_remaining"] <= 3:
            text += f"⚠️ اشتراک شما به زودی تمام میشه!\n\n"

    text += (
        f"━━━━━━━━━━━━━━━\n"
        f"💡 برای جزئیات بیشتر:\n"
        f"از منوی '📦 مدیریت محصولات' استفاده کنید."
    )

    return text