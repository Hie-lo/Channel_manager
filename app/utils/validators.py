"""
اعتبارسنجی‌های عمومی
"""

import httpx
from app.utils.logger import log


async def is_valid_image_url(url: str, timeout: float = 5.0) -> bool:
    """
    چک کن URL به یک عکس معتبر اشاره می‌کنه یا نه
    با درخواست HEAD چک می‌کنه Content-Type
    """
    if not url or not url.strip():
        return False

    url = url.strip()

    if not (url.startswith("http://") or url.startswith("https://")):
        return False

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.head(url)

            # اگه HEAD کار نکرد، GET رو امتحان کن
            if response.status_code >= 400:
                response = await client.get(url)

            if response.status_code >= 400:
                log.warning(f"URL عکس در دسترس نیست ({response.status_code}): {url}")
                return False

            content_type = response.headers.get("content-type", "").lower()

            if not content_type.startswith("image/"):
                log.warning(
                    f"URL عکس نیست، content-type: {content_type}, url: {url}"
                )
                return False

            return True

    except httpx.TimeoutException:
        log.warning(f"Timeout در بررسی URL عکس: {url}")
        return False
    except Exception as e:
        log.warning(f"خطا در بررسی URL عکس {url}: {e}")
        return False