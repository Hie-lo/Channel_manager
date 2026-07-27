"""
سرویس اصلی AI - هماهنگ‌کننده کل فرآیند
"""

from dataclasses import dataclass

from app.database.models import Product
from app.business.config import BusinessConfig
from app.services.ai.provider import call_ai
from app.services.ai.prompt_builder import (
    SYSTEM_PROMPT,
    build_generation_prompt,
    build_improve_prompt,
)
from app.services.ai.formatter import parse_ai_response, AIDescription
from app.utils.logger import log


@dataclass
class AIGenerationResult:
    """نتیجه تولید توضیحات AI"""
    success: bool
    description: AIDescription = None
    formatted_text: str = ""
    raw_response: str = ""
    error_message: str = ""
    tokens_used: int = 0

    def __post_init__(self):
        if self.description is None:
            self.description = AIDescription()


async def generate_product_description(
    product: Product,
    business_config: BusinessConfig,
    mode: str = "auto",  # "auto" | "new" | "improve"
) -> AIGenerationResult:
    """
    تولید یا بهبود توضیحات محصول با AI

    mode:
        auto: اگه توضیح دستی بود، improve؛ وگرنه new
        new: تولید از صفر
        improve: بهبود متن موجود
    """
    # تعیین mode
    existing_desc = product.description_manual or ""

    if mode == "auto":
        if existing_desc.strip():
            actual_mode = "improve"
        else:
            actual_mode = "new"
    else:
        actual_mode = mode

    # ساخت پرامپت
    if actual_mode == "improve" and existing_desc.strip():
        user_prompt = build_improve_prompt(product, business_config, existing_desc)
        log.info(f"🤖 [AI] بهبود توضیحات برای {product.sku}")
    else:
        user_prompt = build_generation_prompt(product, business_config)
        log.info(f"🤖 [AI] تولید توضیحات جدید برای {product.sku}")

    # فراخوانی AI
    ai_response = await call_ai(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=200,
        temperature=0.5,
    )

    if not ai_response.success:
        return AIGenerationResult(
            success=False,
            error_message=ai_response.error_message,
        )

    # پارس خروجی
    description = parse_ai_response(ai_response.content)

    if not description.is_valid:
        log.warning(
            f"AI response قابل پارس نبود: {ai_response.content[:200]}"
        )
        return AIGenerationResult(
            success=False,
            error_message="پاسخ AI قابل پردازش نیست",
            raw_response=ai_response.content,
        )

    formatted = description.format_for_post()

    return AIGenerationResult(
        success=True,
        description=description,
        formatted_text=formatted,
        raw_response=ai_response.content,
        tokens_used=ai_response.tokens_used,
    )