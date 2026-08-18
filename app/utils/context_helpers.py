"""
توابع کمکی برای handler ها
"""

from app.database.connection import AsyncSessionLocal
from app.services.customer_service import get_customer_by_platform_id
from app.utils.admin_check import detect_platform_from_context


async def get_customer_from_update(update, context):
    """
    گرفتن مشتری از update و context
    خودش platform رو تشخیص میده و مشتری رو پیدا می‌کنه

    استفاده:
        async with AsyncSessionLocal() as session:
            customer = await get_customer_from_update(update, context)
            if not customer:
                # کاربر ثبت‌نام نکرده
                return
    """
    user = update.effective_user
    platform = detect_platform_from_context(context)

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_platform_id(session, user.id, platform)
        return customer


def get_user_platform(context) -> str:
    """گرفتن platform از context"""
    return detect_platform_from_context(context)