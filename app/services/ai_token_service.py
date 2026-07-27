"""
سرویس مدیریت توکن AI
- تخصیص توکن ماهانه (پلن پرو)
- ثبت خرید توکن اضافی
- مصرف توکن
- شمارش موجودی
"""

from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AIToken, TokenSource
from app.utils.logger import log
from app.utils.time import utc_now_naive


# ═══════════════════════════════════════════════
# محاسبه موجودی
# ═══════════════════════════════════════════════

async def get_total_available_tokens(
    session: AsyncSession,
    customer_id: int,
) -> int:
    """
    مجموع توکن‌های در دسترس مشتری
    (ماهانه غیرمنقضی + خریداری شده)
    """
    now = utc_now_naive()

    # توکن‌های ماهانه معتبر
    monthly_result = await session.execute(
        select(AIToken).where(
            and_(
                AIToken.customer_id == customer_id,
                AIToken.source == TokenSource.MONTHLY,
                AIToken.expires_at > now,
            )
        )
    )
    monthly_tokens = list(monthly_result.scalars().all())
    monthly_remaining = sum(t.remaining_amount for t in monthly_tokens)

    # توکن‌های خریداری شده (بدون انقضا)
    purchased_result = await session.execute(
        select(AIToken).where(
            and_(
                AIToken.customer_id == customer_id,
                AIToken.source == TokenSource.PURCHASED,
            )
        )
    )
    purchased_tokens = list(purchased_result.scalars().all())
    purchased_remaining = sum(t.remaining_amount for t in purchased_tokens)

    return monthly_remaining + purchased_remaining


async def get_tokens_breakdown(
    session: AsyncSession,
    customer_id: int,
) -> dict:
    """جزئیات توکن‌ها (ماهانه/خریداری/کل)"""
    now = utc_now_naive()

    monthly_result = await session.execute(
        select(AIToken).where(
            and_(
                AIToken.customer_id == customer_id,
                AIToken.source == TokenSource.MONTHLY,
                AIToken.expires_at > now,
            )
        )
    )
    monthly_tokens = list(monthly_result.scalars().all())
    monthly_total = sum(t.total_amount for t in monthly_tokens)
    monthly_remaining = sum(t.remaining_amount for t in monthly_tokens)

    purchased_result = await session.execute(
        select(AIToken).where(
            and_(
                AIToken.customer_id == customer_id,
                AIToken.source == TokenSource.PURCHASED,
            )
        )
    )
    purchased_tokens = list(purchased_result.scalars().all())
    purchased_total = sum(t.total_amount for t in purchased_tokens)
    purchased_remaining = sum(t.remaining_amount for t in purchased_tokens)

    # تاریخ انقضای اولین توکن ماهانه
    next_reset = None
    if monthly_tokens:
        next_reset = min(t.expires_at for t in monthly_tokens if t.expires_at)

    return {
        "monthly_total": monthly_total,
        "monthly_remaining": monthly_remaining,
        "monthly_used": monthly_total - monthly_remaining,
        "purchased_total": purchased_total,
        "purchased_remaining": purchased_remaining,
        "purchased_used": purchased_total - purchased_remaining,
        "total_remaining": monthly_remaining + purchased_remaining,
        "next_monthly_reset": next_reset,
    }


# ═══════════════════════════════════════════════
# تخصیص توکن
# ═══════════════════════════════════════════════

async def allocate_monthly_tokens(
    session: AsyncSession,
    customer_id: int,
    amount: int,
    duration_days: int = 30,
) -> AIToken:
    """
    تخصیص توکن ماهانه (برای اشتراک پرو)
    توکن ماهانه بعد از duration_days منقضی می‌شود
    """
    now = utc_now_naive()
    expires_at = now + timedelta(days=duration_days)

    token = AIToken(
        customer_id=customer_id,
        source=TokenSource.MONTHLY,
        total_amount=amount,
        used_amount=0,
        remaining_amount=amount,
        expires_at=expires_at,
        created_at=now,
    )
    session.add(token)
    await session.commit()
    await session.refresh(token)

    log.info(
        f"💳 توکن ماهانه تخصیص یافت: مشتری={customer_id}, "
        f"مقدار={amount}, انقضا={expires_at.strftime('%Y/%m/%d')}"
    )
    return token


async def add_purchased_tokens(
    session: AsyncSession,
    customer_id: int,
    amount: int,
) -> AIToken:
    """
    افزودن توکن خریداری شده (بدون انقضا)
    """
    now = utc_now_naive()

    token = AIToken(
        customer_id=customer_id,
        source=TokenSource.PURCHASED,
        total_amount=amount,
        used_amount=0,
        remaining_amount=amount,
        expires_at=None,  # بدون انقضا
        created_at=now,
    )
    session.add(token)
    await session.commit()
    await session.refresh(token)

    log.info(
        f"💰 توکن خریداری شد: مشتری={customer_id}, مقدار={amount}"
    )
    return token


# ═══════════════════════════════════════════════
# مصرف توکن
# ═══════════════════════════════════════════════

async def can_use_tokens(
    session: AsyncSession,
    customer_id: int,
    amount: int = 1,
) -> bool:
    """چک کن مشتری به اندازه کافی توکن داره"""
    available = await get_total_available_tokens(session, customer_id)
    return available >= amount


