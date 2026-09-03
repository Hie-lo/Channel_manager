"""
هندلرهای مربوط به تولید توضیحات با AI
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from app.config import settings
from app.database.connection import AsyncSessionLocal
from app.database.models import CustomerStatus, Product, AIUsageLog
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
                "✏️ ویرایش توضیحات",
                callback_data=f"ai_edit_{product_id}_{log_id}"
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
    has_existing = bool(product.description_custom and product.description_custom.strip())
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
            f"{product.description_custom[:200]}\n\n"
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
        had_existing = bool(p.description_custom and p.description_custom.strip()) if p else False

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
        data={
            "log_id": log_id,
            "formatted_text": ai_result.formatted_text,
            "ai_description_obj": ai_result.description,  # ذخیره شیء ساختاریافته
        },
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
    
    # دریافت نتیجه AI ساختاریافته
    ai_description_obj = user_data.get("ai_description_obj")
    
    if not ai_description_obj:
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

        # ذخیره ساختاریافته داده‌های AI
        product.ai_description = ai_description_obj.description
        product.ai_pros = ai_description_obj.pros if ai_description_obj.pros else []
        product.ai_cons = ai_description_obj.cons if ai_description_obj.cons else []
        
        # اگر features وجود داشت (کسب‌وکارهای کامپیوتری)، در pros ذخیره می‌کنیم
        if ai_description_obj.features:
            product.ai_pros = ai_description_obj.features
        
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



async def ai_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ویرایش توضیحات AI قبل از ذخیره (از صفحه نتیجه AI)"""
    query = update.callback_query
    await query.answer()

    parts = query.data.replace("ai_edit_", "").split("_")
    product_id = int(parts[0])
    log_id = int(parts[1])

    user = query.from_user

    # گرفتن نتیجه AI از user_data
    user_data = get_user_data(user.id)
    ai_description_obj = user_data.get("ai_description_obj")

    if not ai_description_obj:
        await query.edit_message_text("❌ نتیجه AI پیدا نشد!")
        return

    description = ai_description_obj.description or ""
    
    # بررسی features یا pros
    if hasattr(ai_description_obj, 'features') and ai_description_obj.features:
        pros_or_features = ai_description_obj.features
    else:
        pros_or_features = ai_description_obj.pros or []
    
    cons = ai_description_obj.cons or []

    text = (
        f"✏️ ویرایش توضیحات AI\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"📝 **توضیح اصلی:**\n{description}\n\n"
    )

    if pros_or_features:
        text += f"✅ **مزایا/ویژگی‌ها:**\n"
        for item in pros_or_features:
            text += f"• {item}\n"
        text += "\n"

    if cons:
        text += f"❌ **معایب:**\n"
        for item in cons:
            text += f"• {item}\n"
        text += "\n"

    text += f"کدام بخش را می‌خواهید ویرایش کنید؟"

    keyboard = [
        [InlineKeyboardButton("📝 توضیح اصلی", callback_data=f"ai_edit_desc_{product_id}_{log_id}")],
        [InlineKeyboardButton("✅ مزایا/ویژگی‌ها", callback_data=f"ai_edit_pros_{product_id}_{log_id}")],
    ]

    if cons:
        keyboard.append([InlineKeyboardButton("❌ معایب", callback_data=f"ai_edit_cons_{product_id}_{log_id}")])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"ai_view_result_{product_id}_{log_id}")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def ai_edit_saved_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ویرایش توضیحات AI ذخیره شده (از صفحه جزئیات محصول)"""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.replace("ai_edit_saved_", ""))
    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            await query.edit_message_text("❌ خطا!")
            return

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

    description = product.ai_description or ""
    pros = product.ai_pros or []
    cons = product.ai_cons or []

    text = (
        f"✏️ ویرایش توضیحات AI ذخیره شده\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"📝 **توضیح اصلی:**\n{description}\n\n"
    )

    if pros:
        text += f"✅ **مزایا/ویژگی‌ها:**\n"
        for item in pros:
            text += f"• {item}\n"
        text += "\n"

    if cons:
        text += f"❌ **معایب:**\n"
        for item in cons:
            text += f"• {item}\n"
        text += "\n"

    text += f"کدام بخش را می‌خواهید ویرایش کنید؟"

    keyboard = [
        [InlineKeyboardButton("📝 توضیح اصلی", callback_data=f"ai_edit_saved_desc_{product_id}")],
        [InlineKeyboardButton("✅ مزایا/ویژگی‌ها", callback_data=f"ai_edit_saved_pros_{product_id}")],
    ]

    if cons:
        keyboard.append([InlineKeyboardButton("❌ معایب", callback_data=f"ai_edit_saved_cons_{product_id}")])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت به محصول", callback_data=f"prod_view_{product_id}")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def ai_edit_field_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """شروع ویرایش یک فیلد خاص (description/pros/cons)"""
    query = update.callback_query
    await query.answer()

    data = query.data
    user = query.from_user

    # Parse callback data
    if data.startswith("ai_edit_desc_"):
        parts = data.replace("ai_edit_desc_", "").split("_")
        product_id = int(parts[0])
        log_id = int(parts[1])
        field_type = "description"
        from_saved = False
    elif data.startswith("ai_edit_pros_"):
        parts = data.replace("ai_edit_pros_", "").split("_")
        product_id = int(parts[0])
        log_id = int(parts[1])
        field_type = "pros"
        from_saved = False
    elif data.startswith("ai_edit_cons_"):
        parts = data.replace("ai_edit_cons_", "").split("_")
        product_id = int(parts[0])
        log_id = int(parts[1])
        field_type = "cons"
        from_saved = False
    elif data.startswith("ai_edit_saved_desc_"):
        product_id = int(data.replace("ai_edit_saved_desc_", ""))
        log_id = None
        field_type = "description"
        from_saved = True
    elif data.startswith("ai_edit_saved_pros_"):
        product_id = int(data.replace("ai_edit_saved_pros_", ""))
        log_id = None
        field_type = "pros"
        from_saved = True
    elif data.startswith("ai_edit_saved_cons_"):
        product_id = int(data.replace("ai_edit_saved_cons_", ""))
        log_id = None
        field_type = "cons"
        from_saved = True
    else:
        await query.edit_message_text("❌ خطا در پردازش!")
        return

    # گرفتن محتوای فعلی
    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            await query.edit_message_text("❌ خطا!")
            return

        if from_saved:
            # از product
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

            if field_type == "description":
                current_value = product.ai_description or ""
            elif field_type == "pros":
                current_value = "\n".join(product.ai_pros or [])
            else:  # cons
                current_value = "\n".join(product.ai_cons or [])
        else:
            # از user_data (نتیجه AI که هنوز ذخیره نشده)
            user_data = get_user_data(user.id)
            ai_description_obj = user_data.get("ai_description_obj")
            
            if not ai_description_obj:
                await query.edit_message_text("❌ نتیجه AI پیدا نشد!")
                return
            
            if field_type == "description":
                current_value = ai_description_obj.description or ""
            elif field_type == "pros":
                # بررسی features یا pros
                if hasattr(ai_description_obj, 'features') and ai_description_obj.features:
                    items = ai_description_obj.features
                else:
                    items = ai_description_obj.pros or []
                current_value = "\n".join(items)
            else:  # cons
                items = ai_description_obj.cons or []
                current_value = "\n".join(items)

    field_name = {
        "description": "توضیح اصلی",
        "pros": "مزایا/ویژگی‌ها",
        "cons": "معایب"
    }[field_type]

    text = (
        f"✏️ ویرایش {field_name}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"📝 محتوای فعلی (برای کپی کلیک کنید):\n\n"
        f"```\n{current_value}\n```\n\n"
        f"━━━━━━━━━━━━━━━\n\n"
    )

    if field_type in ["pros", "cons"]:
        text += f"لطفاً موارد جدید را هر کدام در یک خط جداگانه ارسال کنید:\n\n"
        text += f"مثال:\n```\nمورد اول\nمورد دوم\nمورد سوم\n```"
    else:
        text += f"لطفاً متن جدید را ارسال کنید:"

    # Set state
    from app.bot.states.user_state import set_user_state, UserState
    if field_type == "description":
        set_user_state(user.id, UserState.EDITING_AI_DESCRIPTION, {
            "product_id": product_id,
            "log_id": log_id,
            "from_saved": from_saved
        })
    elif field_type == "pros":
        set_user_state(user.id, UserState.EDITING_AI_PROS, {
            "product_id": product_id,
            "log_id": log_id,
            "from_saved": from_saved
        })
    else:  # cons
        set_user_state(user.id, UserState.EDITING_AI_CONS, {
            "product_id": product_id,
            "log_id": log_id,
            "from_saved": from_saved
        })

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "🔙 بازگشت", 
                callback_data=f"ai_edit_saved_{product_id}" if from_saved else f"ai_edit_{product_id}_{log_id}"
            )
        ]])
    )


async def ai_edit_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دریافت متن ویرایش شده"""
    user = update.effective_user
    from app.bot.states.user_state import get_user_state, get_user_data, clear_user_state, UserState

    state = get_user_state(user.id)
    if state not in [UserState.EDITING_AI_DESCRIPTION, UserState.EDITING_AI_PROS, UserState.EDITING_AI_CONS]:
        return

    state_data = get_user_data(user.id)
    product_id = state_data.get("product_id")
    log_id = state_data.get("log_id")
    from_saved = state_data.get("from_saved", False)

    if not product_id:
        await update.message.reply_text("❌ خطا! لطفاً دوباره تلاش کنید.")
        clear_user_state(user.id)
        return

    new_text = update.message.text.strip()

    # تشخیص نوع فیلد
    if state == UserState.EDITING_AI_DESCRIPTION:
        field_type = "description"
        new_value = new_text
    elif state == UserState.EDITING_AI_PROS:
        field_type = "pros"
        # Split by newlines
        new_value = [line.strip() for line in new_text.split('\n') if line.strip()]
    else:  # EDITING_AI_CONS
        field_type = "cons"
        new_value = [line.strip() for line in new_text.split('\n') if line.strip()]

    # ذخیره تغییرات
    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            await update.message.reply_text("❌ خطا!")
            clear_user_state(user.id)
            return

        if from_saved:
            # ذخیره در product
            result = await session.execute(
                select(Product).where(
                    Product.id == product_id,
                    Product.customer_id == customer.id,
                )
            )
            product = result.scalar_one_or_none()
            if not product:
                await update.message.reply_text("❌ محصول پیدا نشد!")
                clear_user_state(user.id)
                return

            if field_type == "description":
                product.ai_description = new_value
            elif field_type == "pros":
                product.ai_pros = new_value
            else:  # cons
                product.ai_cons = new_value

            await session.commit()
        else:
            # ذخیره در user_data (نتیجه AI که هنوز ذخیره نشده)
            user_data = get_user_data(user.id)
            ai_description_obj = user_data.get("ai_description_obj")
            
            if not ai_description_obj:
                await update.message.reply_text("❌ نتیجه AI پیدا نشد!")
                clear_user_state(user.id)
                return
            
            # ویرایش object
            if field_type == "description":
                ai_description_obj.description = new_value
            elif field_type == "pros":
                # بررسی features یا pros
                if hasattr(ai_description_obj, 'features'):
                    ai_description_obj.features = new_value
                else:
                    ai_description_obj.pros = new_value
            else:  # cons
                ai_description_obj.cons = new_value
            
            # آپدیت user_data
            set_user_state(user.id, UserState.VIEWING_AI_RESULT, {
                "log_id": log_id,
                "formatted_text": user_data.get("formatted_text", ""),
                "ai_description_obj": ai_description_obj,
            })

    if from_saved:
        clear_user_state(user.id)

    field_name = {
        "description": "توضیح اصلی",
        "pros": "مزایا/ویژگی‌ها",
        "cons": "معایب"
    }[field_type]

    if from_saved:
        await update.message.reply_text(
            f"✅ {field_name} با موفقیت ویرایش و ذخیره شد!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت به محصول", callback_data=f"prod_view_{product_id}")
            ]])
        )
    else:
        await update.message.reply_text(
            f"✅ {field_name} با موفقیت ویرایش شد!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("👀 مشاهده نتیجه", callback_data=f"ai_view_result_{product_id}_{log_id}")
            ]])
        )



