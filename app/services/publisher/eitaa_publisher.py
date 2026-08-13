"""
Publisher برای ایتا با استراتژی delete-and-repost
چون ایتا editMessage رو پشتیبانی نمی‌کنه
"""

import asyncio
import tempfile
import os
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from app.services.publisher.eitaa_client import EitaaClient, EitaaResponse
from app.utils.logger import log


# محدودیت کپشن ایتا (احتیاطاً)
MAX_CAPTION_LENGTH = 1000


@dataclass
class EitaaPublishResult:
    """نتیجه انتشار در ایتا"""
    success: bool
    message_id: int | None = None
    error_message: str = ""
    used_fallback: bool = False


async def _download_url_to_temp(url: str, timeout: int = 30) -> Path | None:
    """
    دانلود URL به فایل موقت
    برای وقتی که product.image_url داریم و باید در ایتا آپلود کنیم
    """
    if not url or not url.strip():
        return None

    url = url.strip()
    if not url.startswith(("http://", "https://")):
        return None

    try:
        async with httpx.AsyncClient(
            verify=False,
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            response = await client.get(url)

            if response.status_code >= 400:
                log.warning(f"[Eitaa] URL دانلود نشد ({response.status_code}): {url}")
                return None

            # چک نوع فایل
            content_type = response.headers.get("content-type", "").lower()
            if not content_type.startswith("image/"):
                log.warning(f"[Eitaa] URL عکس نیست: {content_type}")
                return None

            # ذخیره در temp
            suffix = ".jpg"
            if "png" in content_type:
                suffix = ".png"

            temp_file = tempfile.NamedTemporaryFile(
                suffix=suffix, delete=False, mode="wb"
            )
            temp_file.write(response.content)
            temp_file.close()

            return Path(temp_file.name)

    except Exception as e:
        log.error(f"[Eitaa] خطا در دانلود URL {url}: {e}")
        return None


async def _download_telegram_file(
    bot,
    file_id: str,
) -> Path | None:
    """
    دانلود فایل تلگرام به فایل موقت
    برای وقتی که file_id تلگرام داریم و باید در ایتا آپلود کنیم
    """
    try:
        tg_file = await bot.get_file(file_id)

        suffix = ".jpg"  # اکثر عکس‌های تلگرام jpg هستن
        temp_file = tempfile.NamedTemporaryFile(
            suffix=suffix, delete=False, mode="wb"
        )
        temp_path = Path(temp_file.name)
        temp_file.close()

        await tg_file.download_to_drive(str(temp_path))
        return temp_path

    except Exception as e:
        log.error(f"[Eitaa] خطا در دانلود فایل تلگرام {file_id[:30]}...: {e}")
        return None


def _cleanup_temp_file(path: Path | None) -> None:
    """پاک کردن فایل موقت"""
    if path and path.exists():
        try:
            os.unlink(path)
        except Exception as e:
            log.warning(f"[Eitaa] خطا در پاک کردن {path}: {e}")


async def publish_post_to_eitaa(
    eitaa_token: str,
    chat_id: str,
    caption: str,
    photo_local_path: Path | None = None,
    photo_url: str | None = None,
) -> EitaaPublishResult:
    """
    ارسال پست به کانال ایتا

    Args:
        eitaa_token: توکن ربات ایتا
        chat_id: آیدی کانال ایتا (عددی)
        caption: متن پست
        photo_local_path: مسیر عکس روی سیستم (اگه داریم)
        photo_url: URL عکس (اگه فقط URL داریم)

    اولویت: photo_local_path > photo_url > بدون عکس

    Returns:
        EitaaPublishResult
    """
    client = EitaaClient(token=eitaa_token)

    # کوتاه کردن کپشن
    if len(caption) > MAX_CAPTION_LENGTH:
        caption = caption[:MAX_CAPTION_LENGTH - 3] + "..."

    # ─── حالت ۱: فایل محلی داریم ───
    if photo_local_path and photo_local_path.exists():
        log.info(f"[Eitaa] ارسال فایل محلی به chat={chat_id}")
        result = await client.send_file(
            chat_id=chat_id,
            file_path=photo_local_path,
            caption=caption,
        )

        if result.ok and result.message_id:
            return EitaaPublishResult(
                success=True,
                message_id=result.message_id,
            )

        # اگه فایل fail شد، متنی fallback
        log.warning(f"[Eitaa] ارسال فایل fail شد: {result.error_message}")

    # ─── حالت ۲: URL داریم، دانلود کن ───
    elif photo_url:
        log.info(f"[Eitaa] دانلود URL و ارسال به chat={chat_id}")
        temp_path = await _download_url_to_temp(photo_url)

        if temp_path:
            try:
                result = await client.send_file(
                    chat_id=chat_id,
                    file_path=temp_path,
                    caption=caption,
                )

                if result.ok and result.message_id:
                    return EitaaPublishResult(
                        success=True,
                        message_id=result.message_id,
                    )
                log.warning(f"[Eitaa] ارسال URL fail شد: {result.error_message}")
            finally:
                _cleanup_temp_file(temp_path)
        else:
            log.warning(f"[Eitaa] دانلود URL fail شد: {photo_url}")

    # ─── حالت ۳ (fallback): ارسال متنی ───
    log.info(f"[Eitaa] Fallback به ارسال متنی برای chat={chat_id}")
    result = await client.send_message(chat_id=chat_id, text=caption)

    if result.ok and result.message_id:
        return EitaaPublishResult(
            success=True,
            message_id=result.message_id,
            used_fallback=True,
        )

    return EitaaPublishResult(
        success=False,
        error_message=result.error_message or "خطای نامشخص",
    )


async def edit_post_in_eitaa(
    eitaa_token: str,
    chat_id: str,
    old_message_id: int,
    new_caption: str,
    photo_local_path: Path | None = None,
    photo_url: str | None = None,
) -> EitaaPublishResult:
    """
    "ادیت" پست ایتا با استراتژی delete-and-repost
    چون ایتا editMessage رو پشتیبانی نمی‌کنه

    مراحل:
    1. حذف پست قدیمی
    2. ارسال پست جدید
    3. برگرداندن message_id جدید

    Returns:
        EitaaPublishResult (با message_id جدید)
    """
    client = EitaaClient(token=eitaa_token)

    # ─── مرحله ۱: حذف پست قدیمی ───
    log.info(f"[Eitaa] حذف پست قدیمی {old_message_id} در chat={chat_id}")
    delete_result = await client.delete_message(
        chat_id=chat_id,
        message_id=old_message_id,
    )

    if not delete_result.ok:
        log.warning(
            f"[Eitaa] حذف پست قدیمی fail شد: {delete_result.error_message}"
        )
        # ادامه می‌دیم چون شاید پست قبلاً حذف شده
    else:
        log.info(f"[Eitaa] پست قدیمی حذف شد")

    # کمی تاخیر برای consistency در ایتا
    await asyncio.sleep(1)

    # ─── مرحله ۲: ارسال پست جدید ───
    log.info(f"[Eitaa] ارسال پست جدید در chat={chat_id}")
    return await publish_post_to_eitaa(
        eitaa_token=eitaa_token,
        chat_id=chat_id,
        caption=new_caption,
        photo_local_path=photo_local_path,
        photo_url=photo_url,
    )