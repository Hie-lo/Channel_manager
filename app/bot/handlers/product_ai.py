"""
هندلرهای مربوط به تولید توضیحات با AI
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from app.config import settings
from app.database.connection import AsyncSessionLocal
from app.database.models import CustomerStatus, Product
from app.services.customer_service import get_customer_by_telegram_id
from app.services.subscription.service import get_active_subscription
from app.services.subscription.plans import get_plan
from app.services.business_service import (
    get_business_config_for_customer,
    get_business_for_customer,
)
from app.services.ai_token_service import (
    can_use_tokens,
    consume_tokens,
    refund_tokens,
    get_total_available_tokens,
)
from app.services.ai_usage_log_service import (
    log_ai_usage,
    mark_log_as_accepted,
)
from app.services.ai.service import generate_product_description
from app.services.content.post_builder import build_post_caption
from app.bot.states.user_state import (
    UserState,
    set_user_state,
    get_user_data,
    clear_user_state,
)
from app.utils.logger import log
from sqlalchemy import select


COST_PER_GENERATION = 1  # هر تولید = ۱ توکن


def _get_ai_prompt_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """کیبورد تایید مصرف توکن"""
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ تایید و تولید",
                callback_data=f"ai_confirm_gen_{product_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                "❌ انصراف",
                callback_data=f"prod_view_{product_id}"
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def _get_ai_result_keyboard(product_id: int, log_id: int) -> InlineKeyboardMarkup:
    """کیبورد نتیجه AI"""
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ قبول و ذخیره",
                callback_data=f"ai_accept_{product_id}_{log_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                "🔄 دوباره بساز (۱ توکن)",
                callback_data=f"ai_regen_{product_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                "❌ انصراف",
                callback_data=f"prod_view_{product_id}"
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def ai_start_generation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    شروع فرآیند تولید توضیحات با AI
    نمایش هزینه و درخواست تایید
    """
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.replace("ai_start_", ""))
    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer or customer.customer_status != CustomerStatus.ACTIVE:
            await query.answer("❌ حساب شما فعال نیست", show_alert=True)
            return

        # چک اشتراک
        subscription = await get_active_subscription(session, customer.id)
        if not subscription:
            await query.edit_message_text(
                "❌ برای استفاده از AI باید اشتراک فعال داشته باشید.\n"
                "از منوی '💳 اشتراک من' اشتراک تهیه کنید."
            )
            return

        plan = get_plan(subscription.plan_key)
        available_tokens = await get_total_available_tokens(session, customer.id)

        # پیدا کردن محصول
        result = await session.execute(
            select(Product).where(
                Product.id == product_id,
                Product.customer_id == customer.id,
            )
        )
        product = result.scalar_one_or_none()

        if not product:
            await query.edit_message_text("❌ محصول پیدا نشد!")
            return

    # چک توکن کافی
    if available_tokens < COST_PER_GENERATION:
        await query.edit_message_text(
            f"❌ توکن AI کافی ندارید!\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 موجودی: {available_tokens} توکن\n"
            f"💸 نیاز: {COST_PER_GENERATION} توکن\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"از منوی '🤖 توکن AI' توکن خریداری کنید."
        )
        return

    # نمایش تایید
    has_existing = bool(product.description_manual and product.description_manual.strip())
    mode_text = "بهبود متن موجود" if has_existing else "تولید متن جدید"
    mode_emoji = "🔄" if has_existing else "✨"

    text = (
        f"🤖 استفاده از AI\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📦 محصول: {product.product_name}\n"
        f"🎯 عملیات: {mode_emoji} {mode_text}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 هزینه: {COST_PER_GENERATION} توکن\n"
        f"💳 موجودی شما: {available_tokens} توکن\n"
        f"💳 بعد از این: {available_tokens - COST_PER_GENERATION} توکن\n"
        f"━━━━━━━━━━━━━━━\n\n"
    )

    if has_existing:
        text += (
            f"📝 متن فعلی:\n"
            f"{product.description_manual[:200]}\n\n"
            f"AI این متن رو بهبود می‌ده و مزایا/نکات اضافه می‌کنه."
        )
    else:
        text += (
            f"AI بر اساس مشخصات محصول یک توضیح جذاب\n"
            f"همراه با مزایا و نکات تولید می‌کنه."
        )

    await query.edit_message_text(
        text,
        reply_markup=_get_ai_prompt_keyboard(product_id),
    )


async def ai_confirm_generation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """کاربر تایید کرد - مصرف توکن و فراخوانی AI"""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.replace("ai_confirm_gen_", ""))
    user = query.from_user

    # پیام "در حال پردازش"
    await query.edit_message_text("🤖 در حال تولید با AI...\nلطفاً چند لحظه صبر کنید.")

    log_id = await _do_ai_generation(context.bot, user.id, product_id, query)


