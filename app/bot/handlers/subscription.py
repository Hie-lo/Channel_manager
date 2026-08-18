"""
هندلرهای مدیریت اشتراک و پرداخت
"""

from telegram import Update
from telegram.ext import ContextTypes
from app.services.ai_token_service import allocate_monthly_tokens
from app.config import settings
from app.database.connection import AsyncSessionLocal
from app.database.models import CustomerStatus
from app.services.customer_service import get_customer_by_telegram_id
from app.services.subscription.service import (
    get_active_subscription,
    get_pending_subscription,
    create_pending_subscription,
    activate_subscription,
    reject_subscription,
    cancel_pending_subscription,
    calculate_days_remaining,
    is_subscription_active,
)
from app.services.subscription.plans import (
    get_plan,
    get_duration_price,
    get_duration_days,
    get_duration_name,
    format_price,
)
from app.bot.keyboards.subscription import (
    get_subscription_menu_keyboard,
    get_plans_keyboard,
    get_duration_keyboard,
    get_cancel_payment_keyboard,
    get_payment_confirmation_keyboard,
)
from app.bot.states.user_state import (
    UserState,
    set_user_state,
    get_user_state,
    get_user_data,
    clear_user_state,
)
from app.utils.admin_check import detect_platform_from_context, get_admin_id_for_platform
from app.utils.logger import log
from sqlalchemy import select


async def subscription_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    نمایش منوی اشتراک
    وقتی مشتری دکمه '💳 اشتراک من' رو میزنه
    """
    user = update.effective_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)

        if not customer or customer.customer_status != CustomerStatus.ACTIVE:
            await update.message.reply_text("❌ حساب شما فعال نیست. /start بزنید.")
            return

        active_sub = await get_active_subscription(session, customer.id)
        pending_sub = await get_pending_subscription(session, customer.id)

    text = "💳 اشتراک\n━━━━━━━━━━━━━━━\n\n"

    if active_sub:
        plan = get_plan(active_sub.plan_key)
        days = calculate_days_remaining(active_sub)
        text += (
            f"✅ اشتراک فعال\n"
            f"📦 پلن: {plan.emoji} {plan.name_fa}\n"
            f"📅 روزهای باقیمانده: {days} روز\n"
        )
    elif pending_sub:
        plan = get_plan(pending_sub.plan_key)
        text += (
            f"⏳ اشتراک در انتظار تایید پرداخت\n"
            f"📦 پلن: {plan.emoji} {plan.name_fa}\n"
        )
    else:
        text += "❌ شما اشتراک فعالی ندارید.\n\nبرای استفاده از ربات یک پلن انتخاب کنید."

    await update.message.reply_text(
        text,
        reply_markup=get_subscription_menu_keyboard(has_active_sub=active_sub is not None),
    )


async def sub_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بازگشت به منوی اشتراک از کالبک"""
    query = update.callback_query
    await query.answer()

    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        active_sub = await get_active_subscription(session, customer.id) if customer else None
        pending_sub = await get_pending_subscription(session, customer.id) if customer else None

    text = "💳 اشتراک\n━━━━━━━━━━━━━━━\n\n"

    if active_sub:
        plan = get_plan(active_sub.plan_key)
        days = calculate_days_remaining(active_sub)
        text += (
            f"✅ اشتراک فعال\n"
            f"📦 پلن: {plan.emoji} {plan.name_fa}\n"
            f"📅 روزهای باقیمانده: {days} روز\n"
        )
    elif pending_sub:
        plan = get_plan(pending_sub.plan_key)
        text += (
            f"⏳ اشتراک در انتظار تایید پرداخت\n"
            f"📦 پلن: {plan.emoji} {plan.name_fa}\n"
        )
    else:
        text += "❌ شما اشتراک فعالی ندارید."

    await query.edit_message_text(
        text,
        reply_markup=get_subscription_menu_keyboard(has_active_sub=active_sub is not None),
    )


