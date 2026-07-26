"""
سرویس مدیریت مشتریان
تمام عملیات مربوط به مشتری اینجاست
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Customer, CustomerStatus
from app.utils.logger import log
from app.utils.time import utc_now_naive


async def get_customer_by_telegram_id(
    session: AsyncSession,
    telegram_user_id: int
) -> Customer | None:
    """پیدا کردن مشتری با آیدی تلگرام"""
    result = await session.execute(
        select(Customer).where(Customer.telegram_user_id == telegram_user_id)
    )
    return result.scalar_one_or_none()


async def create_customer(
    session: AsyncSession,
    telegram_user_id: int,
    first_name: str | None,
    last_name: str | None,
    username: str | None,
) -> Customer:
    """ساخت مشتری جدید با وضعیت PENDING"""
    customer = Customer(
        telegram_user_id=telegram_user_id,
        first_name=first_name,
        last_name=last_name,
        username=username,
        customer_status=CustomerStatus.PENDING,
        created_at=utc_now_naive(),
        updated_at=utc_now_naive(),
    )
    session.add(customer)
    await session.commit()
    await session.refresh(customer)
    log.info(f"مشتری جدید ساخته شد: {telegram_user_id} - {first_name}")
    return customer


async def set_customer_business_type(
    session: AsyncSession,
    telegram_user_id: int,
    business_type_key: str,
) -> Customer | None:
    """تنظیم نوع کسب‌وکار مشتری"""
    customer = await get_customer_by_telegram_id(session, telegram_user_id)
    if not customer:
        return None

    customer.business_type_key = business_type_key
    customer.updated_at = utc_now_naive()
    await session.commit()
    await session.refresh(customer)
    return customer


async def approve_customer(
    session: AsyncSession,
    telegram_user_id: int,
) -> Customer | None:
    """تایید مشتری توسط ادمین"""
    customer = await get_customer_by_telegram_id(session, telegram_user_id)
    if not customer:
        return None

    customer.customer_status = CustomerStatus.ACTIVE
    customer.updated_at = utc_now_naive()
    await session.commit()
    await session.refresh(customer)
    log.info(f"مشتری تایید شد: {telegram_user_id}")
    return customer


async def reject_customer(
    session: AsyncSession,
    telegram_user_id: int,
) -> Customer | None:
    """رد مشتری توسط ادمین"""
    customer = await get_customer_by_telegram_id(session, telegram_user_id)
    if not customer:
        return None

    customer.customer_status = CustomerStatus.REJECTED
    customer.updated_at = utc_now_naive()
    await session.commit()
    await session.refresh(customer)
    log.info(f"مشتری رد شد: {telegram_user_id}")
    return customer


async def get_all_pending_customers(
    session: AsyncSession,
) -> list[Customer]:
    """لیست مشتریان در انتظار تایید"""
    result = await session.execute(
        select(Customer).where(Customer.customer_status == CustomerStatus.PENDING)
    )
    return list(result.scalars().all())