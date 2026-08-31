"""
اتصال به OpenRouter API
"""

from dataclasses import dataclass
import httpx
import asyncio
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
    max_tokens: int = 500,
    temperature: float = 0.6,
) -> AIResponse:
    """ارسال درخواست به OpenRouter با سیستم Retry هوشمند"""
    
    if not settings.AI_API_KEY:
        return AIResponse(success=False, error_message="API Key تنظیم نشده")

    headers = {
        "Authorization": f"Bearer {settings.AI_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://channel-manager-bot.local",
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
    log.info(f"🤖 استفاده از مدل: {settings.AI_MODEL}")
    max_retries = 3
    last_error_msg = ""

    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.post(OPENROUTER_URL, headers=headers, json=payload)
                
                if response.status_code != 200:
                    error_body = response.text[:300]
                    last_error_msg = _translate_api_error(response.status_code, error_body)
                    log.warning(f"⚠️ [AI Attempt {attempt}] API Error: {response.status_code}")
                    
                    if attempt == max_retries:
                        return AIResponse(success=False, error_message=last_error_msg)
                    
                    await asyncio.sleep(6) # وقفه ۲ ثانیه‌ای قبل از تلاش مجدد
                    continue

                data = response.json()
                content = ""
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0].get("message", {}).get("content", "")

                if not content:
                    last_error_msg = "پاسخ خالی از سرور هوش مصنوعی"
                    if attempt == max_retries:
                        return AIResponse(success=False, error_message=last_error_msg)
                    await asyncio.sleep(6)
                    continue

                tokens_used = data.get("usage", {}).get("total_tokens", 0)
                log.info(f"✅ AI پاسخ داد (تلاش {attempt}): tokens={tokens_used}")
                
                return AIResponse(success=True, content=content.strip(), tokens_used=tokens_used)

        except (httpx.TimeoutException, httpx.NetworkError) as e:
            last_error_msg = f"مشکل ارتباط با سرور AI (تلاش {attempt})"
            log.warning(f"⚠️ [AI Attempt {attempt}] Network/Timeout Error: {e}")
            if attempt == max_retries:
                return AIResponse(success=False, error_message="هوش مصنوعی در حال حاضر پاسخگو نیست. لطفاً بعداً تلاش کنید.")
            await asyncio.sleep(6)
            
        except Exception as e:
            log.error(f"خطای غیرمنتظره در AI: {e}", exc_info=True)
            return AIResponse(success=False, error_message=f"خطای سیستمی: {str(e)[:100]}")

    return AIResponse(success=False, error_message=last_error_msg)


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