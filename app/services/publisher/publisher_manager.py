"""
مدیریت publisher های مختلف بر اساس پلتفرم
"""

import tempfile
import os
from pathlib import Path
from dataclasses import dataclass, field
from app.config import settings
from sqlalchemy import select
from app.database.models import Platform, Channel, Product, PostedMessage, Business
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


def _fill_contact_id_placeholder(caption: str, channel: Channel, fallback_contact: str = "") -> str:
    """
    پر کردن placeholder {contact_id} و {contact} با آیدی تماس کانال بر اساس پلتفرم
    """
    # Check if any contact placeholder exists
    if "{contact_id}" not in caption and "{contact}" not in caption:
        return caption
    
    contact_id = ""
    if channel.platform == Platform.TELEGRAM:
        contact_id = channel.contact_id_telegram or ""
    elif channel.platform == Platform.BALE:
        contact_id = channel.contact_id_bale or ""
    elif channel.platform == Platform.EITAA:
        contact_id = channel.contact_id_eitaa or ""

    if not contact_id:
        contact_id = fallback_contact
    
    # جایگزینی placeholder ها
    result = caption.replace("{contact_id}", contact_id)
    result = result.replace("{contact}", contact_id)

    if not contact_id:
        return "\n".join(
            line for line in caption.split("\n")
            if "{contact_id}" not in line and "{contact}" not in line
        )

    return result


def _fill_phone_placeholder(caption: str, channel: Channel) -> str:
    phone = {
        Platform.TELEGRAM: channel.phone_telegram,
        Platform.BALE: channel.phone_bale,
        Platform.EITAA: channel.phone_eitaa,
    }.get(channel.platform) or ""
    if phone:
        return caption.replace("{phone}", phone)
    return "\n".join(
        line for line in caption.split("\n")
        if "{phone}" not in line
    )


