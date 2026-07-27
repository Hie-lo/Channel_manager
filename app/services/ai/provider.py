"""
اتصال به OpenRouter API
"""

from dataclasses import dataclass
import httpx

from app.config import settings
from app.utils.logger import log


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_TIMEOUT = 30.0


@dataclass
class AIResponse:
    """نتیجه فراخوانی AI"""
    success: bool
    content: str = ""
    error_message: str = ""
    tokens_used: int = 0


async def call_ai(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 200,
    temperature: float = 0.5,
) -> AIResponse:
    """
    ارسال درخواست به OpenRouter و دریافت پاسخ
    """
    if not settings.AI_API_KEY:
        return AIResponse(
            success=False,
            error_message="API Key تنظیم نشده",
        )

    headers = {
        "Authorization": f"Bearer {settings.AI_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://channel-manager-bot.local",  # برای رنکینگ در OpenRouter
        "X-Title": "Channel Manager Bot",
    }

    payload = {
        "model": settings.AI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
            )

            if response.status_code != 200:
                error_body = response.text[:300]
                log.error(
                    f"AI API خطا: status={response.status_code}, "
                    f"body={error_body}"
                )
                return AIResponse(
                    success=False,
                    error_message=_translate_api_error(response.status_code, error_body),
                )

            data = response.json()

            # استخراج محتوا
            content = ""
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0].get("message", {}).get("content", "")

            if not content:
                return AIResponse(
                    success=False,
                    error_message="پاسخ خالی از AI دریافت شد",
                )

            # استخراج مصرف توکن (اگر موجود)
            tokens_used = 0
            if "usage" in data:
                tokens_used = data["usage"].get("total_tokens", 0)

            log.info(
                f"✅ AI پاسخ داد: model={settings.AI_MODEL}, "
                f"tokens={tokens_used}, length={len(content)}"
            )

            return AIResponse(
                success=True,
                content=content.strip(),
                tokens_used=tokens_used,
            )

    except httpx.TimeoutException:
        log.error("Timeout در فراخوانی AI")
        return AIResponse(
            success=False,
            error_message="AI پاسخ نداد (timeout)",
        )
    except Exception as e:
        log.error(f"خطای غیرمنتظره در AI: {e}", exc_info=True)
        return AIResponse(
            success=False,
            error_message=f"خطای غیرمنتظره: {str(e)[:100]}",
        )


def _translate_api_error(status_code: int, body: str) -> str:
    """ترجمه خطاهای API"""
    if status_code == 401:
        return "کلید API نامعتبر است"
    if status_code == 402:
        return "اعتبار OpenRouter تمام شده"
    if status_code == 429:
        return "محدودیت درخواست - چند لحظه صبر کنید"
    if status_code == 500:
        return "خطای سرور OpenRouter"
    if status_code == 503:
        return "سرویس در دسترس نیست"

    body_lower = body.lower()
    if "insufficient" in body_lower or "credit" in body_lower:
        return "اعتبار کافی نیست"
    if "rate" in body_lower and "limit" in body_lower:
        return "محدودیت درخواست"

    return f"خطای API (کد {status_code})"