"""
سرویس اصلی AI - هماهنگ‌کننده کل فرآیند
"""

from dataclasses import dataclass

from app.database.models import Product
from app.business.config import BusinessConfig
from app.services.ai.provider import call_ai
from app.services.ai.prompt_builder import (
    get_system_prompt,
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
    existing_desc = product.description_custom or ""

    if mode == "auto":
        actual_mode = "improve" if existing_desc.strip() else "new"
    else:
        actual_mode = mode

    if actual_mode == "improve" and existing_desc.strip():
        user_prompt = build_improve_prompt(product, business_config, existing_desc)
        log.info(f"🤖 [AI] بهبود توضیحات برای {product.sku}")
    else:
        user_prompt = build_generation_prompt(product, business_config)
        log.info(f"🤖 [AI] تولید توضیحات جدید برای {product.sku}")

    ai_response = await call_ai(
        system_prompt=get_system_prompt(business_config.key),
        user_prompt=user_prompt,
        max_tokens=450,
        temperature=0.6,
    )

    if not ai_response.success:
        try:
            from app.config import settings
            from telegram import Bot
            admin_bot = Bot(token=settings.BOT_TOKEN)
            await admin_bot.send_message(
                chat_id=settings.ADMIN_CHAT_ID,
                text=(
                    f"🚨 <b>هشدار خرابی سیستم AI</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"هوش مصنوعی پس از ۳ بار تلاش پاسخ نداد!\n"
                    f"محصول: {product.sku}\n"
                    f"خطا: {ai_response.error_message}\n"
                    f"━━━━━━━━━━━━━━━"
                ),
                parse_mode="HTML"
            )
        except Exception as e:
            log.error(f"خطا در ارسال هشدار خرابی AI به ادمین: {e}")

        return AIGenerationResult(success=False, error_message=ai_response.error_message)

    # پارس خروجی — با توجه به نوع کسب‌وکار (F1-F12 یا P1-P5)
    description = parse_ai_response(ai_response.content, business_key=business_config.key)

    # شروع توضیح با متن فارسی باعث می‌شود نمایش آن در پیام راست‌چین پایدار بماند.
    if description.description:
        description.description = description.description.strip()
        if not description.description.startswith("لپتاپ"):
            description.description = f"لپتاپ {description.description}"

    if not description.is_valid:
        log.warning(f"AI response قابل پارس نبود: {ai_response.content[:200]}")
        return AIGenerationResult(
            success=False,
            error_message="پاسخ AI قابل پردازش نیست",
            raw_response=ai_response.content,
        )

    return AIGenerationResult(
        success=True,
        description=description,
        formatted_text=description.format_for_post(),
        raw_response=ai_response.content,
        tokens_used=ai_response.tokens_used,
    )