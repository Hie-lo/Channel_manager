"""
کلاینت سطح پایین برای ارتباط با Eitaayar API
مسئولیت: فقط HTTP requests
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.config import settings
from app.utils.logger import log


@dataclass
class EitaaResponse:
    """پاسخ استاندارد از API ایتا"""
    ok: bool
    message_id: int | None = None
    error_code: int | None = None
    error_message: str = ""
    raw_data: dict | None = None


class EitaaClient:
    """
    کلاینت HTTP برای ایتایار

    استفاده:
        client = EitaaClient(token="bot123:xyz")
        result = await client.send_message(chat_id="12345", text="سلام")
    """

    def __init__(self, token: str):
        if not token:
            raise ValueError("توکن ایتا نمی‌تواند خالی باشد")
        self.token = token
        self.base_url = settings.EITAA_API_BASE.rstrip("/")
        self.timeout = settings.EITAA_TIMEOUT

    def _build_url(self, method: str) -> str:
        """ساخت URL کامل برای یک متد"""
        return f"{self.base_url}/{self.token}/{method}"

    async def _make_request(
        self,
        method: str,
        data: dict | None = None,
        files: dict | None = None,
    ) -> EitaaResponse:
        """
        درخواست HTTP به API با retry logic

        Args:
            method: نام endpoint (مثل sendMessage)
            data: دیتا برای form
            files: فایل‌ها برای multipart

        Returns:
            EitaaResponse
        """
        url = self._build_url(method)

        for attempt in range(1, settings.EITAA_MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(
                    verify=False,   # ایتایار SSL درست ندارد
                    timeout=self.timeout,
                ) as client:
                    response = await client.post(url, data=data, files=files)

                    return self._parse_response(response, method)

            except httpx.TimeoutException:
                log.warning(
                    f"[Eitaa] Timeout در {method} (تلاش {attempt}/{settings.EITAA_MAX_RETRIES})"
                )
                if attempt < settings.EITAA_MAX_RETRIES:
                    await asyncio.sleep(2 ** attempt)  # exponential backoff
                    continue
                return EitaaResponse(
                    ok=False,
                    error_message="Timeout در اتصال به ایتایار",
                )

            except httpx.NetworkError as e:
                log.warning(
                    f"[Eitaa] خطای شبکه در {method}: {e} (تلاش {attempt})"
                )
                if attempt < settings.EITAA_MAX_RETRIES:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return EitaaResponse(
                    ok=False,
                    error_message=f"خطای شبکه: {str(e)[:100]}",
                )

            except Exception as e:
                log.error(
                    f"[Eitaa] خطای غیرمنتظره در {method}: {e}",
                    exc_info=True,
                )
                return EitaaResponse(
                    ok=False,
                    error_message=f"خطای غیرمنتظره: {str(e)[:100]}",
                )

        return EitaaResponse(ok=False, error_message="تلاش‌ها تمام شد")

    def _parse_response(
        self,
        response: httpx.Response,
        method: str,
    ) -> EitaaResponse:
        """پارس پاسخ HTTP"""
        try:
            data = response.json()
        except Exception as e:
            log.error(f"[Eitaa] پاسخ JSON نبود در {method}: {response.text[:200]}")
            return EitaaResponse(
                ok=False,
                error_message=f"پاسخ نامعتبر (HTTP {response.status_code})",
            )

        # پاسخ ناموفق
        if not data.get("ok"):
            error_code = data.get("error_code", response.status_code)
            error_desc = data.get("description", "خطای نامشخص")
            log.warning(
                f"[Eitaa] {method} ناموفق: code={error_code}, desc={error_desc}"
            )
            return EitaaResponse(
                ok=False,
                error_code=error_code,
                error_message=error_desc,
                raw_data=data,
            )

        # پاسخ موفق
        result = data.get("result", {})
        message_id = None

        if isinstance(result, dict):
            message_id = result.get("message_id")

        return EitaaResponse(
            ok=True,
            message_id=message_id,
            raw_data=data,
        )

    # ═══════════════════════════════════════════
    # متدهای عمومی
    # ═══════════════════════════════════════════

    async def send_message(
        self,
        chat_id: str,
        text: str,
    ) -> EitaaResponse:
        """ارسال پیام متنی"""
        return await self._make_request(
            method="sendMessage",
            data={
                "chat_id": str(chat_id),
                "text": text,
            }
        )

    async def send_file(
        self,
        chat_id: str,
        file_path: str | Path,
        caption: str = "",
    ) -> EitaaResponse:
        """ارسال فایل (عکس/سند) با کپشن"""
        file_path = Path(file_path)
        if not file_path.exists():
            return EitaaResponse(
                ok=False,
                error_message=f"فایل پیدا نشد: {file_path}",
            )

        try:
            with open(file_path, "rb") as f:
                files = {"file": f}
                return await self._make_request(
                    method="sendFile",
                    data={
                        "chat_id": str(chat_id),
                        "caption": caption,
                    },
                    files=files,
                )
        except Exception as e:
            log.error(f"[Eitaa] خطا در باز کردن فایل {file_path}: {e}")
            return EitaaResponse(
                ok=False,
                error_message=f"خطا در باز کردن فایل: {str(e)[:100]}",
            )

    async def delete_message(
        self,
        chat_id: str,
        message_id: int,
    ) -> EitaaResponse:
        """حذف پیام"""
        return await self._make_request(
            method="deleteMessage",
            data={
                "chat_id": str(chat_id),
                "message_id": message_id,
            }
        )