"""
سرویس اتصال حساب‌ها (Account Linking) با رعایت استانداردهای امنیتی
"""
import random
import string
from datetime import timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AccountLinkCode, Customer, CustomerStatus
from app.utils.time import utc_now_naive
from app.utils.logger import log

# تنظیمات امنیتی
CODE_EXPIRY_MINUTES = 5
MAX_FAILED_ATTEMPTS = 3


def _generate_secure_code() -> str:
    """تولید کد 6 رقمی امن (فقط اعداد برای راحتی کاربر)"""
    import secrets
    return "".join(secrets.choice(string.digits) for _ in range(6))


async def generate_link_code(session: AsyncSession, customer_id: int) -> str | None:
    """
    تولید و ذخیره کد اتصال جدید برای مشتری
    کدهای قبلی را غیرفعال می‌کند.
    """
    # 1. باطل کردن کدهای استفاده نشده قبلی این مشتری (امنیت)
    result = await session.execute(
        select(AccountLinkCode).where(
            and_(
                AccountLinkCode.customer_id == customer_id,
                AccountLinkCode.is_used == False
            )
        )
    )
    old_codes = list(result.scalars().all())
    for code in old_codes:
        code.is_used = True
    
    # 2. تولید کد یکتا
    # در محیط Production احتمال برخورد (Collision) هست، پس چک می‌کنیم
    max_retries = 5
    for _ in range(max_retries):
        new_code_str = _generate_secure_code()
        
        # آیا این کد الان در دیتابیس (و استفاده نشده/منقضی نشده) وجود داره؟
        exist_check = await session.execute(
            select(AccountLinkCode).where(
                and_(
                    AccountLinkCode.link_code == new_code_str,
                    AccountLinkCode.is_used == False,
                    AccountLinkCode.expires_at > utc_now_naive()
                )
            )
        )
        if not exist_check.scalar_one_or_none():
            break
    else:
        log.error("Failed to generate a unique link code after max retries")
        return None

    # 3. ذخیره در دیتابیس
    expires = utc_now_naive() + timedelta(minutes=CODE_EXPIRY_MINUTES)
    new_code = AccountLinkCode(
        customer_id=customer_id,
        link_code=new_code_str,
        expires_at=expires,
        is_used=False
    )
    
    session.add(new_code)
    await session.commit()
    
    log.info(f"🔒 کد اتصال جدید برای مشتری {customer_id} تولید شد. انقضا: {CODE_EXPIRY_MINUTES} دقیقه")
    return new_code_str


async def verify_and_link_account(
    session: AsyncSession, 
    code_str: str, 
    new_user_id: int, 
    new_platform: str,
    new_first_name: str | None = None,
    new_username: str | None = None
) -> tuple[bool, str, Customer | None]:
    """
    اعتبارسنجی کد و اتصال پلتفرم جدید به مشتری قدیمی.
    Returns: (Success, Message, OriginalCustomer)
    """
    now = utc_now_naive()
    
    # 1. جستجوی کد
    result = await session.execute(
        select(AccountLinkCode).where(AccountLinkCode.link_code == code_str)
    )
    link_record = result.scalar_one_or_none()
    
    # 2. بررسی‌های امنیتی
    if not link_record:
        return False, "❌ کد نامعتبر است.", None
        
    if link_record.is_used:
        return False, "❌ این کد قبلاً استفاده شده است.", None
        
    if link_record.failed_attempts >= MAX_FAILED_ATTEMPTS:
        link_record.is_used = True
        await session.commit()
        return False, "❌ به دلیل تلاش‌های ناموفق متعدد، این کد باطل شده است.", None
        
    if link_record.expires_at < now:
        link_record.is_used = True
        await session.commit()
        return False, "❌ زمان استفاده از این کد (۵ دقیقه) به پایان رسیده است.", None

    # 3. یافتن مشتری اصلی
    customer_result = await session.execute(
        select(Customer).where(Customer.id == link_record.customer_id)
    )
    customer = customer_result.scalar_one_or_none()
    
    if not customer or customer.customer_status != CustomerStatus.ACTIVE:
        return False, "❌ حساب اصلی یافت نشد یا غیرفعال است.", None

    # 4. بررسی اینکه آیا این آیدی (در این پلتفرم) قبلاً به جای دیگری وصل است؟
    # (جلوگیری از تصاحب حساب)
    from app.services.customer_service import get_customer_by_platform_id
    existing_user_check = await get_customer_by_platform_id(session, new_user_id, new_platform)
    
    if existing_user_check:
        # اگر کاربر جدید الان به عنوان یه PENDING ثبت شده، باید اون رکورد PENDING رو پاک کنیم (یا نادیده بگیریم)
        if existing_user_check.id != customer.id:
            if existing_user_check.customer_status == CustomerStatus.PENDING:
                # پاک کردن مشتری موقت
                await session.delete(existing_user_check)
            else:
                link_record.failed_attempts += 1
                await session.commit()
                return False, "❌ این حساب قبلاً به یک کسب‌وکار دیگر متصل شده است!", None

    # 5. اتصال امن حساب
    if new_platform.upper() == "BALE":
        customer.bale_user_id = new_user_id
        customer.bale_first_name = new_first_name
        customer.bale_username = new_username
    elif new_platform.upper() == "TELEGRAM":
        customer.telegram_user_id = new_user_id
        customer.telegram_first_name = new_first_name
        customer.telegram_username = new_username
        
    customer.updated_at = now
    
    # 6. ابطال کد
    link_record.is_used = True
    
    await session.commit()
    await session.refresh(customer)
    
    log.info(f"🔗 حساب {new_platform} ({new_user_id}) به مشتری {customer.id} متصل شد.")
    
    return True, "✅ حساب‌ها با موفقیت متصل شدند.", customer