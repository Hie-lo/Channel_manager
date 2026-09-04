"""
سرویس مدیریت رکوردهای پست‌های ارسال شده
"""

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import PostedMessage, Platform
from app.utils.logger import log
from app.utils.time import utc_now_naive


async def get_posted_message(
    session: AsyncSession,
    product_id: int,
    channel_id: int,
) -> PostedMessage | None:
    """پیدا کردن رکورد پست"""
    result = await session.execute(
        select(PostedMessage).where(
            and_(
                PostedMessage.product_id == product_id,
                PostedMessage.channel_id == channel_id,
            )
        )
    )
    return result.scalar_one_or_none()


async def create_posted_message(
    session: AsyncSession,
    product_id: int,
    channel_id: int,
    telegram_message_id: int,
    caption: str,
    price: int,
    stock_qty: int,
    platform: Platform = Platform.TELEGRAM,
    message_ids: list[int] | None = None,
) -> PostedMessage:
    """ایجاد رکورد پست ارسال شده"""
    now = utc_now_naive()

    posted = PostedMessage(
        product_id=product_id,
        channel_id=channel_id,
        platform=platform,
        telegram_message_id=telegram_message_id,
        telegram_message_ids=message_ids or [telegram_message_id],
        last_caption=caption,
        last_price=price,
        last_stock_qty=stock_qty,
        status="ACTIVE",
        created_at=now,
        updated_at=now,
    )
    session.add(posted)
    await session.commit()
    await session.refresh(posted)

    log.info(
        f"رکورد پست ذخیره شد: product={product_id}, "
        f"channel={channel_id}, msg_id={telegram_message_id}"
    )
    return posted


async def update_posted_message(
    session: AsyncSession,
    posted_message: PostedMessage,
    new_caption: str,
    new_price: int,
    new_stock_qty: int,
) -> PostedMessage:
    """آپدیت رکورد پست بعد از ویرایش"""
    posted_message.last_caption = new_caption
    posted_message.last_price = new_price
    posted_message.last_stock_qty = new_stock_qty
    posted_message.updated_at = utc_now_naive()

    await session.commit()
    await session.refresh(posted_message)
    return posted_message


async def get_posted_messages_by_product(
    session: AsyncSession,
    product_id: int,
) -> list[PostedMessage]:
    """همه پست‌های یک محصول در همه کانال‌ها"""
    result = await session.execute(
        select(PostedMessage).where(PostedMessage.product_id == product_id)
    )
    return list(result.scalars().all())