"""
مدیریت publisher های مختلف بر اساس پلتفرم
"""

import tempfile
import os
from pathlib import Path
from dataclasses import dataclass

from app.database.models import Platform, Channel, Product
from app.utils.logger import log


@dataclass
class UnifiedPublishResult:
    """نتیجه یکسان برای همه پلتفرم‌ها"""
    success: bool
    message_id: int | None = None
    platform: Platform = Platform.TELEGRAM
    error_message: str = ""
    used_fallback: bool = False


async def publish_to_channel(
    bot,
    channel: Channel,
    product: Product,
    caption: str,
    eitaa_token: str | None = None,
) -> UnifiedPublishResult:
    """
    ارسال پست به یک کانال (تشخیص خودکار پلتفرم)

    Args:
        bot: نمونه Bot تلگرام
        channel: کانال هدف
        product: محصول
        caption: متن پست
        eitaa_token: توکن ایتا (فقط برای کانال‌های ایتا)

    Returns:
        UnifiedPublishResult
    """
    if channel.platform == Platform.TELEGRAM:
        return await _publish_to_telegram_channel(bot, channel, product, caption)

    elif channel.platform == Platform.EITAA:
        if not eitaa_token:
            return UnifiedPublishResult(
                success=False,
                platform=Platform.EITAA,
                error_message="توکن ایتا موجود نیست",
            )
        return await _publish_to_eitaa_channel(bot, channel, product, caption, eitaa_token)

    else:
        return UnifiedPublishResult(
            success=False,
            platform=channel.platform,
            error_message=f"پلتفرم {channel.platform.value} پشتیبانی نمی‌شود",
        )


async def edit_channel_post(
    bot,
    channel: Channel,
    product: Product,
    new_caption: str,
    old_message_id: int,
    eitaa_token: str | None = None,
) -> UnifiedPublishResult:
    """
    ویرایش پست موجود (تشخیص خودکار پلتفرم)
    برای ایتا: delete + repost
    """
    if channel.platform == Platform.TELEGRAM:
        return await _edit_telegram_post(
            bot, channel, product, new_caption, old_message_id
        )

    elif channel.platform == Platform.EITAA:
        if not eitaa_token:
            return UnifiedPublishResult(
                success=False,
                platform=Platform.EITAA,
                error_message="توکن ایتا موجود نیست",
            )
        return await _edit_eitaa_post(
            bot, channel, product, new_caption, old_message_id, eitaa_token
        )

    else:
        return UnifiedPublishResult(
            success=False,
            platform=channel.platform,
            error_message=f"پلتفرم {channel.platform.value} پشتیبانی نمی‌شود",
        )


# ═══════════════════════════════════════════════════════════
# تلگرام
# ═══════════════════════════════════════════════════════════

async def _publish_to_telegram_channel(
    bot,
    channel: Channel,
    product: Product,
    caption: str,
) -> UnifiedPublishResult:
    """ارسال پست به کانال تلگرام"""
    from app.services.publisher.telegram_publisher import (
        publish_post_to_telegram,
        publish_media_group_to_telegram,
    )
    from app.services.product_media_service import (
        get_product_medias,
        get_photo_sources_for_platform,
    )
    from app.database.connection import AsyncSessionLocal

    # گرفتن عکس‌ها
    async with AsyncSessionLocal() as session:
        uploaded_medias = await get_product_medias(
            session, product.id, Platform.TELEGRAM
        )

    photo_sources = get_photo_sources_for_platform(product, uploaded_medias)

    if len(photo_sources) > 1:
        # آلبوم
        result = await publish_media_group_to_telegram(
            bot=bot,
            channel_identifier=channel.channel_identifier,
            caption=caption,
            photo_sources=photo_sources,
        )
    else:
        # تک عکس یا بدون عکس
        photo_url = photo_sources[0] if photo_sources else None
        result = await publish_post_to_telegram(
            bot=bot,
            channel_identifier=channel.channel_identifier,
            caption=caption,
            photo_url=photo_url,
        )

    return UnifiedPublishResult(
        success=result.success,
        message_id=result.message_id,
        platform=Platform.TELEGRAM,
        error_message=result.error_message,
        used_fallback=result.used_fallback,
    )