async def ai_regenerate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دوباره تولید کن (مصرف ۱ توکن دیگه)"""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.replace("ai_regen_", ""))
    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            return

        # چک توکن
        available = await get_total_available_tokens(session, customer.id)
        if available < COST_PER_GENERATION:
            await query.answer(
                f"❌ توکن کافی ندارید! موجودی: {available}",
                show_alert=True,
            )
            return

    await query.edit_message_text("🤖 در حال تولید مجدد با AI...\nلطفاً صبر کنید.")

    await _do_ai_generation(context.bot, user.id, product_id, query)


async def _do_ai_generation(bot, telegram_user_id: int, product_id: int, query):
    """اجرای اصلی تولید AI + مدیریت توکن"""
    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, telegram_user_id)
        if not customer:
            await query.edit_message_text("❌ خطا!")
            return

        # پیدا کردن محصول
        result = await session.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()

        if not product:
            await query.edit_message_text("❌ محصول پیدا نشد!")
            return

        business_config = get_business_config_for_customer(customer)

        # مصرف توکن قبل از فراخوانی AI
        consumed = await consume_tokens(session, customer.id, COST_PER_GENERATION)
        if not consumed:
            await query.edit_message_text(
                "❌ توکن کافی ندارید!\n"
                "از منوی '🤖 توکن AI' توکن خریداری کنید."
            )
            return

    # فراخوانی AI (خارج از session)
    result = await generate_product_description(
        product=product,
        business_config=business_config,
        mode="auto",
    )

    # اگه AI خطا داد، توکن رو برگردون
    if not result.success:
        async with AsyncSessionLocal() as session:
            await refund_tokens(session, customer.id, COST_PER_GENERATION)

            # لاگ خطا
            await log_ai_usage(
                session=session,
                customer_id=customer.id,
                product_id=product.id,
                usage_type="failed",
                tokens_used=0,  # برگردانده شد
                model_used=settings.AI_MODEL,
                accepted=False,
                raw_response=result.raw_response or result.error_message,
            )

        await query.edit_message_text(
            f"❌ خطا در تولید با AI\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📝 دلیل: {result.error_message}\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"💰 توکن به حسابتون برگردانده شد.\n\n"
            f"لطفاً دوباره تلاش کنید.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "🔙 بازگشت",
                    callback_data=f"prod_view_{product_id}"
                )
            ]]),
        )
        return

    # موفق - لاگ کن
    async with AsyncSessionLocal() as session:
        # چک وجود description قبلی
        result_prod = await session.execute(
            select(Product).where(Product.id == product_id)
        )
        p = result_prod.scalar_one_or_none()
        had_existing = bool(p.description_manual and p.description_manual.strip()) if p else False

        usage_log = await log_ai_usage(
            session=session,
            customer_id=customer.id,
            product_id=product.id,
            usage_type="improve" if had_existing else "generate",
            tokens_used=COST_PER_GENERATION,
            model_used=settings.AI_MODEL,
            accepted=False,  # هنوز کاربر تایید نکرده
            raw_response=result.raw_response,
        )
        log_id = usage_log.id

    # نمایش نتیجه به کاربر
    await _show_ai_result(query, product_id, result, log_id)


async def _show_ai_result(query, product_id: int, ai_result, log_id: int):
    """نمایش نتیجه AI به کاربر"""

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, query.from_user.id)
        available = await get_total_available_tokens(session, customer.id)

    text = (
        f"🤖 نتیجه AI\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"{ai_result.formatted_text}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💳 موجودی باقیمانده: {available} توکن\n\n"
        f"می‌خوای این متن رو ذخیره کنی؟"
    )

    # ذخیره log_id در state برای استفاده بعدی
    set_user_state(
        query.from_user.id,
        UserState.VIEWING_AI_RESULT,
        data={"log_id": log_id, "formatted_text": ai_result.formatted_text},
    )

    await query.edit_message_text(
        text,
        reply_markup=_get_ai_result_keyboard(product_id, log_id),
    )


async def ai_accept_result_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """کاربر نتیجه AI رو قبول کرد - ذخیره در محصول"""
    query = update.callback_query
    await query.answer()

    # ai_accept_{product_id}_{log_id}
    parts = query.data.replace("ai_accept_", "").split("_")
    if len(parts) != 2:
        return

    try:
        product_id = int(parts[0])
        log_id = int(parts[1])
    except ValueError:
        return

    user = query.from_user
    user_data = get_user_data(user.id)
    formatted_text = user_data.get("formatted_text", "")

    if not formatted_text:
        await query.edit_message_text("❌ خطا! لطفاً دوباره تلاش کنید.")
        clear_user_state(user.id)
        return

    async with AsyncSessionLocal() as session:
        # آپدیت محصول
        result = await session.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()

        if not product:
            await query.edit_message_text("❌ محصول پیدا نشد!")
            return

        # ذخیره متن AI به عنوان description
        product.description_manual = formatted_text
        await session.commit()

        # علامت‌گذاری لاگ به عنوان قبول شده
        await mark_log_as_accepted(session, log_id)

    clear_user_state(user.id)

    await query.edit_message_text(
        f"✅ توضیحات با AI ذخیره شد!\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"از الان پست‌های این محصول با این توضیحات ارسال میشن.\n\n"
        f"💡 برای دیدن پیش‌نمایش پست، دکمه '👁 پیش‌نمایش' رو بزنید.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👁 پیش‌نمایش پست", callback_data=f"prod_preview_{product_id}")],
            [InlineKeyboardButton("🔙 بازگشت به محصول", callback_data=f"prod_view_{product_id}")],
        ]),
    )