async def _get_business_contact(channel: Channel) -> str:
    from app.database.connection import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Business.contact_text).where(Business.customer_id == channel.customer_id).limit(1)
        )
        return result.scalar_one_or_none() or ""


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
    # پر کردن {contact_id} برای این کانال
    fallback_contact = await _get_business_contact(channel)
    caption_with_contact = _fill_contact_id_placeholder(caption, channel, fallback_contact)
    caption_with_contact = _fill_phone_placeholder(caption_with_contact, channel)
    
    if channel.platform == Platform.TELEGRAM:
        return await _publish_to_telegram_channel(bot, channel, product, caption_with_contact)

    elif channel.platform == Platform.EITAA:
        if not eitaa_token:
            return UnifiedPublishResult(
                success=False,
                platform=Platform.EITAA,
                error_message="توکن ایتا موجود نیست",
            )
        return await _publish_to_eitaa_channel(bot, channel, product, caption_with_contact, eitaa_token)

    elif channel.platform == Platform.BALE:
        return await _publish_to_bale_channel(bot, channel, product, caption_with_contact)

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
    # پر کردن {contact_id} برای این کانال
    fallback_contact = await _get_business_contact(channel)
    caption_with_contact = _fill_contact_id_placeholder(new_caption, channel, fallback_contact)
    caption_with_contact = _fill_phone_placeholder(caption_with_contact, channel)
    
    if channel.platform == Platform.TELEGRAM:
        return await _edit_telegram_post(
            bot, channel, product, caption_with_contact, old_message_id
        )

    elif channel.platform == Platform.EITAA:
        if not eitaa_token:
            return UnifiedPublishResult(
                success=False,
                platform=Platform.EITAA,
                error_message="توکن ایتا موجود نیست",
            )
        return await _edit_eitaa_post(
            bot, channel, product, caption_with_contact, old_message_id, eitaa_token
        )
    
    elif channel.platform == Platform.BALE:
        return await _edit_bale_post(
            bot, channel, product, caption_with_contact, old_message_id
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
    """ارسال پست به کانال تلگرام (با پشتیبانی از آلبوم عکس و ویدیو)"""
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
        # ─── ۱. پشتیبانی از پست سفارشی (Dummy Product) ───
        if product.sku == "CUSTOM" and product.specs and "custom_medias" in product.specs:
            custom_medias = product.specs["custom_medias"]
            
            if not custom_medias:
                res = await publish_post_to_telegram(actual_bot, channel.channel_identifier, caption)
                return UnifiedPublishResult(success=res.success, message_id=res.message_id, platform=Platform.TELEGRAM, error_message=res.error_message)

            if len(custom_medias) == 1:
                m = custom_medias[0]
                src = m["file_id"]
                is_video = (m["type"] == "video")
                is_bale_id = (":" in src) and not src.startswith("http")
                
                if is_bale_id:
                    temp_p = await _download_bale_file_by_id(src, is_video=is_video)
                    if temp_p:
                        try:
                            with open(temp_p, "rb") as f:
                                if is_video:
                                    msg = await actual_bot.send_video(chat_id=channel.channel_identifier, video=f, caption=caption[:1024])
                                else:
                                    msg = await actual_bot.send_photo(chat_id=channel.channel_identifier, photo=f, caption=caption[:1024])
                            return UnifiedPublishResult(success=True, message_id=msg.message_id, message_ids=[msg.message_id], platform=Platform.TELEGRAM)
                        finally:
                            if os.path.exists(temp_p): os.remove(temp_p)
                else:
                    if is_video:
                        msg = await actual_bot.send_video(chat_id=channel.channel_identifier, video=src, caption=caption[:1024])
                        return UnifiedPublishResult(success=True, message_id=msg.message_id, message_ids=[msg.message_id], platform=Platform.TELEGRAM)
                    else:
                        res = await publish_post_to_telegram(actual_bot, channel.channel_identifier, caption, photo_url=src)
                        return UnifiedPublishResult(success=res.success, message_id=res.message_id, message_ids=[res.message_id] if res.message_id else [], platform=Platform.TELEGRAM)

            else:
                # 🚀 ارسال آلبوم ترکیبی (عکس و ویدیو)
                from telegram import InputMediaPhoto, InputMediaVideo
                media_list = []
                temp_files_to_cleanup = []

                try:
                    for i, m in enumerate(custom_medias[:10]):
                        cap = caption[:1024] if i == 0 else None
                        src = m["file_id"]
                        is_video = (m["type"] == "video")
                        is_bale_id = (":" in src) and not src.startswith("http")

                        if is_bale_id:
                            temp_p = await _download_bale_file_by_id(src, is_video=is_video)
                            if temp_p:
                                temp_files_to_cleanup.append(temp_p)
                                fh = open(temp_p, "rb")
                                if is_video: media_list.append(InputMediaVideo(media=fh, caption=cap))
                                else: media_list.append(InputMediaPhoto(media=fh, caption=cap))
                        else:
                            if is_video: media_list.append(InputMediaVideo(media=src, caption=cap))
                            else: media_list.append(InputMediaPhoto(media=src, caption=cap))

                    messages = await actual_bot.send_media_group(chat_id=channel.channel_identifier, media=media_list)
                    all_ids = [msg.message_id for msg in messages]
                    return UnifiedPublishResult(success=True, message_id=all_ids[0], message_ids=all_ids, platform=Platform.TELEGRAM)
                finally:
                    for tp in temp_files_to_cleanup:
                        if os.path.exists(tp):
                            try: os.remove(tp)
                            except: pass

        # ─── ۲. روال عادی برای محصولات معمولی دیتابیس ───
        async with AsyncSessionLocal() as session:
            tg_medias = await get_product_medias(session, product.id, Platform.TELEGRAM)

        photo_sources = get_photo_sources_for_platform(product, tg_medias)

        # اگر عکس تلگرام نبود، سعی کن از بله بگیری
        if not photo_sources:
            async with AsyncSessionLocal() as session:
                all_medias = await get_all_product_medias(session, product.id)
            
            bale_medias = [m for m in all_medias if m.platform == Platform.BALE]
            
            if bale_medias:
                log.info(f"[TG Publish] دانلود {len(bale_medias)} عکس از بله...")
                temp_files = []
                try:
                    for media in bale_medias:
                        # پیش‌فرض در محصولات معمولی عکس (jpg) است
                        temp_path = await _download_bale_file_by_id(media.file_id, is_video=False)
                        if temp_path:
                            temp_files.append(temp_path)

                    if len(temp_files) == 1:
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
                            message_ids=[message.message_id],
                            platform=Platform.TELEGRAM,
                        )
                    elif len(temp_files) > 1:
                        from telegram import InputMediaPhoto
                        media_list = []
                        file_handles = []
                        for i, path in enumerate(temp_files[:10]):
                            fh = open(path, "rb")
                            file_handles.append(fh)
                            cap = caption if i == 0 else None
                            media_list.append(InputMediaPhoto(media=fh, caption=cap))

                        try:
                            messages = await actual_bot.send_media_group(
                                chat_id=channel.channel_identifier,
                                media=media_list,
                            )
                            all_ids = [msg.message_id for msg in messages]
                            log.info(f"✅ [TG Publish] آلبوم با {len(messages)} عکس ارسال شد")
                            return UnifiedPublishResult(
                                success=True,
                                message_id=all_ids[0],
                                message_ids=all_ids,
                                platform=Platform.TELEGRAM,
                            )
                        finally:
                            for fh in file_handles:
                                fh.close()
                except Exception as e:
                    log.error(f"[TG Publish] خطا در ارسال عکس بله: {e}")
                finally:
                    for path in temp_files:
                        if os.path.exists(path):
                            try: os.remove(path)
                            except: pass

        if not photo_sources and product.image_url:
            photo_sources = [product.image_url]

        if len(photo_sources) > 1:
            result = await publish_media_group_to_telegram(bot=actual_bot, channel_identifier=channel.channel_identifier, caption=caption, photo_sources=photo_sources)
        else:
            photo_url = photo_sources[0] if photo_sources else None
            result = await publish_post_to_telegram(bot=actual_bot, channel_identifier=channel.channel_identifier, caption=caption, photo_url=photo_url)

        return UnifiedPublishResult(success=result.success, message_id=result.message_id, message_ids=getattr(result, 'message_ids', []), platform=Platform.TELEGRAM, error_message=result.error_message)

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
    """گرفتن یک فایل مدیا برای ارسال به ایتا با تشخیص دقیق آیدی‌های بله و تلگرام"""
    from app.services.product_media_service import get_all_product_medias
    from app.services.publisher.eitaa_publisher import _download_telegram_file, _download_url_to_temp
    from app.database.connection import AsyncSessionLocal

    # ۱. پست سفارشی (CUSTOM)
    if product.sku == "CUSTOM" and product.specs and "custom_medias" in product.specs:
        medias = product.specs["custom_medias"]
        if medias:
            m = medias[0]  # اولین مدیای انتخابی
            src = m["file_id"]
            is_video = (m.get("type") == "video")
            
            # 💡 تشخیص دقیق: اگر شامل : باشد آیدی بله است، در غیر این صورت تلگرام
            is_bale_id = (":" in src) and not src.startswith("http")

            if is_bale_id:
                return await _download_bale_file_by_id(src, is_video=is_video)
            elif src.startswith("http"):
                return await _download_url_to_temp(src)
            else:
                return await _download_telegram_file(bot, src)

    # ۲. محصولات دیتابیس
    async with AsyncSessionLocal() as session:
        all_medias = await get_all_product_medias(session, product.id)

    if all_medias:
        first_media = all_medias[0]
        if first_media.platform == Platform.TELEGRAM:
            return await _download_telegram_file(bot, first_media.file_id)
        elif first_media.platform == Platform.BALE:
            return await _download_bale_file_by_id(first_media.file_id)

    if product.image_url and product.image_url.strip():
        return await _download_url_to_temp(product.image_url)

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
    """ارسال پست به کانال بله با پشتیبانی کامل از آلبوم‌های ترکیبی عکس و ویدیو"""
    from app.services.product_media_service import get_product_medias
    from app.database.connection import AsyncSessionLocal
    from app.config import settings
    from telegram import InputMediaPhoto, InputMediaVideo
    import os

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
        log.error(f"[Bale Publish] خطا در ساخت Bot بله: {e}")
        return UnifiedPublishResult(success=False, platform=Platform.BALE, error_message=f"خطا در ساخت Bot بله: {str(e)[:100]}")

    max_len = 1024
    if len(caption) > max_len:
        caption = caption[:max_len - 3] + "..."

    try:
        # ─── ۱. پشتیبانی از پست سفارشی (CUSTOM) ───
        if product.sku == "CUSTOM" and product.specs and "custom_medias" in product.specs:
            custom_medias = product.specs["custom_medias"]
            if custom_medias:
                if len(custom_medias) > 1:
                    media_list = []
                    temp_files_to_cleanup = []
                    
                    try:
                        for i, m in enumerate(custom_medias[:10]):
                            cap = caption if i == 0 else None
                            src = m["file_id"]
                            is_video = (m["type"] == "video")
                            is_bale_id = (":" in src) and not src.startswith("http")

                            if is_bale_id:
                                if is_video: media_list.append(InputMediaVideo(media=src, caption=cap))
                                else: media_list.append(InputMediaPhoto(media=src, caption=cap))
                            else:
                                temp_p = None
                                from app.services.publisher.eitaa_publisher import _download_telegram_file
                                from telegram import Bot
                                tg_temp = Bot(token=settings.BOT_TOKEN)
                                await tg_temp.initialize()
                                try:
                                    temp_p = await _download_telegram_file(tg_temp, src)
                                finally:
                                    await tg_temp.shutdown()

                                if temp_p:
                                    temp_files_to_cleanup.append(temp_p)
                                    fh = open(temp_p, "rb")
                                    if is_video: media_list.append(InputMediaVideo(media=fh, caption=cap))
                                    else: media_list.append(InputMediaPhoto(media=fh, caption=cap))

                        messages = await actual_bot.send_media_group(chat_id=channel.channel_identifier, media=media_list)
                        all_ids = [msg.message_id for msg in messages]
                        return UnifiedPublishResult(success=True, message_id=all_ids[0], message_ids=all_ids, platform=Platform.BALE)
                    
                    except Exception as e:
                        log.error(f"[Bale Publish Custom Album] خطا: {e}", exc_info=True)
                    
                    finally:
                        for tp in temp_files_to_cleanup:
                            if os.path.exists(tp):
                                try: os.remove(tp)
                                except: pass
                else:
                    m = custom_medias[0]
                    src = m["file_id"]
                    is_video = (m["type"] == "video")
                    is_bale_id = (":" in src) and not src.startswith("http")

                    if is_bale_id:
                        try:
                            if is_video: msg = await actual_bot.send_video(chat_id=channel.channel_identifier, video=src, caption=caption)
                            else: msg = await actual_bot.send_photo(chat_id=channel.channel_identifier, photo=src, caption=caption)
                            return UnifiedPublishResult(success=True, message_id=msg.message_id, message_ids=[msg.message_id], platform=Platform.BALE)
                        except Exception as e:
                            log.error(f"[Bale Publish Custom Native Single] خطا: {e}")
                    else:
                        temp_p = None
                        from app.services.publisher.eitaa_publisher import _download_telegram_file
                        from telegram import Bot
                        tg_temp = Bot(token=settings.BOT_TOKEN)
                        await tg_temp.initialize()
                        try:
                            temp_p = await _download_telegram_file(tg_temp, src)
                        finally:
                            await tg_temp.shutdown()

                        if temp_p:
                            try:
                                with open(temp_p, "rb") as f:
                                    if is_video: msg = await actual_bot.send_video(chat_id=channel.channel_identifier, video=f, caption=caption)
                                    else: msg = await actual_bot.send_photo(chat_id=channel.channel_identifier, photo=f, caption=caption)
                                return UnifiedPublishResult(success=True, message_id=msg.message_id, message_ids=[msg.message_id], platform=Platform.BALE)
                            finally:
                                if os.path.exists(temp_p):
                                    try: os.remove(temp_p)
                                    except: pass

        # ─── 2. روال عادی برای محصولات دیتابیس ───
        else:
            async with AsyncSessionLocal() as session:
                bale_medias = await get_product_medias(session, product.id, Platform.BALE)

            if bale_medias:
                if len(bale_medias) == 1:
                    try:
                        message = await actual_bot.send_photo(
                            chat_id=channel.channel_identifier,
                            photo=bale_medias[0].file_id,
                            caption=caption,
                        )
                        return UnifiedPublishResult(success=True, message_id=message.message_id, message_ids=[message.message_id], platform=Platform.BALE)
                    except Exception as e:
                        log.error(f"[Bale Publish] خطا در ارسال عکس نیتیو: {e}")
                else:
                    try:
                        from telegram import InputMediaPhoto
                        media_list = []
                        for i, media in enumerate(bale_medias[:10]):
                            cap = caption if i == 0 else None
                            media_list.append(InputMediaPhoto(media=media.file_id, caption=cap))

                        messages = await actual_bot.send_media_group(chat_id=channel.channel_identifier, media=media_list)
                        all_ids = [msg.message_id for msg in messages]
                        return UnifiedPublishResult(success=True, message_id=all_ids[0], message_ids=all_ids, platform=Platform.BALE)
                    except Exception as e:
                        log.error(f"[Bale Publish] خطا در ارسال آلبوم نیتیو: {e}")

            if not bale_medias:
                async with AsyncSessionLocal() as session:
                    tg_medias = await get_product_medias(session, product.id, Platform.TELEGRAM)

                if tg_medias:
                    temp_files = []
                    try:
                        from app.services.publisher.eitaa_publisher import _download_telegram_file
                        from telegram import Bot
                        tg_bot = Bot(token=settings.BOT_TOKEN)
                        await tg_bot.initialize()

                        try:
                            for media in tg_medias[:10]:
                                temp_path = await _download_telegram_file(tg_bot, media.file_id)
                                if temp_path:
                                    temp_files.append(temp_path)
                        finally:
                            await tg_bot.shutdown()

                        if len(temp_files) == 1:
                            with open(temp_files[0], "rb") as f:
                                message = await actual_bot.send_photo(chat_id=channel.channel_identifier, photo=f, caption=caption)
                            return UnifiedPublishResult(success=True, message_id=message.message_id, message_ids=[message.message_id], platform=Platform.BALE)
                        
                        elif len(temp_files) > 1:
                            from telegram import InputMediaPhoto
                            media_list = []
                            file_handles = []

                            for i, path in enumerate(temp_files):
                                fh = open(path, "rb")
                                file_handles.append(fh)
                                cap = caption if i == 0 else None
                                media_list.append(InputMediaPhoto(media=fh, caption=cap))

                            try:
                                messages = await actual_bot.send_media_group(chat_id=channel.channel_identifier, media=media_list)
                                all_ids = [msg.message_id for msg in messages]
                                return UnifiedPublishResult(success=True, message_id=all_ids[0], message_ids=all_ids, platform=Platform.BALE)
                            finally:
                                for fh in file_handles:
                                    fh.close()
                    except Exception as e:
                        log.error(f"[Bale Publish] خطا در انتقال عکس تلگرام: {e}")
                    finally:
                        for path in temp_files:
                            if os.path.exists(path):
                                try: os.remove(path)
                                except: pass

                if product.image_url and product.image_url.strip():
                    try:
                        message = await actual_bot.send_photo(chat_id=channel.channel_identifier, photo=product.image_url.strip(), caption=caption)
                        return UnifiedPublishResult(success=True, message_id=message.message_id, message_ids=[message.message_id], platform=Platform.BALE)
                    except Exception as e:
                        log.warning(f"[Bale Publish] URL fail: {e}")

        # ─── ۳. Fallback نهایی: ارسال متنی ───
        try:
            message = await actual_bot.send_message(chat_id=channel.channel_identifier, text=caption)
            return UnifiedPublishResult(success=True, message_id=message.message_id, message_ids=[message.message_id], platform=Platform.BALE, used_fallback=True)
        except Exception as e:
            return UnifiedPublishResult(success=False, platform=Platform.BALE, error_message=str(e)[:100])

    finally:
        if is_temp_bot and actual_bot:
            try: await actual_bot.shutdown()
            except Exception: pass


