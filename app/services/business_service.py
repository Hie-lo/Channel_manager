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


async def reset_customer_data(
    session: AsyncSession,
    customer_id: int,
) -> None:
    """
    ریست کامل داده‌های مشتری به‌جز اشتراک‌ها و توکن‌های AI

    جداول پاک‌شونده:
    - PostedMessage (وابسته به Product و Channel)
    - ProductPlatformMedia (وابسته به Product)
    - AIUsageLog (وابسته به Product)
    - Product
    - Channel
    - PostingSettings
    - GoogleSheetConnection
    - AccountLinkCode
    - Business
    - Customer.business_type_key → None
    """
    from sqlalchemy import delete
    from app.database.models import (
        PostedMessage,
        ProductPlatformMedia,
        AIUsageLog,
        Product,
        Channel,
        PostingSettings,
        GoogleSheetConnection,
        AccountLinkCode,
        Business,
        Customer,
    )

    # ۱. جمع‌آوری آیدی محصولات این مشتری
    from sqlalchemy import select
    product_ids_result = await session.execute(
        select(Product.id).where(Product.customer_id == customer_id)
    )
    product_ids = [row[0] for row in product_ids_result.fetchall()]

    # ۲. پاک کردن PostedMessage (وابسته به Product)
    if product_ids:
        await session.execute(
            delete(PostedMessage).where(PostedMessage.product_id.in_(product_ids))
        )

    # ۳. پاک کردن ProductPlatformMedia (وابسته به Product)
    if product_ids:
        await session.execute(
            delete(ProductPlatformMedia).where(ProductPlatformMedia.product_id.in_(product_ids))
        )

    # ۴. پاک کردن AIUsageLog های مرتبط با محصولات (لاگ‌های AI کلی مشتری نگه داشته می‌شه)
    if product_ids:
        await session.execute(
            delete(AIUsageLog).where(AIUsageLog.product_id.in_(product_ids))
        )

    # ۵. پاک کردن محصولات
    await session.execute(
        delete(Product).where(Product.customer_id == customer_id)
    )

    # ۶. پاک کردن کانال‌ها
    await session.execute(
        delete(Channel).where(Channel.customer_id == customer_id)
    )

    # ۷. پاک کردن تنظیمات ارسال
    await session.execute(
        delete(PostingSettings).where(PostingSettings.customer_id == customer_id)
    )

    # ۸. پاک کردن اتصال Google Sheet
    await session.execute(
        delete(GoogleSheetConnection).where(GoogleSheetConnection.customer_id == customer_id)
    )

    # ۹. پاک کردن کدهای اتصال حساب
    await session.execute(
        delete(AccountLinkCode).where(AccountLinkCode.customer_id == customer_id)
    )

    # ۱۰. پاک کردن رکورد Business
    await session.execute(
        delete(Business).where(Business.customer_id == customer_id)
    )

    # ۱۱. ریست کردن business_type_key در جدول مشتری
    from sqlalchemy import update as sa_update
    from app.utils.time import utc_now_naive
    await session.execute(
        sa_update(Customer)
        .where(Customer.id == customer_id)
        .values(business_type_key=None, updated_at=utc_now_naive())
    )

    await session.commit()
    log.info(f"[RESET] داده‌های مشتری {customer_id} پاک شدند (اشتراک‌ها و توکن‌های AI حفظ شدند)")
