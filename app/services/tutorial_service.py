"""
سرویس مدیریت آموزش‌ها
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Tutorial
from app.utils.logger import log
from app.utils.time import utc_now_naive


async def get_tutorial_by_key(
    session: AsyncSession,
    key: str,
) -> Tutorial | None:
    """گرفتن یک آموزش با کلیدش"""
    result = await session.execute(
        select(Tutorial).where(
            Tutorial.key == key,
            Tutorial.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def get_tutorials_by_category(
    session: AsyncSession,
    category: str,
) -> list[Tutorial]:
    """گرفتن آموزش‌های یک دسته"""
    result = await session.execute(
        select(Tutorial)
        .where(
            Tutorial.category == category,
            Tutorial.is_active == True,
        )
        .order_by(Tutorial.display_order.asc(), Tutorial.id.asc())
    )
    return list(result.scalars().all())


async def get_all_categories(session: AsyncSession) -> list[str]:
    """گرفتن لیست همه دسته‌های موجود"""
    result = await session.execute(
        select(Tutorial.category)
        .where(Tutorial.is_active == True)
        .distinct()
    )
    return [row[0] for row in result.all()]


async def get_all_faqs(session: AsyncSession) -> list[Tutorial]:
    """گرفتن همه سوالات متداول"""
    result = await session.execute(
        select(Tutorial)
        .where(
            Tutorial.content_type == "faq",
            Tutorial.is_active == True,
        )
        .order_by(Tutorial.display_order.asc())
    )
    return list(result.scalars().all())


async def create_tutorial(
    session: AsyncSession,
    key: str,
    title: str,
    category: str,
    content_type: str,
    text_content: str | None = None,
    video_file_id: str | None = None,
    video_caption: str | None = None,
    faq_question: str | None = None,
    display_order: int = 0,
) -> Tutorial:
    """ساخت آموزش جدید"""
    tutorial = Tutorial(
        key=key,
        title=title,
        category=category,
        content_type=content_type,
        text_content=text_content,
        video_file_id=video_file_id,
        video_caption=video_caption,
        faq_question=faq_question,
        display_order=display_order,
        is_active=True,
        created_at=utc_now_naive(),
    )
    session.add(tutorial)
    await session.commit()
    await session.refresh(tutorial)
    log.info(f"📚 آموزش جدید: {key}")
    return tutorial


async def update_tutorial(
    session: AsyncSession,
    key: str,
    **kwargs,
) -> Tutorial | None:
    """آپدیت آموزش"""
    tutorial = await get_tutorial_by_key(session, key)
    if not tutorial:
        return None

    for field, value in kwargs.items():
        if hasattr(tutorial, field):
            setattr(tutorial, field, value)

    tutorial.updated_at = utc_now_naive()
    await session.commit()
    await session.refresh(tutorial)
    return tutorial


async def delete_tutorial(
    session: AsyncSession,
    key: str,
) -> bool:
    """حذف آموزش"""
    tutorial = await get_tutorial_by_key(session, key)
    if not tutorial:
        return False

    await session.delete(tutorial)
    await session.commit()
    return True