"""
سرویس مدیریت مشتریان (چند پلتفرمی)
"""

import platform

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Customer, CustomerStatus
from app.utils.logger import log
from app.utils.time import utc_now_naive


# ═══════════════════════════════════════════════════════════
# جستجوی مشتری
# ═══════════════════════════════════════════════════════════

async def get_customer_by_platform_id(
    session: AsyncSession,
    user_id: int,
    platform: str = "TELEGRAM",
) -> Customer | None:
    """
    پیدا کردن مشتری با آیدی پلتفرم مشخص
    """
    if platform.upper() == "TELEGRAM":
        result = await session.execute(
            select(Customer).where(Customer.telegram_user_id == user_id)
        )
    elif platform.upper() == "BALE":
        result = await session.execute(
            select(Customer).where(Customer.bale_user_id == user_id)
        )
    else:
        return None

    return result.scalar_one_or_none()


async def get_customer_by_telegram_id(
    session: AsyncSession,
    telegram_user_id: int,
) -> Customer | None:
    """پیدا کردن مشتری با آیدی تلگرام (سازگاری با کد قدیمی)"""
    return await get_customer_by_platform_id(session, telegram_user_id, "TELEGRAM")


async def get_customer_by_bale_id(
    session: AsyncSession,
    bale_user_id: int,
) -> Customer | None:
    """پیدا کردن مشتری با آیدی بله"""
    return await get_customer_by_platform_id(session, bale_user_id, "BALE")


# ═══════════════════════════════════════════════════════════
# ساخت مشتری
# ═══════════════════════════════════════════════════════════

async def create_customer(
    session: AsyncSession,
    user_id: int,
    first_name: str | None,
    last_name: str | None,
    username: str | None,
    platform: str = "TELEGRAM",
) -> Customer:
    """
    ساخت مشتری جدید (چند پلتفرمی)

    Args:
        user_id: آیدی کاربر در پلتفرم مبدا
        platform: TELEGRAM یا BALE
    """
    now = utc_now_naive()
    platform_upper = platform.upper()
    customer_data = {
        "customer_status": CustomerStatus.PENDING,
        "source_platform": platform_upper,
        "first_name": first_name,     # برای سازگاری
        "last_name": last_name,
        "username": username,
        "created_at": now,
        "updated_at": now,
    }

    # پلتفرم اصلی رو تنظیم کن
    if platform_upper == "TELEGRAM":
        customer_data.update({
            "telegram_user_id": user_id,
            "telegram_first_name": first_name,
            "telegram_last_name": last_name,
            "telegram_username": username,
        })
    elif platform_upper == "BALE":
        customer_data.update({
            "bale_user_id": user_id,
            "bale_first_name": first_name,
            "bale_last_name": last_name,
            "bale_username": username,
        })

    customer = Customer(**customer_data)
    session.add(customer)
    await session.commit()
    await session.refresh(customer)

    log.info(
        f"مشتری جدید ساخته شد: user_id={user_id}, "
        f"name={first_name}, platform={platform_upper}"
    )
    return customer


# ═══════════════════════════════════════════════════════════
# اتصال حساب (لینک کردن پلتفرم دوم)
# آماده برای پیاده‌سازی آینده
# ═══════════════════════════════════════════════════════════

async def link_platform_to_customer(
    session: AsyncSession,
    customer_id: int,
    platform: str,
    user_id: int,
    first_name: str | None = None,
    last_name: str | None = None,
    username: str | None = None,
) -> Customer | None:
    """
    اتصال یک پلتفرم دیگه به مشتری موجود

    مثال: مشتری در تلگرام هست، الان می‌خواد بله رو هم متصل کنه
    """
    result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        return None

    if platform.upper() == "TELEGRAM":
        # چک تکراری نبودن
        existing = await get_customer_by_telegram_id(session, user_id)
        if existing and existing.id != customer_id:
            log.warning(
                f"آیدی تلگرام {user_id} قبلاً به مشتری {existing.id} متصله"
            )
            return None

        customer.telegram_user_id = user_id
        if first_name:
            customer.telegram_first_name = first_name
        if last_name:
            customer.telegram_last_name = last_name
        if username:
            customer.telegram_username = username

    elif platform.upper() == "BALE":
        existing = await get_customer_by_bale_id(session, user_id)
        if existing and existing.id != customer_id:
            log.warning(
                f"آیدی بله {user_id} قبلاً به مشتری {existing.id} متصله"
            )
            return None

        customer.bale_user_id = user_id
        if first_name:
            customer.bale_first_name = first_name
        if last_name:
            customer.bale_last_name = last_name
        if username:
            customer.bale_username = username

    customer.updated_at = utc_now_naive()
    await session.commit()
    await session.refresh(customer)

    log.info(f"پلتفرم {platform} به مشتری {customer_id} متصل شد")
    return customer