async def ai_view_result_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش دوباره نتیجه AI (بعد از ویرایش)"""
    query = update.callback_query
    await query.answer()

    parts = query.data.replace("ai_view_result_", "").split("_")
    product_id = int(parts[0])
    log_id = int(parts[1])

    user = query.from_user
    user_data = get_user_data(user.id)
    ai_description_obj = user_data.get("ai_description_obj")

    if not ai_description_obj:
        await query.edit_message_text("❌ نتیجه AI پیدا نشد!")
        return

    # ساخت متن فرمت شده از object
    formatted_lines = []
    
    if ai_description_obj.description:
        formatted_lines.append(f"📝 {ai_description_obj.description}")
        formatted_lines.append("")
    
    # Features or Pros
    if hasattr(ai_description_obj, 'features') and ai_description_obj.features:
        formatted_lines.append("✨ ویژگی‌ها:")
        for item in ai_description_obj.features:
            formatted_lines.append(f"🔹 {item}")
        formatted_lines.append("")
    elif ai_description_obj.pros:
        formatted_lines.append("✅ مزایا:")
        for item in ai_description_obj.pros:
            formatted_lines.append(f"• {item}")
        formatted_lines.append("")
    
    # Cons
    if ai_description_obj.cons:
        formatted_lines.append("❌ معایب:")
        for item in ai_description_obj.cons:
            formatted_lines.append(f"• {item}")
    
    formatted_text = "\n".join(formatted_lines)

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        available = await get_total_available_tokens(session, customer.id)

    text = (
        f"🤖 نتیجه AI\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"{formatted_text}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💳 موجودی باقیمانده: {available} توکن\n\n"
        f"می‌خوای این متن رو ذخیره کنی؟"
    )

    await query.edit_message_text(
        text,
        reply_markup=_get_ai_result_keyboard(product_id, log_id),
    )
