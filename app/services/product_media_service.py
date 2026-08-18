"""
سرویس مدیریت عکس‌های محصول (تک عکس یا چند عکس / آلبوم)
"""

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ProductPlatformMedia, Platform
from app.utils.logger import log
from app.utils.time import utc_now_naive


MAX_PHOTOS_PER_PRODUCT = 10  # محدودیت تلگرام برای media group


async def get_product_medias(
    session: AsyncSession,
    product_id: int,
    platform: Platform = Platform.TELEGRAM,
) -> list[ProductPlatformMedia]:
    """گرفتن همه عکس‌های محصول برای یه پلتفرم (به ترتیب order)"""
    result = await session.execute(
        select(ProductPlatformMedia)
        .where(
            ProductPlatformMedia.product_id == product_id,
            ProductPlatformMedia.platform == platform,
        )
        .order_by(ProductPlatformMedia.media_order.asc())
    )
    return list(result.scalars().all())


async def add_product_media(
    session: AsyncSession,
    product_id: int,
    file_id: str,
    platform: Platform = Platform.TELEGRAM,
    uploaded_by_customer: bool = True,
) -> ProductPlatformMedia | None:
    """
    اضافه کردن یه عکس جدید به آخر لیست
    اگه از حد مجاز بیشتر بشه، None برمی‌گرده
    """
    existing = await get_product_medias(session, product_id, platform)

    if len(existing) >= MAX_PHOTOS_PER_PRODUCT:
        log.warning(
            f"محصول {product_id} به حداکثر تعداد عکس ({MAX_PHOTOS_PER_PRODUCT}) رسیده"
        )
        return None

    # ترتیب جدید = آخرین + 1
    next_order = max([m.media_order for m in existing], default=-1) + 1

    media = ProductPlatformMedia(
        product_id=product_id,
        platform=platform,
        file_id=file_id,
        media_order=next_order,
        uploaded_by_customer=uploaded_by_customer,
        created_at=utc_now_naive(),
    )
    session.add(media)
    await session.commit()
    await session.refresh(media)
    log.info(
        f"📷 عکس جدید (order={next_order}) به محصول {product_id} اضافه شد"
    )
    return media


async def remove_all_product_media(
    session: AsyncSession,
    product_id: int,
    platform: Platform | None = None,
) -> int:
    """
    حذف همه عکس‌های آپلود شده مشتری
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


async def count_product_medias(
    session: AsyncSession,
    product_id: int,
    platform: Platform = Platform.TELEGRAM,
) -> int:
    """شمارش تعداد عکس‌های محصول"""
    medias = await get_product_medias(session, product_id, platform)
    return len(medias)


def get_photo_sources_for_platform(
    product,
    medias: list[ProductPlatformMedia],
) -> list[str]:
    """
    گرفتن لیست منابع عکس برای ارسال
    اولویت:
    1. عکس‌های آپلود شده توسط مشتری (لیست file_id ها)
    2. لینک image_url در اکسل/شیت (یک URL)

    Returns:
        لیست از file_id یا URL ها (یا لیست خالی اگه هیچی نبود)
    """
    # اولویت ۱: عکس‌های آپلود شده
    if medias:
        return [m.file_id for m in medias]

    # اولویت ۲: لینک image_url
    if product.image_url and product.image_url.strip():
        return [product.image_url.strip()]

    return []
async def count_all_product_medias(
    session: AsyncSession,
    product_id: int,
) -> int:
    """شمارش کل عکس‌های محصول در همه پلتفرم‌ها"""
    result = await session.execute(
        select(ProductPlatformMedia).where(
            ProductPlatformMedia.product_id == product_id
        )
    )
    medias = list(result.scalars().all())
    return len(medias)


async def get_all_product_medias(
    session: AsyncSession,
    product_id: int,
) -> list[ProductPlatformMedia]:
    """گرفتن همه عکس‌های محصول در همه پلتفرم‌ها"""
    result = await session.execute(
        select(ProductPlatformMedia)
        .where(ProductPlatformMedia.product_id == product_id)
        .order_by(
            ProductPlatformMedia.platform.asc(),
            ProductPlatformMedia.media_order.asc(),
        )
    )
    return list(result.scalars().all())

async def set_product_media(
    session: AsyncSession,
    product_id: int,
    platform: Platform,
    file_id: str,
    uploaded_by_customer: bool = False,
) -> ProductPlatformMedia:
    """ذخیره یا آپدیت file_id"""
    # چک کن آیا قبلاً هست
    existing = await get_product_medias(session, product_id, platform)

    if existing and not uploaded_by_customer:
        # فقط اولین عکس رو آپدیت کن (کش)
        existing[0].file_id = file_id
        existing[0].updated_at = utc_now_naive()
        await session.commit()
        return existing[0]

    # اگه نبود، اضافه کن
    return await add_product_media(
        session=session,
        product_id=product_id,
        file_id=file_id,
        platform=platform,
        uploaded_by_customer=uploaded_by_customer,
    )