"""
مدیریت publisher های مختلف بر اساس پلتفرم
"""

import tempfile
import os
from pathlib import Path
from dataclasses import dataclass, field

from app.database.models import Platform, Channel, Product
from app.utils.logger import log



@dataclass
class UnifiedPublishResult:
    """نتیجه یکسان برای همه پلتفرم‌ها"""
    success: bool
    message_id: int | None = None
    message_ids: list[int] = field(default_factory=list)
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

    elif channel.platform == Platform.BALE:
        return await _publish_to_bale_channel(bot, channel, product, caption)

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
    
    elif channel.platform == Platform.BALE:
        return await _edit_bale_post(
            bot, channel, product, new_caption, old_message_id
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
    import os

    actual_bot = bot
    is_temp_bot = False

    try:
        base_url = str(getattr(bot, "base_url", "") or "")
        if "bale" in base_url.lower():
            from telegram import Bot
            actual_bot = Bot(token=settings.BOT_TOKEN)
            await actual_bot.initialize()
            is_temp_bot = True
            log.info("[TG Publish] استفاده از Bot تلگرام (ساخته شده از بله)")
    except Exception as e:
        log.error(f"[TG Publish] خطا در ساخت Bot تلگرام: {e}")

    try:
        # ۱. گرفتن عکس‌ها
        async with AsyncSessionLocal() as session:
            tg_medias = await get_product_medias(session, product.id, Platform.TELEGRAM)

        photo_sources = get_photo_sources_for_platform(product, tg_medias)

        # 💡 اگر عکس مال پست سفارشی یا بله است (یعنی image_url مقدار file_id بله دارد یا عکس تلگرامی نیست)
        if not photo_sources and product.image_url:
            photo_sources = [product.image_url]

        # ۲. بررسی اینکه آیا عکس‌ها نیاز به دانلود از بله دارند؟ (تشخیص file_id بله)
        processed_photos = []
        temp_files_to_cleanup = []

        for src in photo_sources:
            # عکس نیتیو تلگرام همیشه با AgAC یا AgAD شروع می‌شود
            is_telegram_native = src.startswith("AgAC") or src.startswith("AgAD")
            is_url = src.startswith("http://") or src.startswith("https://")

            # فقط اگر آیدی مربوط به بله باشد (یعنی شامل دو نقطه است و نیتیو تلگرام نیست) دانلود از بله انجام می‌شود
            is_bale_id = not is_telegram_native and not is_url and ":" in src
            
            if is_bale_id:
                log.info(f"[TG Publish] عکس از بله شناسایی شد ({src[:20]}...). در حال دانلود برای تلگرام...")
                temp_p = await _download_bale_file_by_id(src)
                if temp_p:
                    temp_files_to_cleanup.append(temp_p)
                    processed_photos.append(str(temp_p))
            else:
                processed_photos.append(src)

        # ۳. ارسال به تلگرام
        try:
            if len(processed_photos) > 1:
                result = await publish_media_group_to_telegram(
                    bot=actual_bot,
                    channel_identifier=channel.channel_identifier,
                    caption=caption,
                    photo_sources=processed_photos,
                )
            else:
                photo_url = processed_photos[0] if processed_photos else None
                
                # اگر عکس بصورت فایل موقت محلی دانلود شده
                if photo_url and os.path.exists(photo_url):
                    with open(photo_url, "rb") as f:
                        msg = await actual_bot.send_photo(
                            chat_id=channel.channel_identifier,
                            photo=f,
                            caption=caption[:1024]
                        )
                        result = UnifiedPublishResult(success=True, message_id=msg.message_id, message_ids=[msg.message_id], platform=Platform.TELEGRAM)
                else:
                    result = await publish_post_to_telegram(
                        bot=actual_bot,
                        channel_identifier=channel.channel_identifier,
                        caption=caption,
                        photo_url=photo_url,
                    )

            return UnifiedPublishResult(
                success=result.success,
                message_id=result.message_id,
                message_ids=getattr(result, 'message_ids', []),
                platform=Platform.TELEGRAM,
                error_message=result.error_message,
                used_fallback=result.used_fallback,
            )

        finally:
            # پاکسازی فایل‌های موقت دانلود شده
            for tp in temp_files_to_cleanup:
                if os.path.exists(tp):
                    try: os.remove(tp)
                    except Exception: pass

    finally:
        if is_temp_bot and actual_bot:
            try: await actual_bot.shutdown()
            except Exception: pass


async def _edit_telegram_post(
    bot,
    channel: Channel,
    product: Product,
    new_caption: str,
    old_message_id: int,
) -> UnifiedPublishResult:
    """ویرایش هوشمند پست تلگرام (کپشن یا متن)"""
    from app.services.publisher.telegram_publisher import edit_post_in_telegram
    from app.services.product_media_service import get_product_medias, get_all_product_medias
    from app.database.connection import AsyncSessionLocal
    from app.database.models import PostedMessage

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
            # بررسی اینکه آیا رکورد قبلی عکس داشته یا فقط متنی بوده
            posted_res = await session.execute(
                select(PostedMessage).where(
                    PostedMessage.product_id == product.id,
                    PostedMessage.channel_id == channel.id
                )
            )
            posted_rec = posted_res.scalar_one_or_none()
            
            all_medias = await get_all_product_medias(session, product.id)

        # اگر پست قبلی بدون عکس بوده یا عکس ندارد، editMessageText بزن، در غیر این صورت editMessageCaption
        has_photo = bool(all_medias) or bool(product.image_url)
        
        # اگر در رکورد ثبت شده که آخرین بار Fallback به متنی شده بود، has_photo را False کن
        if posted_rec and posted_rec.last_caption and not posted_rec.last_price:
            pass # قابلیت تحلیل بیشتر در صورت نیاز

        result = await edit_post_in_telegram(
            bot=actual_bot,
            channel_identifier=channel.channel_identifier,
            message_id=old_message_id,
            new_caption=new_caption,
            has_photo=has_photo,
        )

        # 💡 اگر خطا داد که Caption ندارد، تلاش مجدد با Edit Text (برای ایمنی ۱۰۰٪)
        if not result.success and "no caption" in result.error_message.lower():
            log.warning("[TG Edit] پست بدون کپشن بود، تلاش مجدد با Edit Text...")
            result = await edit_post_in_telegram(
                bot=actual_bot,
                channel_identifier=channel.channel_identifier,
                message_id=old_message_id,
                new_caption=new_caption,
                has_photo=False, # اجبار به Edit Text
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

# ═══════════════════════════════════════════════════════════
# بله (Bale)
# ═══════════════════════════════════════════════════════════

async def _publish_to_bale_channel(
    bot,
    channel: Channel,
    product: Product,
    caption: str,
) -> UnifiedPublishResult:
    """
    ارسال پست به کانال بله
    چون API بله مثل تلگرامه، مستقیم از bot بله استفاده می‌کنیم
    """
    from app.services.product_media_service import (
        get_product_medias,
        get_photo_sources_for_platform,
        get_all_product_medias,
    )
    from app.database.connection import AsyncSessionLocal
    from app.config import settings
    import os

    # ─── مطمئن شو Bot بله داریم ───
    actual_bot = bot
    is_temp_bot = False

    try:
        base_url = str(getattr(bot, "base_url", "") or "")
        if "bale" not in base_url.lower():
            # ربات فعلی تلگرامه، Bot بله بساز
            if settings.BALE_BOT_TOKEN:
                from telegram import Bot
                actual_bot = Bot(
                    token=settings.BALE_BOT_TOKEN,
                    base_url=settings.BALE_API_BASE,
                    base_file_url=settings.BALE_FILE_API_BASE,
                )
                await actual_bot.initialize()
                is_temp_bot = True
                log.info("[Bale Publish] استفاده از Bot بله (ساخته شده از تلگرام)")
            else:
                return UnifiedPublishResult(
                    success=False,
                    platform=Platform.BALE,
                    error_message="توکن بله تنظیم نشده",
                )
    except Exception as e:
        log.error(f"[Bale Publish] خطا در ساخت Bot بله: {e}")
        return UnifiedPublishResult(
            success=False,
            platform=Platform.BALE,
            error_message=f"خطا در ساخت Bot بله: {str(e)[:100]}",
        )

    try:
        # ─── عکس‌ها ───
        # اول عکس‌های بله (file_id مستقیم)
        async with AsyncSessionLocal() as session:
            bale_medias = await get_product_medias(
                session, product.id, Platform.BALE
            )

        # کوتاه کردن caption
        max_len = 1024
        if len(caption) > max_len:
            caption = caption[:max_len - 3] + "..."

        if bale_medias:
            # ─── file_id بله داریم → مستقیم بفرست ───
            if len(bale_medias) == 1:
                # تک عکس
                try:
                    message = await actual_bot.send_photo(
                        chat_id=channel.channel_identifier,
                        photo=bale_medias[0].file_id,
                        caption=caption,
                    )
                    log.info(f"✅ [Bale Publish] پست با ۱ عکس ارسال شد")
                    return UnifiedPublishResult(
                        success=True,
                        message_id=message.message_id,
                        message_ids=[message.message_id],
                        platform=Platform.BALE,
                    )
                except Exception as e:
                    log.error(f"[Bale Publish] خطا در ارسال عکس: {e}")

            else:
                # آلبوم
                try:
                    from telegram import InputMediaPhoto

                    media_list = []
                    for i, media in enumerate(bale_medias[:10]):
                        if i == 0:
                            media_list.append(
                                InputMediaPhoto(
                                    media=media.file_id,
                                    caption=caption,
                                )
                            )
                        else:
                            media_list.append(
                                InputMediaPhoto(media=media.file_id)
                            )

                    messages = await actual_bot.send_media_group(
                        chat_id=channel.channel_identifier,
                        media=media_list,
                    )
                    all_ids = [msg.message_id for msg in messages]
                    log.info(
                        f"✅ [Bale Publish] آلبوم {len(messages)} عکسی "
                        f"ارسال شد (ids: {all_ids})"
                    )
                    return UnifiedPublishResult(
                        success=True,
                        message_id=all_ids[0],
                        message_ids=all_ids,
                        platform=Platform.BALE,
                    )
                except Exception as e:
                    log.error(f"[Bale Publish] خطا در ارسال آلبوم: {e}")

        # ─── اگه عکس بله نبود، از تلگرام یا URL ───
        if not bale_medias:
            # عکس تلگرام داره؟ دانلود و آپلود
            async with AsyncSessionLocal() as session:
                tg_medias = await get_product_medias(
                    session, product.id, Platform.TELEGRAM
                )

            if tg_medias:
                # دانلود از تلگرام و آپلود به بله
                temp_files = []
                try:
                    from app.services.publisher.eitaa_publisher import _download_telegram_file

                    # ⚠️ برای دانلود از تلگرام باید Bot تلگرام بسازیم
                    from telegram import Bot
                    tg_bot = Bot(token=settings.BOT_TOKEN)
                    await tg_bot.initialize()

                    try:
                        for media in tg_medias[:10]:
                            temp_path = await _download_telegram_file(
                                tg_bot, media.file_id
                            )
                            if temp_path:
                                temp_files.append(temp_path)
                    finally:
                        await tg_bot.shutdown()

                    if len(temp_files) == 1:
                        with open(temp_files[0], "rb") as f:
                            message = await actual_bot.send_photo(
                                chat_id=channel.channel_identifier,
                                photo=f,
                                caption=caption,
                            )
                        log.info(f"✅ [Bale Publish] عکس تلگرام → بله ارسال شد")
                        return UnifiedPublishResult(
                            success=True,
                            message_id=message.message_id,
                            message_ids=[message.message_id],
                            platform=Platform.BALE,
                        )
                    elif len(temp_files) > 1:
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
                            all_ids = [msg.message_id for msg in messages]
                            log.info(
                                f"✅ [Bale Publish] آلبوم تلگرام → بله ارسال شد"
                            )
                            return UnifiedPublishResult(
                                success=True,
                                message_id=all_ids[0],
                                message_ids=all_ids,
                                platform=Platform.BALE,
                            )
                        finally:
                            for fh in file_handles:
                                fh.close()

                except Exception as e:
                    log.error(f"[Bale Publish] خطا در انتقال عکس تلگرام: {e}")
                finally:
                    for path in temp_files:
                        try:
                            os.unlink(path)
                        except Exception:
                            pass

            # ─── image_url ───
            if product.image_url and product.image_url.strip():
                try:
                    message = await actual_bot.send_photo(
                        chat_id=channel.channel_identifier,
                        photo=product.image_url.strip(),
                        caption=caption,
                    )
                    log.info(f"✅ [Bale Publish] عکس URL ارسال شد")
                    return UnifiedPublishResult(
                        success=True,
                        message_id=message.message_id,
                        platform=Platform.BALE,
                    )
                except Exception as e:
                    log.warning(f"[Bale Publish] URL fail: {e}")

        # ─── fallback: ارسال متنی ───
        try:
            message = await actual_bot.send_message(
                chat_id=channel.channel_identifier,
                text=caption,
            )
            log.info(f"✅ [Bale Publish] پست متنی ارسال شد")
            return UnifiedPublishResult(
                success=True,
                message_id=message.message_id,
                platform=Platform.BALE,
                used_fallback=True,
            )
        except Exception as e:
            log.error(f"[Bale Publish] خطا در ارسال متنی: {e}")
            return UnifiedPublishResult(
                success=False,
                platform=Platform.BALE,
                error_message=str(e)[:100],
            )

    finally:
        if is_temp_bot and actual_bot:
            try:
                await actual_bot.shutdown()
            except Exception:
                pass


async def _edit_bale_post(
    bot,
    channel: Channel,
    product: Product,
    new_caption: str,
    old_message_id: int,
) -> UnifiedPublishResult:
    """ویرایش پست بله"""
    from app.config import settings
    from app.services.product_media_service import get_product_medias
    from app.database.connection import AsyncSessionLocal

    actual_bot = bot
    is_temp_bot = False

    try:
        base_url = str(getattr(bot, "base_url", "") or "")
        if "bale" not in base_url.lower():
            if settings.BALE_BOT_TOKEN:
                from telegram import Bot
                actual_bot = Bot(
                    token=settings.BALE_BOT_TOKEN,
                    base_url=settings.BALE_API_BASE,
                    base_file_url=settings.BALE_FILE_API_BASE,
                )
                await actual_bot.initialize()
                is_temp_bot = True
    except Exception as e:
        log.error(f"[Bale Edit] خطا: {e}")

    try:
        max_len = 1024
        if len(new_caption) > max_len:
            new_caption = new_caption[:max_len - 3] + "..."

        async with AsyncSessionLocal() as session:
            medias = await get_product_medias(session, product.id, Platform.BALE)

        has_photo = len(medias) > 0 or bool(product.image_url)

        try:
            if has_photo:
                await actual_bot.edit_message_caption(
                    chat_id=channel.channel_identifier,
                    message_id=old_message_id,
                    caption=new_caption,
                )
            else:
                await actual_bot.edit_message_text(
                    chat_id=channel.channel_identifier,
                    message_id=old_message_id,
                    text=new_caption,
                )

            log.info(f"✅ [Bale Edit] پست ادیت شد: msg={old_message_id}")
            return UnifiedPublishResult(
                success=True,
                message_id=old_message_id,
                platform=Platform.BALE,
            )

        except Exception as e:
            error_msg = str(e).lower()
            if "message is not modified" in error_msg:
                return UnifiedPublishResult(
                    success=True,
                    message_id=old_message_id,
                    platform=Platform.BALE,
                )
            log.error(f"[Bale Edit] خطا: {e}")
            return UnifiedPublishResult(
                success=False,
                platform=Platform.BALE,
                error_message=str(e)[:100],
            )

    finally:
        if is_temp_bot and actual_bot:
            try:
                await actual_bot.shutdown()
            except Exception:
                pass

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

async def _cache_file_id(
    product_id: int,
    platform: Platform,
    file_id: str,
) -> None:
    """
    کش کردن file_id یک پلتفرم
    وقتی عکس از پلتفرم A دانلود و به پلتفرم B آپلود شد،
    file_id پلتفرم B رو ذخیره کن تا دفعه بعد نیازی به دانلود نباشه
    """
    from app.services.product_media_service import set_product_media
    from app.database.connection import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as session:
            await set_product_media(
                session=session,
                product_id=product_id,
                platform=platform,
                file_id=file_id,
                uploaded_by_customer=False,  # سیستم ذخیره کرده
            )
    except Exception as e:
        log.warning(f"[Cache] خطا در ذخیره file_id: {e}")

async def _download_bale_file_by_id(file_id: str) -> Path | None:
    """دانلود یک فایل از بله صرفاً با داشتن file_id (مستقل از مدل Product)"""
    import tempfile
    import httpx
    from app.config import settings

    if not settings.BALE_BOT_TOKEN or not file_id:
        return None

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            file_url = f"{settings.BALE_API_BASE}{settings.BALE_BOT_TOKEN}/getFile"
            response = await client.post(file_url, json={"file_id": file_id})

            if response.status_code == 200 and response.json().get("ok"):
                file_path = response.json().get("result", {}).get("file_path", "")
                download_url = f"{settings.BALE_FILE_API_BASE}{settings.BALE_BOT_TOKEN}/{file_path}"
            else:
                download_url = f"{settings.BALE_FILE_API_BASE}{settings.BALE_BOT_TOKEN}/{file_id}"

            file_response = await client.get(download_url)
            if file_response.status_code == 200 and len(file_response.content) > 100:
                temp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False, mode="wb")
                temp_file.write(file_response.content)
                temp_file.close()
                return Path(temp_file.name)
    except Exception as e:
        log.error(f"[Bale Download By ID] خطا در دانلود {file_id}: {e}")
    return None