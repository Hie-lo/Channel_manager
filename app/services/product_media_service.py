"""
سرویس مدیریت عکس‌های محصول برای پلتفرم‌های مختلف
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ProductPlatformMedia, Platform
from app.utils.logger import log
from app.utils.time import utc_now_naive


async def get_product_media(
    session: AsyncSession,
    product_id: int,
    platform: Platform,
) -> ProductPlatformMedia | None:
    """گرفتن عکس محصول برای یک پلتفرم خاص"""
    result = await session.execute(
        select(ProductPlatformMedia).where(
            ProductPlatformMedia.product_id == product_id,
            ProductPlatformMedia.platform == platform,
        )
    )
    return result.scalar_one_or_none()


async def set_product_media(
    session: AsyncSession,
    product_id: int,
    platform: Platform,
    file_id: str,
    uploaded_by_customer: bool = False,
) -> ProductPlatformMedia:
    """
    ذخیره یا آپدیت file_id عکس محصول برای یک پلتفرم
    """
    existing = await get_product_media(session, product_id, platform)

    if existing:
        existing.file_id = file_id
        existing.uploaded_by_customer = uploaded_by_customer
        existing.updated_at = utc_now_naive()
        await session.commit()
        await session.refresh(existing)
        log.info(
            f"📷 عکس محصول {product_id} برای {platform.value} آپدیت شد"
        )
        return existing

    media = ProductPlatformMedia(
        product_id=product_id,
        platform=platform,
        file_id=file_id,
        uploaded_by_customer=uploaded_by_customer,
        created_at=utc_now_naive(),
    )
    session.add(media)
    await session.commit()
    await session.refresh(media)
    log.info(
        f"📷 عکس محصول {product_id} برای {platform.value} ذخیره شد"
    )
    return media


async def remove_product_media(
    session: AsyncSession,
    product_id: int,
    platform: Platform | None = None,
) -> int:
    """
    حذف عکس محصول
    اگه platform مشخص باشه، فقط اون پلتفرم
    اگه None باشه، همه پلتفرم‌ها
    """
    query = select(ProductPlatformMedia).where(
        ProductPlatformMedia.product_id == product_id
    )

    if platform:
        query = query.where(ProductPlatformMedia.platform == platform)

    result = await session.execute(query)
    medias = list(result.scalars().all())

    count = len(medias)
    for media in medias:
        await session.delete(media)

    if count > 0:
        await session.commit()
        log.info(f"🗑 {count} عکس محصول {product_id} حذف شد")

    return count


async def get_customer_uploaded_media(
    session: AsyncSession,
    product_id: int,
) -> ProductPlatformMedia | None:
    """
    گرفتن عکس آپلود شده توسط مشتری (اگه هست)
    """
    result = await session.execute(
        select(ProductPlatformMedia).where(
            ProductPlatformMedia.product_id == product_id,
            ProductPlatformMedia.uploaded_by_customer == True,
        )
    )
    return result.scalar_one_or_none()


def get_photo_source_for_platform(
    product,
    telegram_media: ProductPlatformMedia | None = None,
) -> str | None:
    """
    گرفتن منبع عکس برای ارسال به تلگرام
    اولویت:
    1. عکس آپلود شده توسط مشتری (file_id تلگرام)
    2. لینک image_url در اکسل/شیت

    Args:
        product: آبجکت محصول
        telegram_media: عکس تلگرام (اگه از قبل گرفته شده)

    Returns:
        file_id یا URL یا None
    """
    # اولویت ۱: عکس آپلود شده
    if telegram_media and telegram_media.file_id:
        return telegram_media.file_id

    # اولویت ۲: لینک image_url
    if product.image_url and product.image_url.strip():
        return product.image_url.strip()

    return None