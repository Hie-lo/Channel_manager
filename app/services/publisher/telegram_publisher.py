"""
انتشار پست در کانال تلگرام
"""

from dataclasses import dataclass, field
from telegram import Bot
from telegram.error import TelegramError, BadRequest
from app.utils.validators import is_valid_image_url
from app.utils.logger import log


# محدودیت کپشن تلگرام
MAX_CAPTION_LENGTH = 1024
MAX_TEXT_LENGTH = 4096


@dataclass
class PublishResult:
    """نتیجه انتشار پست"""
    success: bool
    message_id: int | None = None
    message_ids: list[int] = field(default_factory=list)  # ← جدید (برای media group)
    error_message: str = ""
    used_fallback: bool = False


async def publish_post_to_telegram(
    bot: Bot,
    channel_identifier: str,
    caption: str,
    photo_url: str | None = None,
) -> PublishResult:
    """
    انتشار پست در کانال تلگرام
    photo_url می‌تونه URL باشه یا file_id تلگرام
    """
    max_len = MAX_CAPTION_LENGTH if photo_url else MAX_TEXT_LENGTH
    if len(caption) > max_len:
        caption = caption[:max_len - 3] + "..."

    # چک نوع photo_url
    is_url = False
    is_file_id = False

    if photo_url:
        photo_url = photo_url.strip()
        if photo_url.startswith("http://") or photo_url.startswith("https://"):
            is_url = True
        else:
            # هر چیز دیگه‌ای file_id در نظر می‌گیریم
            is_file_id = True

    # اعتبارسنجی URL (فقط اگه URL باشه)
    if is_url:
        is_valid = await is_valid_image_url(photo_url)
        if not is_valid:
            log.warning(f"⚠️ لینک عکس نامعتبر: {photo_url}")
            log.warning(f"⚠️ Fallback به متنی")
            return await _fallback_to_text(bot, channel_identifier, caption)

    # اگه file_id هست، مستقیم استفاده کن (بدون اعتبارسنجی URL)
    if is_file_id:
        log.info(f"📷 استفاده از file_id تلگرام برای {channel_identifier}")

    # تلاش ۱: ارسال با عکس
    if photo_url:
        try:
            message = await bot.send_photo(
                chat_id=channel_identifier,
                photo=photo_url,
                caption=caption,
            )
            log.info(
                f"پست با عکس ارسال شد به {channel_identifier}، "
                f"message_id: {message.message_id}"
            )
            return PublishResult(
                success=True,
                message_id=message.message_id,
                used_fallback=False,
            )

        except (BadRequest, TelegramError) as e:
            error_msg = str(e).lower()

            if _is_photo_error(error_msg):
                log.warning(
                    f"خطا در بارگذاری عکس: {e}. تلاش برای ارسال بدون عکس..."
                )
                return await _fallback_to_text(bot, channel_identifier, caption)
            else:
                log.error(f"خطا در ارسال به {channel_identifier}: {e}")
                return PublishResult(
                    success=False,
                    error_message=_translate_telegram_error(str(e)),
                )

        except Exception as e:
            log.error(f"خطای غیرمنتظره در ارسال با عکس: {e}", exc_info=True)
            return await _fallback_to_text(bot, channel_identifier, caption)

    # تلاش ۲: ارسال متنی مستقیم
    return await _send_text_only(bot, channel_identifier, caption)


async def _fallback_to_text(
    bot: Bot,
    channel_identifier: str,
    caption: str,
) -> PublishResult:
    """ارسال متنی به عنوان fallback"""
    # اگه بیش از حد بود، برای متنی طولانی‌تر مجازه
    if len(caption) > MAX_TEXT_LENGTH:
        caption = caption[:MAX_TEXT_LENGTH - 3] + "..."

    log.warning(f"⚠️ Fallback به ارسال متنی برای کانال {channel_identifier}")

    result = await _send_text_only(bot, channel_identifier, caption)
    if result.success:
        result.used_fallback = True
        log.info(f"✅ Fallback موفق - پیام متنی ارسال شد به {channel_identifier}")
    else:
        log.error(f"❌ Fallback هم fail شد: {result.error_message}")
    return result


async def _send_text_only(
    bot: Bot,
    channel_identifier: str,
    text: str,
) -> PublishResult:
    """ارسال فقط متن"""
    try:
        message = await bot.send_message(
            chat_id=channel_identifier,
            text=text,
        )
        log.info(
            f"پست متنی ارسال شد به {channel_identifier}، "
            f"message_id: {message.message_id}"
        )
        return PublishResult(
            success=True,
            message_id=message.message_id,
        )

    except TelegramError as e:
        log.error(f"خطا در ارسال متنی: {e}")
        return PublishResult(
            success=False,
            error_message=_translate_telegram_error(str(e)),
        )
    except Exception as e:
        log.error(f"خطای غیرمنتظره در ارسال متنی: {e}", exc_info=True)
        return PublishResult(
            success=False,
            error_message=f"خطای غیرمنتظره: {str(e)[:100]}",
        )