async def _edit_bale_post(
    bot,
    channel: Channel,
    product: Product,
    new_caption: str,
    old_message_id: int,
) -> UnifiedPublishResult:
    """
    ویرایش پست بله با هندل کردن تمامی حالت‌های edge case:
    1. پست قبلی text-only بود، الان عکس داره → نمیشه edit زد، باید delete+repost
    2. پست قبلی عکس داشت، الان عکس نداره → edit_message_caption با خطا مواجه میشه
    3. هر دو text-only → edit_message_text
    4. هر دو عکس دارن → edit_message_caption
    """
    from app.config import settings
    from app.services.product_media_service import get_product_medias
    from app.database.connection import AsyncSessionLocal
    from app.database.models import PostedMessage

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
            
            # بررسی وضعیت پست قبلی: آیا text-only بود؟
            posted_res = await session.execute(
                select(PostedMessage).where(
                    PostedMessage.product_id == product.id,
                    PostedMessage.channel_id == channel.id
                )
            )
            posted_rec = posted_res.scalar_one_or_none()

        has_photo_now = len(medias) > 0 or bool(product.image_url)
        
        # 🔍 تشخیص هوشمند: آیا پست قبلی text-only بود؟
        # نکته مهم: برای پست‌های قدیمی که last_media_hash ندارند، فرض می‌کنیم عکس داشتند
        # چون اکثر محصولات عکس دارند و این امن‌تر است (edit_caption امتحان می‌شود)
        was_text_only = False
        if posted_rec and posted_rec.last_media_hash is not None:
            # اگر media_hash خالی باشد (رشته خالی) → text-only بوده
            was_text_only = (posted_rec.last_media_hash == "")
        # اگر last_media_hash اصلاً نداریم (NULL) → فرض می‌کنیم عکس داشته
        
        # ⚠️ Edge Case: پست قبلی text-only بود ولی الان عکس داره
        # → نمیشه edit زد، باید caller delete+repost کنه
        if was_text_only and has_photo_now:
            log.warning(
                f"[Bale Edit] پست قبلی text-only بود ولی الان عکس داره؛ "
                f"نیاز به delete+repost"
            )
            return UnifiedPublishResult(
                success=False,
                platform=Platform.BALE,
                error_message="[BALE_NEEDS_REPOST] پست قبلی text-only بود، نیاز به repost",
            )

        try:
            if has_photo_now:
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
            log.error(f"[Bale Edit] خطا در ویرایش: {e}")
            
            if "message is not modified" in error_msg:
                return UnifiedPublishResult(
                    success=True,
                    message_id=old_message_id,
                    platform=Platform.BALE,
                )
            
            # 💡 اگه caption ندارد، یعنی text-only بوده، تلاش مجدد با edit_text
            if "no caption" in error_msg or "message has no caption" in error_msg:
                log.warning("[Bale Edit] پست بدون caption، تلاش مجدد با edit_text...")
                try:
                    await actual_bot.edit_message_text(
                        chat_id=channel.channel_identifier,
                        message_id=old_message_id,
                        text=new_caption,
                    )
                    return UnifiedPublishResult(
                        success=True,
                        message_id=old_message_id,
                        platform=Platform.BALE,
                    )
                except Exception as retry_e:
                    log.error(f"[Bale Edit] تلاش مجدد با edit_text هم ناموفق: {retry_e}")

            if "permission_denied" in error_msg or "forbidden" in error_msg:
                try:
                    bot_member = await actual_bot.get_chat_member(
                        chat_id=channel.channel_identifier,
                        user_id=actual_bot.id,
                    )
                    bot_status = getattr(bot_member, "status", "unknown")
                    can_edit = getattr(bot_member, "can_edit_messages", None)
                    can_post = getattr(bot_member, "can_post_messages", None)
                    log.error(
                        f"[Bale Edit] permission diagnostic: "
                        f"chat={channel.channel_identifier} bot_id={actual_bot.id} "
                        f"status={bot_status} "
                        f"can_edit={can_edit if can_edit is not None else 'unknown'} "
                        f"can_post={can_post if can_post is not None else 'unknown'} "
                        f"old_message_id={old_message_id}"
                    )

                    if (
                        bot_status == "creator"
                        or (
                            bot_status == "administrator"
                            and can_post is True
                            and can_edit is True
                        )
                    ):
                        return UnifiedPublishResult(
                            success=False,
                            platform=Platform.BALE,
                            error_message=(
                                "[BALE_MISSING_MESSAGE] پیام قبلی پیدا نشد؛ "
                                "ارسال مجدد انجام می‌شود."
                            ),
                        )
                except Exception as diagnostic_error:
                    log.error(
                        f"[Bale Edit] permission diagnostic failed: "
                        f"chat={channel.channel_identifier} "
                        f"old_message_id={old_message_id} error={diagnostic_error}"
                    )

                return UnifiedPublishResult(
                    success=False,
                    platform=Platform.BALE,
                    error_message=(
                        "بات بله مجوز ویرایش این پیام را ندارد؛ "
                        "ادمین بودن بات و متعلق بودن پیام به همین بات را بررسی کنید. "
                        f"({str(e)[:100]})"
                    ),
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

async def _download_bale_file_by_id(file_id: str, is_video: bool = False) -> Path | None:
    """دانلود فایل از بله با تنظیم پسوند صحیح (.jpg یا .mp4)"""
    import tempfile
    import httpx
    from app.config import settings

    if not settings.BALE_BOT_TOKEN or not file_id:
        return None

    suffix = ".mp4" if is_video else ".jpg"

    try:
        async with httpx.AsyncClient(timeout=35) as client:
            file_url = f"{settings.BALE_API_BASE}{settings.BALE_BOT_TOKEN}/getFile"
            response = await client.post(file_url, json={"file_id": file_id})

            if response.status_code == 200 and response.json().get("ok"):
                file_path = response.json().get("result", {}).get("file_path", "")
                download_url = f"{settings.BALE_FILE_API_BASE}{settings.BALE_BOT_TOKEN}/{file_path}"
            else:
                download_url = f"{settings.BALE_FILE_API_BASE}{settings.BALE_BOT_TOKEN}/{file_id}"

            file_response = await client.get(download_url)
            if file_response.status_code == 200 and len(file_response.content) > 100:
                temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False, mode="wb")
                temp_file.write(file_response.content)
                temp_file.close()
                return Path(temp_file.name)
    except Exception as e:
        log.error(f"[Bale Download By ID] خطا در دانلود {file_id}: {e}")
    return None

