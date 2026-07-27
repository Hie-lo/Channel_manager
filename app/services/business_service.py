"""
سرویس مدیریت کسب‌وکار
"""

from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Business, Customer
from app.business.config import (
    get_business,
    get_business_excel_path,
    BusinessConfig,
)
from app.utils.logger import log
from app.utils.time import utc_now_naive


async def get_business_for_customer(
    session: AsyncSession,
    customer_id: int,
) -> Business | None:
    """گرفتن کسب‌وکار مشتری"""
    result = await session.execute(
        select(Business).where(Business.customer_id == customer_id)
    )
    return result.scalar_one_or_none()


async def create_business_for_customer(
    session: AsyncSession,
    customer_id: int,
    business_type_key: str,
    business_name: str,
    contact_text: str | None = None,
) -> Business:
    """ایجاد کسب‌وکار جدید برای مشتری"""
    business = Business(
        customer_id=customer_id,
        business_type_key=business_type_key,
        business_name=business_name,
        contact_text=contact_text,
        created_at=utc_now_naive(),
    )
    session.add(business)
    await session.commit()
    await session.refresh(business)
    log.info(f"کسب‌وکار جدید: {business_type_key} برای مشتری {customer_id}")
    return business


async def update_business_contact(
    session: AsyncSession,
    customer_id: int,
    contact_text: str,
) -> Business | None:
    """آپدیت اطلاعات تماس"""
    business = await get_business_for_customer(session, customer_id)
    if not business:
        return None

    business.contact_text = contact_text
    await session.commit()
    await session.refresh(business)
    return business


def get_business_config_for_customer(customer: Customer) -> BusinessConfig | None:
    """گرفتن تنظیمات کسب‌وکار از روی مشتری"""
    if not customer.business_type_key:
        return None
    return get_business(customer.business_type_key)


def get_excel_template_path(business_type_key: str) -> Path | None:
    """مسیر فایل نمونه اکسل"""
    path = get_business_excel_path(business_type_key)
    if path and path.exists():
        return path
    return None