async def edit_post_in_telegram(
    bot: Bot,
    channel_identifier: str,
    message_id: int,
    new_caption: str,
    has_photo: bool = True,
) -> PublishResult:
    """
    ویرایش پست قبلی در کانال
    """
    max_len = MAX_CAPTION_LENGTH if has_photo else MAX_TEXT_LENGTH
    if len(new_caption) > max_len:
        new_caption = new_caption[:max_len - 3] + "..."

    try:
        if has_photo:
            await bot.edit_message_caption(
                chat_id=channel_identifier,
                message_id=message_id,
                caption=new_caption,
            )
        else:
            await bot.edit_message_text(
                chat_id=channel_identifier,
                message_id=message_id,
                text=new_caption,
            )

        log.info(f"پست ویرایش شد: {channel_identifier}, msg_id={message_id}")

        return PublishResult(
            success=True,
            message_id=message_id,
        )

    except BadRequest as e:
        error_msg = str(e).lower()
        # اگه متن جدید با قبلی یکی بود، این "موفق" حساب کن
        if "message is not modified" in error_msg:
            return PublishResult(
                success=True,
                message_id=message_id,
            )
        log.error(f"خطا در ویرایش پست: {e}")
        return PublishResult(
            success=False,
            error_message=_translate_telegram_error(str(e)),
        )

    except TelegramError as e:
        log.error(f"خطا در ویرایش پست: {e}")
        return PublishResult(
            success=False,
            error_message=_translate_telegram_error(str(e)),
        )


def _is_photo_error(error_msg: str) -> bool:
    """چک کن خطا مربوط به عکس هست"""
    photo_error_signals = [
        "wrong type of the web page content",
        "wrong file identifier",
        "webpage_media_empty",
        "photo_invalid_dimensions",
        "wrong file",
        "failed to get http url content",
        "image_process_failed",
        "media_empty",
    ]
    return any(signal in error_msg for signal in photo_error_signals)


def _translate_telegram_error(error_msg: str) -> str:
    """ترجمه خطاهای رایج تلگرام به فارسی"""
    error_lower = error_msg.lower()

    if "chat not found" in error_lower:
        return "کانال پیدا نشد"
    if "bot was blocked" in error_lower:
        return "ربات بلاک شده"
    if "not enough rights" in error_lower or "forbidden" in error_lower:
        return "ربات دسترسی ارسال پیام ندارد"
    if _is_photo_error(error_lower):
        return "لینک عکس نامعتبر است"
    if "message is not modified" in error_lower:
        return "متن جدید با قبلی یکی است"
    if "flood" in error_lower:
        return "محدودیت ارسال - چند لحظه صبر کنید"
    if "message to edit not found" in error_lower:
        return "پست قابل ویرایش پیدا نشد"

    return f"خطا: {error_msg[:100]}"

async def publish_media_group_to_telegram(
    bot: Bot,
    channel_identifier: str,
    caption: str,
    photo_sources: list[str],
) -> PublishResult:
    """
    ارسال چند عکس به صورت آلبوم (media group)
    photo_sources: لیست file_id ها یا URL ها
    """
    from telegram import InputMediaPhoto

    if not photo_sources:
        return await _send_text_only(bot, channel_identifier, caption)

    # اگه فقط یه عکس بود، از تابع تک‌عکس استفاده کن
    if len(photo_sources) == 1:
        return await publish_post_to_telegram(
            bot=bot,
            channel_identifier=channel_identifier,
            caption=caption,
            photo_url=photo_sources[0],
        )

    # کوتاه کردن کپشن
    if len(caption) > MAX_CAPTION_LENGTH:
        caption = caption[:MAX_CAPTION_LENGTH - 3] + "..."

    # ساخت InputMediaPhoto لیست
    # کپشن فقط روی اولی
    media_list = []
    for i, source in enumerate(photo_sources[:10]):  # حداکثر ۱۰ عکس
        if i == 0:
            media_list.append(InputMediaPhoto(media=source, caption=caption))
        else:
            media_list.append(InputMediaPhoto(media=source))

    try:
        messages = await bot.send_media_group(
            chat_id=channel_identifier,
            media=media_list,
        )

        message_ids = [msg.message_id for msg in messages]
        log.info(
            f"آلبوم با {len(messages)} عکس ارسال شد به {channel_identifier}"
        )

        return PublishResult(
            success=True,
            message_id=message_ids[0],
            message_ids=message_ids,  # ← همه ID ها
            used_fallback=False,
        )
    except (BadRequest, TelegramError) as e:
        error_msg = str(e).lower()
        log.error(f"خطا در ارسال آلبوم: {e}")

        if _is_photo_error(error_msg):
            log.warning("Fallback به متنی")
            return await _fallback_to_text(bot, channel_identifier, caption)

        return PublishResult(
            success=False,
            error_message=_translate_telegram_error(str(e)),
        )
    except Exception as e:
        log.error(f"خطای غیرمنتظره در آلبوم: {e}", exc_info=True)
        return await _fallback_to_text(bot, channel_identifier, caption)