async def consume_tokens(
    session: AsyncSession,
    customer_id: int,
    amount: int = 1,
) -> bool:
    """
    مصرف توکن از مشتری
    اولویت: توکن ماهانه (که ممکنه سوخت بشه) → خریداری شده

    Returns: True اگر موفق، False اگر توکن کافی نیست
    """
    now = utc_now_naive()
    remaining_to_consume = amount

    # اول از توکن‌های ماهانه غیرمنقضی
    monthly_result = await session.execute(
        select(AIToken).where(
            and_(
                AIToken.customer_id == customer_id,
                AIToken.source == TokenSource.MONTHLY,
                AIToken.expires_at > now,
                AIToken.remaining_amount > 0,
            )
        ).order_by(AIToken.expires_at.asc())  # قدیمی‌تر (که زودتر منقضی میشه) اول
    )
    monthly_tokens = list(monthly_result.scalars().all())

    for token in monthly_tokens:
        if remaining_to_consume <= 0:
            break

        if token.remaining_amount >= remaining_to_consume:
            token.remaining_amount -= remaining_to_consume
            token.used_amount += remaining_to_consume
            remaining_to_consume = 0
        else:
            remaining_to_consume -= token.remaining_amount
            token.used_amount += token.remaining_amount
            token.remaining_amount = 0

    # بعد از توکن‌های خریداری شده
    if remaining_to_consume > 0:
        purchased_result = await session.execute(
            select(AIToken).where(
                and_(
                    AIToken.customer_id == customer_id,
                    AIToken.source == TokenSource.PURCHASED,
                    AIToken.remaining_amount > 0,
                )
            ).order_by(AIToken.created_at.asc())
        )
        purchased_tokens = list(purchased_result.scalars().all())

        for token in purchased_tokens:
            if remaining_to_consume <= 0:
                break

            if token.remaining_amount >= remaining_to_consume:
                token.remaining_amount -= remaining_to_consume
                token.used_amount += remaining_to_consume
                remaining_to_consume = 0
            else:
                remaining_to_consume -= token.remaining_amount
                token.used_amount += token.remaining_amount
                token.remaining_amount = 0

    # اگه هنوز چیزی موند، یعنی توکن کافی نبود
    if remaining_to_consume > 0:
        await session.rollback()
        log.warning(
            f"⚠️ توکن کافی نبود: مشتری={customer_id}, "
            f"درخواست={amount}, کمبود={remaining_to_consume}"
        )
        return False

    await session.commit()
    log.info(f"💸 توکن مصرف شد: مشتری={customer_id}, مقدار={amount}")
    return True


async def refund_tokens(
    session: AsyncSession,
    customer_id: int,
    amount: int = 1,
) -> None:
    """
    برگرداندن توکن (اگر AI خطا داد یا کاربر انصراف داد در حین پردازش)
    توکن رو به آخرین AIToken که مصرف داشته برمی‌گردونه
    """
    now = utc_now_naive()

    # پیدا کردن اولین توکن با used_amount > 0 (اولویت خریداری شده که آخر مصرف شده)
    purchased_result = await session.execute(
        select(AIToken).where(
            and_(
                AIToken.customer_id == customer_id,
                AIToken.source == TokenSource.PURCHASED,
                AIToken.used_amount > 0,
            )
        ).order_by(AIToken.created_at.desc())
    )
    purchased_tokens = list(purchased_result.scalars().all())

    remaining_to_refund = amount
    for token in purchased_tokens:
        if remaining_to_refund <= 0:
            break
        refund_amount = min(token.used_amount, remaining_to_refund)
        token.used_amount -= refund_amount
        token.remaining_amount += refund_amount
        remaining_to_refund -= refund_amount

    if remaining_to_refund > 0:
        # از توکن‌های ماهانه
        monthly_result = await session.execute(
            select(AIToken).where(
                and_(
                    AIToken.customer_id == customer_id,
                    AIToken.source == TokenSource.MONTHLY,
                    AIToken.expires_at > now,
                    AIToken.used_amount > 0,
                )
            ).order_by(AIToken.expires_at.desc())
        )
        monthly_tokens = list(monthly_result.scalars().all())

        for token in monthly_tokens:
            if remaining_to_refund <= 0:
                break
            refund_amount = min(token.used_amount, remaining_to_refund)
            token.used_amount -= refund_amount
            token.remaining_amount += refund_amount
            remaining_to_refund -= refund_amount

    await session.commit()
    actually_refunded = amount - remaining_to_refund
    log.info(f"↩️ توکن برگردانده شد: مشتری={customer_id}, مقدار={actually_refunded}")


# ═══════════════════════════════════════════════
# پاکسازی توکن‌های منقضی
# ═══════════════════════════════════════════════

async def cleanup_expired_monthly_tokens(session: AsyncSession) -> int:
    """
    پاکسازی توکن‌های ماهانه منقضی
    (این تابع می‌تونه توسط یه Job روزانه صدا زده بشه)
    """
    now = utc_now_naive()

    result = await session.execute(
        select(AIToken).where(
            and_(
                AIToken.source == TokenSource.MONTHLY,
                AIToken.expires_at <= now,
            )
        )
    )
    expired = list(result.scalars().all())

    count = len(expired)
    for token in expired:
        await session.delete(token)

    if count > 0:
        await session.commit()
        log.info(f"🧹 {count} توکن ماهانه منقضی پاک شد")

    return count