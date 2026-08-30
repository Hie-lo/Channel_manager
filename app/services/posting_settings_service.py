"""
سرویس مدیریت تنظیمات ارسال پست
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import PostingSettings
from app.utils.logger import log
from app.utils.time import utc_now_naive


async def get_posting_settings(
    session: AsyncSession,
    customer_id: int,
) -> PostingSettings | None:
    """گرفتن تنظیمات ارسال مشتری"""
    result = await session.execute(
        select(PostingSettings).where(PostingSettings.customer_id == customer_id)
    )
    return result.scalar_one_or_none()


async def get_or_create_posting_settings(
    session: AsyncSession,
    customer_id: int,
) -> PostingSettings:
    """گرفتن یا ایجاد تنظیمات پیش‌فرض"""
    settings_obj = await get_posting_settings(session, customer_id)

    if settings_obj:
        return settings_obj

    # ایجاد تنظیمات پیش‌فرض
    settings_obj = PostingSettings(
        customer_id=customer_id,
        auto_publish_enabled=False,  # پیش‌فرض: دستی
        interval_hours=3,
        interval_minutes=180,  # 💡 معادل دقیقه‌ای همون ۳ ساعت — واحد اصلی از این به بعد
        posting_start_hour=9,
        posting_end_hour=22,
        created_at=utc_now_naive(),
    )
    session.add(settings_obj)
    await session.commit()
    await session.refresh(settings_obj)
    log.info(f"تنظیمات ارسال پیش‌فرض ساخته شد برای مشتری {customer_id}")
    return settings_obj


async def set_auto_publish(
    session: AsyncSession,
    customer_id: int,
    enabled: bool,
) -> PostingSettings:
    """فعال/غیرفعال کردن ارسال خودکار"""
    settings_obj = await get_or_create_posting_settings(session, customer_id)
    settings_obj.auto_publish_enabled = enabled
    settings_obj.updated_at = utc_now_naive()
    await session.commit()
    await session.refresh(settings_obj)
    return settings_obj


async def update_interval(
    session: AsyncSession,
    customer_id: int,
    interval_hours: int,
) -> PostingSettings:
    """آپدیت فاصله بین پست‌ها (نسخه‌ی ساعتی - نگه‌داشته‌شده برای backward-compat)"""
    return await update_interval_minutes(session, customer_id, interval_hours * 60)


async def update_interval_minutes(
    session: AsyncSession,
    customer_id: int,
    minutes: int,
) -> PostingSettings:
    """آپدیت فاصله بین پست‌ها به دقیقه (واحد اصلی و دقیق‌تر)"""
    settings_obj = await get_or_create_posting_settings(session, customer_id)
    settings_obj.interval_minutes = minutes
    settings_obj.interval_hours = max(1, minutes // 60)  # فقط برای سازگاری با کدهای قدیمی
    settings_obj.updated_at = utc_now_naive()
    await session.commit()
    await session.refresh(settings_obj)
    return settings_obj


def get_interval_minutes(settings_obj) -> int:
    """
    گرفتن فاصله به دقیقه، صرف‌نظر از اینکه ستون interval_minutes
    قبلاً برای این رکورد ست شده یا نه (سازگاری با رکوردهای قدیمی).
    """
    minutes = getattr(settings_obj, "interval_minutes", None)
    if minutes:
        return minutes
    return (settings_obj.interval_hours or 1) * 60


async def update_posting_hours(
    session: AsyncSession,
    customer_id: int,
    start_hour: int,
    end_hour: int,
) -> PostingSettings:
    """آپدیت ساعت‌های مجاز ارسال"""
    settings_obj = await get_or_create_posting_settings(session, customer_id)
    settings_obj.posting_start_hour = start_hour
    settings_obj.posting_end_hour = end_hour
    settings_obj.updated_at = utc_now_naive()
    await session.commit()
    await session.refresh(settings_obj)
    return settings_obj


def calculate_posts_per_day(settings_obj: PostingSettings) -> int:
    """محاسبه تعداد پست در روز بر اساس تنظیمات"""
    active_minutes = (settings_obj.posting_end_hour - settings_obj.posting_start_hour) * 60
    if active_minutes <= 0:
        return 0
    interval_minutes = get_interval_minutes(settings_obj)
    if interval_minutes <= 0:
        return 0
    return active_minutes // interval_minutes

from datetime import timedelta


async def get_all_customers_with_auto_publish(
    session: AsyncSession,
) -> list:
    """گرفتن همه مشتریانی که auto_publish روشن دارن"""
    result = await session.execute(
        select(PostingSettings).where(PostingSettings.auto_publish_enabled == True)
    )
    return list(result.scalars().all())


async def update_last_post_time(
    session: AsyncSession,
    customer_id: int,
) -> None:
    """آپدیت زمان آخرین پست"""
    settings_obj = await get_posting_settings(session, customer_id)
    if settings_obj:
        settings_obj.last_post_at = utc_now_naive()
        await session.commit()


def is_in_posting_hours(settings_obj) -> bool:
    """چک کن الان در ساعت مجاز ارسال هست"""
    from datetime import datetime
    import pytz

    tehran_tz = pytz.timezone("Asia/Tehran")
    now = datetime.now(tehran_tz)
    current_hour = now.hour

    return settings_obj.posting_start_hour <= current_hour < settings_obj.posting_end_hour


def is_time_for_next_post(settings_obj) -> bool:
    """چک کن الان زمان پست بعدی رسیده"""
    if not settings_obj.last_post_at:
        return True  # اولین پست

    now = utc_now_naive()
    time_since_last = now - settings_obj.last_post_at
    required_interval = timedelta(minutes=get_interval_minutes(settings_obj))

    return time_since_last >= required_interval

async def set_auto_ai_description(
    session: AsyncSession,
    customer_id: int,
    enabled: bool,
) -> PostingSettings:
    """فعال/غیرفعال کردن AI خودکار برای توضیحات"""
    settings_obj = await get_or_create_posting_settings(session, customer_id)
    settings_obj.auto_ai_description = enabled
    settings_obj.updated_at = utc_now_naive()
    await session.commit()
    await session.refresh(settings_obj)
    return settings_obj