async def publish_to_channels_parallel(
    bot,
    channels: list[Channel],
    product: Product,
    caption: str,
    eitaa_token: str | None = None,
) -> list[UnifiedPublishResult]:
    """
    ارسال موازی و همزمان پست به چندین کانال (Parallel Publishing).
    سرعت ارسال را از ۱۵ ثانیه به ۳ الی ۵ ثانیه کاهش می‌دهد.
    """
    import asyncio
    
    log.info(f"🚀 [Parallel Publish] شروع ارسال همزمان برای محصول {product.sku} به {len(channels)} کانال.")

    # 1. آماده‌سازی لیست تسک‌ها (Tasks)
    tasks = []
    for channel in channels:
        # پر کردن {contact_id} برای هر کانال
        channel_caption = _fill_phone_placeholder(
            _fill_contact_id_placeholder(caption, channel), channel
        )
        
        # برای هر کانال یک تسک مستقل (Coroutine) ایجاد می‌کنیم
        task = publish_to_channel(
            bot=bot,
            channel=channel,
            product=product,
            caption=channel_caption,
            eitaa_token=eitaa_token,
        )
        tasks.append(task)

    # 2. شلیک همزمان تمامی تسک‌ها
    # return_exceptions=True باعث می‌شود اگر یک تسک کاملاً کرش کرد، بقیه متوقف نشوند
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 3. پردازش خروجی‌ها و هندل کردن خطاهای بحرانی سیستم
    final_results = []
    for idx, res in enumerate(results):
        channel = channels[idx]
        if isinstance(res, Exception):
            log.error(f"❌ [Parallel Publish] خطای بحرانی در ارسال به {channel.platform.value}: {res}")
            # ایجاد یک خروجی استاندارد ناموفق برای جلوگیری از شکست زنجیره
            final_results.append(
                UnifiedPublishResult(
                    success=False,
                    platform=channel.platform,
                    error_message=f"خطای بحرانی سیستمی: {str(res)[:100]}"
                )
            )
        else:
            final_results.append(res)

    log.info(f"🏁 [Parallel Publish] ارسال همزمان پایان یافت.")
    return final_results