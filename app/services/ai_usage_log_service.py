"""
سرویس لاگ استفاده از AI
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AIUsageLog
from app.utils.logger import log
from app.utils.time import utc_now_naive


async def log_ai_usage(
    session: AsyncSession,
    customer_id: int,
    product_id: int | None,
    usage_type: str,  # "generate" | "improve"
    tokens_used: int,
    model_used: str,
    accepted: bool = False,
    raw_response: str | None = None,
) -> AIUsageLog:
    """ثبت یک لاگ استفاده از AI"""
    usage_log = AIUsageLog(
        customer_id=customer_id,
        product_id=product_id,
        usage_type=usage_type,
        tokens_used=tokens_used,
        model_used=model_used,
        accepted=accepted,
        raw_response=raw_response,
        created_at=utc_now_naive(),
    )
    session.add(usage_log)
    await session.commit()
    await session.refresh(usage_log)

    log.info(
        f"📝 لاگ AI: مشتری={customer_id}, "
        f"محصول={product_id}, نوع={usage_type}, "
        f"تایید={accepted}"
    )
    return usage_log


async def mark_log_as_accepted(
    session: AsyncSession,
    log_id: int,
) -> None:
    """علامت‌گذاری لاگ به عنوان مورد قبول (وقتی کاربر نتیجه رو تایید کرد)"""
    from sqlalchemy import select
    result = await session.execute(
        select(AIUsageLog).where(AIUsageLog.id == log_id)
    )
    log_entry = result.scalar_one_or_none()

    if log_entry:
        log_entry.accepted = True
        await session.commit()