async def _edit_telegram_post(
    bot,
    channel: Channel,
    product: Product,
    new_caption: str,
    old_message_id: int,
) -> UnifiedPublishResult:
    """ویرایش پست تلگرام (فقط کپشن)"""
    from app.services.publisher.telegram_publisher import edit_post_in_telegram
    from app.services.product_media_service import get_product_medias
    from app.database.connection import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        medias = await get_product_medias(session, product.id, Platform.TELEGRAM)

    has_photo = len(medias) > 0 or bool(product.image_url)

    result = await edit_post_in_telegram(
        bot=bot,
        channel_identifier=channel.channel_identifier,
        message_id=old_message_id,
        new_caption=new_caption,
        has_photo=has_photo,
    )

    return UnifiedPublishResult(
        success=result.success,
        message_id=result.message_id,
        platform=Platform.TELEGRAM,
        error_message=result.error_message,
    )


# ═══════════════════════════════════════════════════════════
# ایتا
# ═══════════════════════════════════════════════════════════

async def _get_photo_for_eitaa(bot, product):
    """
    گرفتن یک عکس برای ارسال به ایتا
    اولویت: عکس‌های تلگرام (چون bot تلگرامیه، راحت‌تر دانلود می‌کنه)
    اگه نبود: image_url
    """
    from app.services.product_media_service import get_product_medias
    from app.services.publisher.eitaa_publisher import _download_telegram_file
    from app.database.connection import AsyncSessionLocal

    # اول عکس‌های تلگرام (چون bot تلگرام راحت دانلود می‌کنه)
    async with AsyncSessionLocal() as session:
        tg_medias = await get_product_medias(session, product.id, Platform.TELEGRAM)

    if tg_medias:
        first_media = tg_medias[0]
        log.info(f"[Eitaa Photo] دانلود از تلگرام: {first_media.file_id[:30]}...")
        return await _download_telegram_file(bot, first_media.file_id)

    # اگه تلگرام نبود، image_url استفاده کن
    if product.image_url and product.image_url.strip():
        log.info(f"[Eitaa Photo] استفاده از image_url")
        return None  # publisher خودش دانلود می‌کنه

    return None


async def _publish_to_eitaa_channel(
    bot,
    channel: Channel,
    product: Product,
    caption: str,
    eitaa_token: str,
) -> UnifiedPublishResult:
    """ارسال پست به کانال ایتا"""
    from app.services.publisher.eitaa_publisher import (
        publish_post_to_eitaa,
        _cleanup_temp_file,
    )

    # آماده‌سازی عکس
    temp_photo_path = await _get_photo_for_eitaa(bot, product)

    try:
        result = await publish_post_to_eitaa(
            eitaa_token=eitaa_token,
            chat_id=channel.channel_identifier,
            caption=caption,
            photo_local_path=temp_photo_path,
            photo_url=product.image_url if not temp_photo_path else None,
        )

        return UnifiedPublishResult(
            success=result.success,
            message_id=result.message_id,
            platform=Platform.EITAA,
            error_message=result.error_message,
            used_fallback=result.used_fallback,
        )
    finally:
        _cleanup_temp_file(temp_photo_path)


async def _edit_eitaa_post(
    bot,
    channel: Channel,
    product: Product,
    new_caption: str,
    old_message_id: int,
    eitaa_token: str,
) -> UnifiedPublishResult:
    """ویرایش پست ایتا (delete + repost)"""
    from app.services.publisher.eitaa_publisher import (
        edit_post_in_eitaa,
        _cleanup_temp_file,
    )

    temp_photo_path = await _get_photo_for_eitaa(bot, product)

    try:
        result = await edit_post_in_eitaa(
            eitaa_token=eitaa_token,
            chat_id=channel.channel_identifier,
            old_message_id=old_message_id,
            new_caption=new_caption,
            photo_local_path=temp_photo_path,
            photo_url=product.image_url if not temp_photo_path else None,
        )

        return UnifiedPublishResult(
            success=result.success,
            message_id=result.message_id,
            platform=Platform.EITAA,
            error_message=result.error_message,
            used_fallback=result.used_fallback,
        )
    finally:
        _cleanup_temp_file(temp_photo_path)