async def sub_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش لیست پلن‌ها برای خرید"""
    query = update.callback_query
    await query.answer()

    text = (
        "🛒 انتخاب پلن اشتراک\n"
        "━━━━━━━━━━━━━━━\n\n"
        "🥉 برنزی\n"
        "├── ۱ کانال\n"
        "├── ۵۰ محصول\n"
        "├── هوش مصنوعی ( ۱۰ توکن رایگان/ماه)\n"
        "└── قالب پیش‌فرض\n\n"
        "🥈 نقره‌ای\n"
        "├── ۳ کانال\n"
        "├── ۳۰۰ محصول\n"
        "├── هوش مصنوعی ( ۵۰ توکن رایگان/ماه)\n"
        "└── قالب پیش‌فرض\n\n"
        "🥇 طلایی (پرو)\n"
        "├── 9 کانال\n"
        "├── تعداد محصول نامحدود\n"
        "├── قالب سفارشی\n"
        "├── هوش مصنوعی (۱۰۰ توکن رایگان/ماه)\n"
        "└── گزارش لحظه‌ای\n\n"
        "پلن خود را انتخاب کنید:"
    )

    await query.edit_message_text(text, reply_markup=get_plans_keyboard())


async def sub_plan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """انتخاب پلن → نمایش مدت‌ها"""
    query = update.callback_query
    await query.answer()

    plan_key = query.data.replace("sub_plan_", "")
    plan = get_plan(plan_key)

    if not plan:
        await query.edit_message_text("❌ پلن پیدا نشد!")
        return

    text = (
        f"{plan.emoji} پلن {plan.name_fa}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📢 کانال: {plan.max_channels if plan.max_channels < 9999 else 'نامحدود'}\n"
        f"📦 محصول: {plan.max_products if plan.max_products < 9999 else 'نامحدود'}\n"
        f"🤖 توکن AI: {plan.monthly_ai_tokens} در ماه\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"مدت اشتراک را انتخاب کنید:"
    )

    await query.edit_message_text(text, reply_markup=get_duration_keyboard(plan_key))


async def sub_duration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """انتخاب مدت → نمایش فاکتور و درخواست رسید"""
    query = update.callback_query
    await query.answer()

    # data: sub_dur_GOLD_monthly
    parts = query.data.split("_")
    plan_key = parts[2]
    duration_key = "_".join(parts[3:])

    plan = get_plan(plan_key)
    if not plan:
        await query.edit_message_text("❌ پلن پیدا نشد!")
        return

    price = get_duration_price(plan, duration_key)
    days = get_duration_days(duration_key)
    duration_name = get_duration_name(duration_key)

    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            await query.edit_message_text("❌ خطا!")
            return

        # اگر قبلاً یه pending داشته، لغو کن
        existing_pending = await get_pending_subscription(session, customer.id)
        if existing_pending:
            await session.delete(existing_pending)
            await session.commit()

        # ساخت اشتراک PENDING جدید
        subscription = await create_pending_subscription(
            session=session,
            customer_id=customer.id,
            plan_key=plan_key,
            duration_days=days,
        )

    # ذخیره در state
    set_user_state(user.id, UserState.WAITING_PAYMENT_RECEIPT, data={
        "subscription_id": subscription.id,
        "plan_key": plan_key,
        "duration_key": duration_key,
        "price": price,
    })

    text = (
        f"💳 صورتحساب\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📦 پلن: {plan.emoji} {plan.name_fa}\n"
        f"📅 مدت: {duration_name}\n"
        f"💰 مبلغ: {format_price(price)} تومان\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"لطفاً مبلغ را به کارت زیر واریز کنید:\n\n"
        f"💳 شماره کارت:\n"
        f"`{settings.PAYMENT_CARD_NUMBER}`\n\n"
        f"👤 به نام: {settings.PAYMENT_CARD_HOLDER}\n\n"
        f"⚠️ بعد از واریز، عکس رسید یا اسکرین‌شات را ارسال کنید."
    )

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_cancel_payment_keyboard(),
    )


async def sub_cancel_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """لغو فرآیند پرداخت"""
    query = update.callback_query
    await query.answer()

    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if customer:
            await cancel_pending_subscription(session, customer.id)

    clear_user_state(user.id)

    await query.edit_message_text(
        "❌ فرآیند پرداخت لغو شد.\n\n"
        "هر وقت خواستید می‌تونید از منوی '💳 اشتراک من' دوباره شروع کنید."
    )


async def payment_receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    دریافت عکس رسید پرداخت
    این handler فقط زمانی فعال میشه که state = WAITING_PAYMENT_RECEIPT باشه
    """
    user = update.effective_user
    platform = detect_platform_from_context(context)
    admin_id = get_admin_id_for_platform(platform)
    if get_user_state(user.id) != UserState.WAITING_PAYMENT_RECEIPT:
        return

    user_data = get_user_data(user.id)
    subscription_id = user_data.get("subscription_id")
    plan_key = user_data.get("plan_key")
    duration_key = user_data.get("duration_key")
    price = user_data.get("price")

    if not subscription_id:
        await update.message.reply_text("❌ خطا در پرداخت. لطفاً از اول شروع کنید.")
        clear_user_state(user.id)
        return

    plan = get_plan(plan_key)
    duration_name = get_duration_name(duration_key)

    # پیام تایید به مشتری
    await update.message.reply_text(
        f"✅ رسید دریافت شد!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📦 پلن: {plan.emoji} {plan.name_fa}\n"
        f"📅 مدت: {duration_name}\n"
        f"💰 مبلغ: {format_price(price)} تومان\n"
        f"🔖 شماره پیگیری: PAY-{subscription_id:06d}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"⏳ منتظر تایید ادمین باشید.\n"
        f"معمولاً کمتر از ۲ ساعت طول می‌کشد."
    )

    # ارسال رسید به ادمین
    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)

    name = customer.first_name or ""
    if customer.last_name:
        name += f" {customer.last_name}"
    username_text = f"@{customer.username}" if customer.username else "ندارد"

    admin_text = (
        f"💳 رسید پرداخت جدید\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 مشتری: {name}\n"
        f"🔗 یوزرنیم: {username_text}\n"
        f"🆔 آیدی: {customer.telegram_user_id}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📦 پلن: {plan.emoji} {plan.name_fa}\n"
        f"📅 مدت: {duration_name} ({get_duration_days(duration_key)} روز)\n"
        f"💰 مبلغ: {format_price(price)} تومان\n"
        f"🔖 شماره پیگیری: PAY-{subscription_id:06d}\n"
        f"━━━━━━━━━━━━━━━"
    )

    # ارسال عکس رسید به ادمین
    try:
        if update.message.photo:
            # عکس بزرگترین سایز
            photo = update.message.photo[-1]
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=photo.file_id,
                caption=admin_text,
                reply_markup=get_payment_confirmation_keyboard(subscription_id),
            )
        elif update.message.document:
            await context.bot.send_document(
                chat_id=admin_id,
                document=update.message.document.file_id,
                caption=admin_text,
                reply_markup=get_payment_confirmation_keyboard(subscription_id),
            )
        else:
            # فقط متن
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_text + "\n\n⚠️ رسیدی ارسال نشد!",
                reply_markup=get_payment_confirmation_keyboard(subscription_id),
            )
    except Exception as e:
        log.error(f"خطا در ارسال رسید به ادمین: {e}")

    clear_user_state(user.id)