# ═══════════════════════════════════════════════════════════
# سایر توابع (بدون تغییر ساختار، فقط بازنویسی مختصر)
# ═══════════════════════════════════════════════════════════

async def set_customer_business_type(
    session: AsyncSession,
    telegram_user_id: int,
    business_type_key: str,
    platform: str = "TELEGRAM",
) -> Customer | None:
    """تنظیم نوع کسب‌وکار مشتری"""
    customer = await get_customer_by_platform_id(session, telegram_user_id, platform)
    if not customer:
        return None

    customer.business_type_key = business_type_key
    customer.updated_at = utc_now_naive()
    await session.commit()
    await session.refresh(customer)
    return customer


async def approve_customer(
    session: AsyncSession,
    user_id: int,
    platform: str = "TELEGRAM",
) -> Customer | None:
    """تایید مشتری"""
    customer = await get_customer_by_platform_id(session, user_id, platform)
    if not customer:
        return None

    customer.customer_status = CustomerStatus.ACTIVE
    customer.updated_at = utc_now_naive()
    await session.commit()
    await session.refresh(customer)
    log.info(f"مشتری تایید شد: {user_id} ({platform})")
    return customer


async def reject_customer(
    session: AsyncSession,
    user_id: int,
    platform: str = "TELEGRAM",
) -> Customer | None:
    """رد مشتری"""
    customer = await get_customer_by_platform_id(session, user_id, platform)
    if not customer:
        return None

    customer.customer_status = CustomerStatus.REJECTED
    customer.updated_at = utc_now_naive()
    await session.commit()
    await session.refresh(customer)
    log.info(f"مشتری رد شد: {user_id} ({platform})")
    return customer


async def get_all_pending_customers(session: AsyncSession) -> list[Customer]:
    """لیست مشتریان در انتظار تایید"""
    result = await session.execute(
        select(Customer).where(Customer.customer_status == CustomerStatus.PENDING)
    )
    return list(result.scalars().all())


# ═══════════════════════════════════════════════════════════
# توکن ایتا (بدون تغییر)
# ═══════════════════════════════════════════════════════════

async def set_customer_eitaa_token(
    session: AsyncSession,
    customer_id: int,
    eitaa_token: str,
) -> Customer | None:
    """ذخیره توکن ایتای مشتری (با رمزنگاری)"""
    from app.utils.encryption import encrypt_text, mask_token

    result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        return None

    encrypted_token = encrypt_text(eitaa_token)
    customer.eitaa_bot_token = encrypted_token
    customer.updated_at = utc_now_naive()

    await session.commit()
    await session.refresh(customer)

    log.info(
        f"توکن ایتا برای مشتری {customer_id} ذخیره شد "
        f"({mask_token(eitaa_token)})"
    )
    return customer


async def get_customer_eitaa_token(
    session: AsyncSession,
    customer_id: int,
) -> str | None:
    """گرفتن توکن ایتای مشتری (رمزگشایی شده)"""
    from app.utils.encryption import decrypt_text

    result = await session.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = result.scalar_one_or_none()

    if not customer or not customer.eitaa_bot_token:
        return None

    decrypted = decrypt_text(customer.eitaa_bot_token)
    return decrypted if decrypted else None


# ═══════════════════════════════════════════════════════════
# تابع کمکی برای نمایش
# ═══════════════════════════════════════════════════════════

def get_customer_display_name(customer: Customer) -> str:
    """نام نمایشی مشتری (اولویت: تلگرام)"""
    if customer.telegram_first_name:
        name = customer.telegram_first_name
        if customer.telegram_last_name:
            name += f" {customer.telegram_last_name}"
        return name

    if customer.bale_first_name:
        name = customer.bale_first_name
        if customer.bale_last_name:
            name += f" {customer.bale_last_name}"
        return name

    return customer.first_name or "بدون نام"


def get_customer_all_platforms(customer: Customer) -> list[dict]:
    """لیست همه پلتفرم‌های متصل به مشتری"""
    platforms = []

    if customer.telegram_user_id:
        platforms.append({
            "platform": "TELEGRAM",
            "icon": "📱",
            "name": "تلگرام",
            "user_id": customer.telegram_user_id,
            "username": customer.telegram_username or customer.username,
            "first_name": customer.telegram_first_name,
        })

    if customer.bale_user_id:
        platforms.append({
            "platform": "BALE",
            "icon": "💬",
            "name": "بله",
            "user_id": customer.bale_user_id,
            "username": customer.bale_username,
            "first_name": customer.bale_first_name,
        })

    return platforms