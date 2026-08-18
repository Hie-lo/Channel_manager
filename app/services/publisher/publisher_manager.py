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
        get_all_product_medias,
    )
    from app.database.connection import AsyncSessionLocal
    from app.config import settings

    # ⚠️ مهم: مطمئن شو از Bot تلگرام استفاده می‌کنیم
    # اگه bot فعلی ربات بله باشه، باید Bot تلگرام بسازیم
    actual_bot = bot
    is_temp_bot = False

    try:
        base_url = str(getattr(bot, "base_url", "") or "")
        if "bale" in base_url.lower():
            # ربات فعلی بله‌ست، Bot تلگرام بساز
            from telegram import Bot
            actual_bot = Bot(token=settings.BOT_TOKEN)
            await actual_bot.initialize()
            is_temp_bot = True
            log.info("[TG Publish] استفاده از Bot تلگرام (ساخته شده از بله)")
    except Exception as e:
        log.error(f"[TG Publish] خطا در ساخت Bot تلگرام: {e}")

    try:
        # گرفتن عکس‌های تلگرام
        async with AsyncSessionLocal() as session:
            tg_medias = await get_product_medias(
                session, product.id, Platform.TELEGRAM
            )

        photo_sources = get_photo_sources_for_platform(product, tg_medias)

        # اگه عکس تلگرام نبود → از بله دانلود و آپلود کن
        if not photo_sources:
            async with AsyncSessionLocal() as session:
                all_medias = await get_all_product_medias(session, product.id)

            bale_medias = [m for m in all_medias if m.platform == Platform.BALE]

            if bale_medias:
                log.info(
                    f"[TG Publish] دانلود {len(bale_medias)} عکس از بله..."
                )

                import os
                import tempfile
                temp_files = []

                try:
                    # دانلود همه عکس‌ها از بله
                    for media in bale_medias:
                        temp_path = await _download_bale_file(product, media.file_id)
                        if temp_path:
                            temp_files.append(temp_path)

                    if len(temp_files) == 0:
                        log.warning("[TG Publish] هیچ عکسی از بله دانلود نشد")

                    elif len(temp_files) == 1:
                        # تک عکس
                        with open(temp_files[0], "rb") as f:
                            message = await actual_bot.send_photo(
                                chat_id=channel.channel_identifier,
                                photo=f,
                                caption=caption,
                            )
                        log.info(f"✅ [TG Publish] پست با ۱ عکس ارسال شد")
                        return UnifiedPublishResult(
                            success=True,
                            message_id=message.message_id,
                            platform=Platform.TELEGRAM,
                        )

                    else:
                        # آلبوم (چند عکس)
                        from telegram import InputMediaPhoto

                        media_list = []
                        file_handles = []

                        for i, path in enumerate(temp_files[:10]):
                            fh = open(path, "rb")
                            file_handles.append(fh)

                            if i == 0:
                                media_list.append(
                                    InputMediaPhoto(media=fh, caption=caption)
                                )
                            else:
                                media_list.append(InputMediaPhoto(media=fh))

                        try:
                            messages = await actual_bot.send_media_group(
                                chat_id=channel.channel_identifier,
                                media=media_list,
                            )
                            log.info(
                                f"✅ [TG Publish] آلبوم با {len(messages)} عکس ارسال شد"
                            )
                            return UnifiedPublishResult(
                                success=True,
                                message_id=messages[0].message_id,
                                platform=Platform.TELEGRAM,
                            )
                        finally:
                            for fh in file_handles:
                                fh.close()

                except Exception as e:
                    log.error(f"[TG Publish] خطا در ارسال عکس بله: {e}")

                finally:
                    for path in temp_files:
                        try:
                            os.unlink(path)
                        except Exception:
                            pass

            # fallback به image_url
            if not photo_sources and product.image_url and product.image_url.strip():
                photo_sources = [product.image_url.strip()]

        if len(photo_sources) > 1:
            result = await publish_media_group_to_telegram(
                bot=actual_bot,
                channel_identifier=channel.channel_identifier,
                caption=caption,
                photo_sources=photo_sources,
            )
        else:
            photo_url = photo_sources[0] if photo_sources else None
            result = await publish_post_to_telegram(
                bot=actual_bot,
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

    finally:
        # cleanup Bot موقت
        if is_temp_bot and actual_bot:
            try:
                await actual_bot.shutdown()
            except Exception:
                pass


async def _edit_telegram_post(
    bot,
    channel: Channel,
    product: Product,
    new_caption: str,
    old_message_id: int,
) -> UnifiedPublishResult:
    """ویرایش پست تلگرام"""
    from app.services.publisher.telegram_publisher import edit_post_in_telegram
    from app.services.product_media_service import get_product_medias
    from app.database.connection import AsyncSessionLocal
    from app.config import settings

    # ⚠️ مطمئن شو از Bot تلگرام استفاده می‌کنیم
    actual_bot = bot
    is_temp_bot = False

    try:
        base_url = str(getattr(bot, "base_url", "") or "")
        if "bale" in base_url.lower():
            from telegram import Bot
            actual_bot = Bot(token=settings.BOT_TOKEN)
            await actual_bot.initialize()
            is_temp_bot = True
    except Exception as e:
        log.error(f"[TG Edit] خطا در ساخت Bot تلگرام: {e}")

    try:
        async with AsyncSessionLocal() as session:
            medias = await get_product_medias(session, product.id, Platform.TELEGRAM)

        has_photo = len(medias) > 0 or bool(product.image_url)

        result = await edit_post_in_telegram(
            bot=actual_bot,
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

    finally:
        if is_temp_bot and actual_bot:
            try:
                await actual_bot.shutdown()
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════
# ایتا
# ═══════════════════════════════════════════════════════════

async def _get_photo_for_eitaa(
    bot,
    product: Product,
) -> Path | None:
    """
    گرفتن یک عکس برای ارسال به ایتا
    از هر پلتفرمی که عکس هست، دانلود می‌کنه
    """
    from app.services.product_media_service import get_all_product_medias
    from app.services.publisher.eitaa_publisher import (
        _download_telegram_file,
        _download_url_to_temp,
    )
    from app.database.connection import AsyncSessionLocal

    # اولویت ۱: عکس از هر پلتفرمی (اولین عکس موجود)
    async with AsyncSessionLocal() as session:
        all_medias = await get_all_product_medias(session, product.id)

    if all_medias:
        first_media = all_medias[0]

        if first_media.platform == Platform.TELEGRAM:
            # عکس تلگرام → دانلود از bot تلگرام
            log.info(f"[Eitaa Photo] دانلود از تلگرام: {first_media.file_id[:30]}...")
            return await _download_telegram_file(bot, first_media.file_id)

        elif first_media.platform == Platform.BALE:
            # عکس بله → دانلود از API بله
            log.info(f"[Eitaa Photo] دانلود از بله: {first_media.file_id[:30]}...")
            return await _download_bale_file(product, first_media.file_id)

    # اولویت ۲: image_url
    if product.image_url and product.image_url.strip():
        log.info(f"[Eitaa Photo] دانلود از URL: {product.image_url[:50]}...")
        return await _download_url_to_temp(product.image_url)

    log.info("[Eitaa Photo] هیچ عکسی پیدا نشد")
    return None


async def _download_bale_file(product, file_id: str) -> Path | None:
    """
    دانلود فایل از بله
    بله API: https://tapi.bale.ai/file/bot{TOKEN}/{file_id}
    """
    import tempfile
    import httpx
    from app.config import settings
    from pathlib import Path as PathLib

    if not settings.BALE_BOT_TOKEN:
        log.warning("[Bale Download] BALE_BOT_TOKEN تنظیم نشده")
        return None

    try:
        # اول file_path رو بگیر
        file_url = f"{settings.BALE_API_BASE}{settings.BALE_BOT_TOKEN}/getFile"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                file_url,
                json={"file_id": file_id},
            )

            if response.status_code != 200:
                log.warning(f"[Bale Download] getFile fail: {response.status_code}")

                # راه جایگزین: مستقیم file_id رو به عنوان URL بفرست
                # بعضی API ها file_id رو به عنوان path می‌پذیرن
                download_url = f"{settings.BALE_FILE_API_BASE}{settings.BALE_BOT_TOKEN}/{file_id}"
            else:
                data = response.json()
                if data.get("ok"):
                    file_path = data.get("result", {}).get("file_path", "")
                    download_url = f"{settings.BALE_FILE_API_BASE}{settings.BALE_BOT_TOKEN}/{file_path}"
                else:
                    download_url = f"{settings.BALE_FILE_API_BASE}{settings.BALE_BOT_TOKEN}/{file_id}"

            # دانلود فایل
            log.info(f"[Bale Download] downloading from: {download_url[:80]}...")
            file_response = await client.get(download_url)

            if file_response.status_code == 200 and len(file_response.content) > 100:
                temp_file = tempfile.NamedTemporaryFile(
                    suffix=".jpg", delete=False, mode="wb"
                )
                temp_file.write(file_response.content)
                temp_file.close()

                log.info(f"[Bale Download] فایل ذخیره شد: {temp_file.name}")
                return PathLib(temp_file.name)
            else:
                log.warning(
                    f"[Bale Download] دانلود fail: status={file_response.status_code}, "
                    f"size={len(file_response.content)}"
                )
                return None

    except Exception as e:
        log.error(f"[Bale Download] خطا: {e}", exc_info=True)
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