async def sub_admin_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ادمین پرداخت رو تایید میکنه"""
    query = update.callback_query
    await query.answer()

    subscription_id = int(query.data.replace("sub_admin_approve_", ""))

    async with AsyncSessionLocal() as session:
        # پیدا کردن اشتراک
        result = await session.execute(
            select(Subscription := __import__(
                'app.database.models', fromlist=['Subscription']
            ).Subscription).where(
                __import__(
                    'app.database.models', fromlist=['Subscription']
                ).Subscription.id == subscription_id
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            await query.edit_message_caption("❌ اشتراک پیدا نشد!") if query.message.caption else await query.edit_message_text("❌ اشتراک پیدا نشد!")
            return

        plan = get_plan(subscription.plan_key)
        duration_days = (subscription.end_at - subscription.start_at).days

        # فعال کردن اشتراک
        activated = await activate_subscription(session, subscription_id, duration_days)
        # اگه پلن پرو (طلایی) هست، توکن AI ماهانه تخصیص بده
        if activated and plan and plan.monthly_ai_tokens > 0:
            try:
                await allocate_monthly_tokens(
                    session=session,
                    customer_id=activated.customer_id,
                    amount=plan.monthly_ai_tokens,
                    duration_days=duration_days,
                )
                log.info(
                    f"✅ {plan.monthly_ai_tokens} توکن AI ماهانه "
                    f"به مشتری {activated.customer_id} تخصیص یافت"
                )
            except Exception as e:
                log.error(f"خطا در تخصیص توکن ماهانه: {e}")
        # گرفتن اطلاعات مشتری
        from app.database.models import Customer
        customer_result = await session.execute(
            select(Customer).where(Customer.id == subscription.customer_id)
        )
        customer = customer_result.scalar_one_or_none()

    # آپدیت پیام ادمین
    original_text = query.message.caption or query.message.text or ""
    new_text = original_text + "\n\n✅ تایید شد و فعال شد"

    try:
        if query.message.caption:
            await query.edit_message_caption(caption=new_text)
        else:
            await query.edit_message_text(text=new_text)
    except Exception as e:
        log.error(f"خطا در آپدیت پیام ادمین: {e}")

    # اطلاع به مشتری
    # اطلاع به مشتری
    if customer and activated:
        try:
            welcome_text = (
                f"🎉 تبریک! اشتراک شما فعال شد!\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📦 پلن: {plan.emoji} {plan.name_fa}\n"
                f"📅 شروع: {activated.start_at.strftime('%Y/%m/%d')}\n"
                f"📅 پایان: {activated.end_at.strftime('%Y/%m/%d')}\n"
                f"📢 حداکثر کانال: {plan.max_channels if plan.max_channels < 9999 else 'نامحدود'}\n"
                f"📦 حداکثر محصول: {plan.max_products if plan.max_products < 9999 else 'نامحدود'}\n"
            )

            if plan.monthly_ai_tokens > 0:
                welcome_text += f"🤖 توکن AI: {plan.monthly_ai_tokens} در ماه\n"

            welcome_text += (
                f"━━━━━━━━━━━━━━━\n\n"
                f"از الان می‌تونید از همه امکانات استفاده کنید! 🚀"
            )

            # ⚠️ آیدی مشتری بر اساس platform
            customer_chat_id = (
                customer.telegram_user_id
                if customer.source_platform == "TELEGRAM"
                else customer.bale_user_id
            )

            if customer_chat_id:
                await context.bot.send_message(
                    chat_id=customer_chat_id,
                    text=welcome_text,
                )
                log.info(f"✅ پیام فعال شدن اشتراک به {customer_chat_id} ارسال شد")
            else:
                log.warning(f"⚠️ مشتری {customer.id} آیدی معتبر نداره")
        except Exception as e:
            log.error(f"خطا در ارسال به مشتری: {e}")


async def sub_admin_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ادمین پرداخت رو رد میکنه"""
    query = update.callback_query
    await query.answer()

    subscription_id = int(query.data.replace("sub_admin_reject_", ""))

    async with AsyncSessionLocal() as session:
        from app.database.models import Subscription, Customer

        result = await session.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            return

        customer_result = await session.execute(
            select(Customer).where(Customer.id == subscription.customer_id)
        )
        customer = customer_result.scalar_one_or_none()

        # آیدی مشتری بر اساس platform
        customer_chat_id = None
        if customer:
            customer_chat_id = (
                customer.telegram_user_id
                if customer.source_platform == "TELEGRAM"
                else customer.bale_user_id
            )

        await reject_subscription(session, subscription_id)

    # آپدیت پیام ادمین
    original_text = query.message.caption or query.message.text or ""
    new_text = original_text + "\n\n❌ رد شد"

    try:
        if query.message.caption:
            await query.edit_message_caption(caption=new_text)
        else:
            await query.edit_message_text(text=new_text)
    except Exception as e:
        log.error(f"خطا در آپدیت پیام ادمین: {e}")

    # اطلاع به مشتری
    if customer_chat_id:
        try:
            await context.bot.send_message(
                chat_id=customer_chat_id,
                text=(
                    "❌ متأسفانه پرداخت شما تایید نشد.\n\n"
                    "لطفاً با پشتیبانی تماس بگیرید."
                ),
            )
            log.info(f"✅ پیام رد پرداخت به {customer_chat_id} ارسال شد")
        except Exception as e:
            log.error(f"خطا در ارسال به مشتری {customer_chat_id}: {e}")
    else:
        log.warning(f"⚠️ آیدی معتبر برای مشتری {customer.id if customer else '?'} پیدا نشد")


async def sub_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش جزئیات اشتراک فعلی"""
    query = update.callback_query
    await query.answer()

    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            await query.edit_message_text("❌ خطا!")
            return

        sub = await get_active_subscription(session, customer.id)

    if not sub:
        await query.edit_message_text("❌ اشتراک فعالی ندارید.")
        return

    plan = get_plan(sub.plan_key)
    days = calculate_days_remaining(sub)

    text = (
        f"📊 وضعیت اشتراک\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📦 پلن: {plan.emoji} {plan.name_fa}\n"
        f"📅 شروع: {sub.start_at.strftime('%Y/%m/%d')}\n"
        f"📅 پایان: {sub.end_at.strftime('%Y/%m/%d')}\n"
        f"⏳ باقیمانده: {days} روز\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📢 حداکثر کانال: {plan.max_channels if plan.max_channels < 9999 else 'نامحدود'}\n"
        f"📦 حداکثر محصول: {plan.max_products if plan.max_products < 9999 else 'نامحدود'}\n"
        f"🤖 توکن AI ماهانه: {plan.monthly_ai_tokens}\n"
        f"📝 قالب سفارشی: {'✅' if plan.can_customize_template else '❌'}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await query.edit_message_text(
        text,
        reply_markup=get_subscription_menu_keyboard(has_active_sub=True),
    )