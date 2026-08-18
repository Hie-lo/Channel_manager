"""
هندلرهای مدیریت توکن AI
- نمایش موجودی
- خرید توکن اضافی
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from app.config import settings
from app.database.connection import AsyncSessionLocal
from app.database.models import CustomerStatus
from app.services.customer_service import get_customer_by_telegram_id
from app.services.subscription.service import get_active_subscription
from app.services.subscription.plans import get_plan
from app.services.ai_token_service import (
    get_tokens_breakdown,
    add_purchased_tokens,
)
from app.bot.states.user_state import (
    UserState,
    set_user_state,
    get_user_state,
    get_user_data,
    clear_user_state,
)
from app.utils.logger import log
from app.utils.admin_check import (
        detect_platform_from_context,
        get_admin_id_for_platform,
    )

# پکیج‌های توکن قابل خرید
TOKEN_PACKAGES = [
    {"key": "small", "amount": 50, "price": 50_000, "label": "۵۰ توکن"},
    {"key": "medium", "amount": 100, "price": 80_000, "label": "۱۰۰ توکن (۲۰٪ تخفیف)"},
    {"key": "large", "amount": 300, "price": 200_000, "label": "۳۰۰ توکن (۳۳٪ تخفیف)"},
]


def _format_price(amount: int) -> str:
    return f"{amount:,}"


def _get_ai_tokens_menu_keyboard() -> InlineKeyboardMarkup:
    """کیبورد منوی توکن AI"""
    keyboard = [
        [InlineKeyboardButton("🛒 خرید توکن اضافی", callback_data="ai_buy_tokens")],
    ]
    return InlineKeyboardMarkup(keyboard)


def _get_token_packages_keyboard() -> InlineKeyboardMarkup:
    """کیبورد پکیج‌های خرید"""
    keyboard = []
    for pkg in TOKEN_PACKAGES:
        text = f"{pkg['label']} - {_format_price(pkg['price'])} ت"
        keyboard.append([
            InlineKeyboardButton(text, callback_data=f"ai_pkg_{pkg['key']}")
        ])
    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت", callback_data="ai_menu_back")
    ])
    return InlineKeyboardMarkup(keyboard)


def _get_cancel_purchase_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ لغو خرید", callback_data="ai_cancel_purchase")
    ]])


async def ai_tokens_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش منوی توکن AI"""
    user = update.effective_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)

        if not customer or customer.customer_status != CustomerStatus.ACTIVE:
            await update.message.reply_text("❌ حساب شما فعال نیست.")
            return

        subscription = await get_active_subscription(session, customer.id)
        breakdown = await get_tokens_breakdown(session, customer.id)

    # ساخت متن
    text = (
        f"🤖 توکن AI\n"
        f"━━━━━━━━━━━━━━━\n"
    )

    if not subscription:
        text += (
            f"⚠️ برای استفاده از AI باید اشتراک فعال داشته باشید.\n\n"
            f"ولی می‌تونید توکن خریداری کنید (بعد از فعال کردن اشتراک استفاده کنید).\n"
            f"━━━━━━━━━━━━━━━\n"
        )
    else:
        plan = get_plan(subscription.plan_key)
        text += f"📦 پلن فعلی: {plan.emoji} {plan.name_fa}\n"

        if plan.can_use_ai:
            text += f"✅ AI فعال است\n"
        else:
            text += (
                f"⚠️ پلن شما شامل AI نیست\n"
                f"ولی می‌تونید توکن اضافی خریداری کنید\n"
            )
        text += f"━━━━━━━━━━━━━━━\n"

    text += (
        f"\n💳 موجودی توکن:\n"
        f"├── 📅 ماهانه: {breakdown['monthly_remaining']}/{breakdown['monthly_total']}\n"
        f"├── 💰 خریداری شده: {breakdown['purchased_remaining']}\n"
        f"└── 🎯 کل قابل استفاده: {breakdown['total_remaining']}\n"
    )

    if breakdown['next_monthly_reset']:
        text += (
            f"\n📅 تاریخ ریست توکن ماهانه:\n"
            f"   {breakdown['next_monthly_reset'].strftime('%Y/%m/%d')}\n"
        )

    text += (
        f"\n━━━━━━━━━━━━━━━\n"
        f"💡 نکات:\n"
        f"• هر تولید یا بهبود توضیحات = ۱ توکن\n"
        f"• توکن ماهانه در پایان دوره منقضی می‌شود\n"
        f"• توکن خریداری شده انقضا ندارد ✅\n"
        f"• توکن ماهانه اول مصرف می‌شود"
    )

    await update.message.reply_text(
        text,
        reply_markup=_get_ai_tokens_menu_keyboard(),
    )


async def ai_buy_tokens_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش پکیج‌های خرید توکن"""
    query = update.callback_query
    await query.answer()

    text = (
        f"🛒 خرید توکن AI\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"پکیج مورد نظر رو انتخاب کنید:\n\n"
        f"💰 قیمت‌های تخفیف‌دار برای پکیج‌های بزرگ‌تر\n"
        f"⚠️ توکن‌های خریداری شده انقضا ندارند"
    )

    await query.edit_message_text(
        text,
        reply_markup=_get_token_packages_keyboard(),
    )


async def ai_package_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """کاربر یک پکیج رو انتخاب کرد → نمایش صورتحساب"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    pkg_key = query.data.replace("ai_pkg_", "")

    # پیدا کردن پکیج
    package = next((p for p in TOKEN_PACKAGES if p["key"] == pkg_key), None)
    if not package:
        await query.edit_message_text("❌ پکیج نامعتبر!")
        return

    # ذخیره در state
    set_user_state(user.id, UserState.WAITING_AI_TOKEN_RECEIPT, data={
        "package_key": pkg_key,
        "amount": package["amount"],
        "price": package["price"],
    })

    text = (
        f"💳 صورتحساب خرید توکن\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🎯 پکیج: {package['label']}\n"
        f"💰 مبلغ: {_format_price(package['price'])} تومان\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"لطفاً مبلغ را به کارت زیر واریز کنید:\n\n"
        f"💳 <code>{settings.PAYMENT_CARD_NUMBER}</code>\n\n"
        f"👤 به نام: {settings.PAYMENT_CARD_HOLDER}\n\n"
        f"⚠️ بعد از واریز، عکس رسید یا اسکرین‌شات را ارسال کنید.\n"
        f"💡 توکن‌ها بعد از تایید ادمین به حساب شما اضافه می‌شود."
    )

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=_get_cancel_purchase_keyboard(),
    )


async def ai_cancel_purchase_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """لغو فرآیند خرید"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    clear_user_state(user.id)

    await query.edit_message_text(
        "❌ خرید لغو شد.\n\n"
        "هر وقت خواستید از منوی '🤖 توکن AI' دوباره شروع کنید."
    )


async def ai_menu_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """برگشت به منوی اصلی توکن AI"""
    query = update.callback_query
    await query.answer()

    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            return

        subscription = await get_active_subscription(session, customer.id)
        breakdown = await get_tokens_breakdown(session, customer.id)

    text = (
        f"🤖 توکن AI\n"
        f"━━━━━━━━━━━━━━━\n"
    )

    if not subscription:
        text += f"⚠️ اشتراک فعال ندارید\n━━━━━━━━━━━━━━━\n"
    else:
        plan = get_plan(subscription.plan_key)
        text += f"📦 پلن فعلی: {plan.emoji} {plan.name_fa}\n━━━━━━━━━━━━━━━\n"

    text += (
        f"\n💳 موجودی توکن:\n"
        f"├── 📅 ماهانه: {breakdown['monthly_remaining']}/{breakdown['monthly_total']}\n"
        f"├── 💰 خریداری شده: {breakdown['purchased_remaining']}\n"
        f"└── 🎯 کل قابل استفاده: {breakdown['total_remaining']}"
    )

    await query.edit_message_text(
        text,
        reply_markup=_get_ai_tokens_menu_keyboard(),
    )


async def ai_token_receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    دریافت رسید خرید توکن
    فقط وقتی state = WAITING_AI_TOKEN_RECEIPT
    """
    user = update.effective_user

    if get_user_state(user.id) != UserState.WAITING_AI_TOKEN_RECEIPT:
        return

    user_data = get_user_data(user.id)
    package_key = user_data.get("package_key")
    amount = user_data.get("amount")
    price = user_data.get("price")

    if not amount or not price:
        await update.message.reply_text("❌ خطا در پرداخت. لطفاً از اول شروع کنید.")
        clear_user_state(user.id)
        return

    # پیام تایید به مشتری
    await update.message.reply_text(
        f"✅ رسید دریافت شد!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🎯 پکیج: {amount} توکن\n"
        f"💰 مبلغ: {_format_price(price)} تومان\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"⏳ منتظر تایید ادمین باشید.\n"
        f"معمولاً کمتر از ۲ ساعت طول می‌کشد."
    )

    # ارسال به ادمین
    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)

    name = customer.first_name or ""
    if customer.last_name:
        name += f" {customer.last_name}"
    username_text = f"@{customer.username}" if customer.username else "ندارد"

    admin_text = (
        f"🤖 خرید توکن AI\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 مشتری: {name}\n"
        f"🔗 یوزرنیم: {username_text}\n"
        f"🆔 آیدی: {customer.telegram_user_id}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🎯 مقدار: {amount} توکن\n"
        f"💰 مبلغ: {_format_price(price)} تومان\n"
        f"━━━━━━━━━━━━━━━"
    )

    # کیبورد تایید ادمین (با اطلاعات مشتری و مقدار)
    admin_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ تایید و افزودن توکن",
                callback_data=f"ai_admin_approve_{customer.id}_{amount}"
            ),
            InlineKeyboardButton(
                "❌ رد",
                callback_data=f"ai_admin_reject_{customer.telegram_user_id}"
            ),
        ]
    ])

    platform = detect_platform_from_context(context)
    admin_id = get_admin_id_for_platform(platform)

    try:
        if update.message.photo:
            photo = update.message.photo[-1]
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=photo.file_id,
                caption=admin_text,
                reply_markup=admin_keyboard,
            )
        elif update.message.document:
            await context.bot.send_document(
                chat_id=admin_id,
                document=update.message.document.file_id,
                caption=admin_text,
                reply_markup=admin_keyboard,
            )
        else:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_text + "\n\n⚠️ رسیدی ارسال نشد!",
                reply_markup=admin_keyboard,
            )
    except Exception as e:
        log.error(f"خطا در ارسال رسید توکن به ادمین {admin_id}: {e}")

    clear_user_state(user.id)


async def ai_admin_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ادمین خرید توکن رو تایید می‌کنه"""
    query = update.callback_query
    await query.answer()

    # data: ai_admin_approve_{customer_id}_{amount}
    parts = query.data.replace("ai_admin_approve_", "").split("_")
    if len(parts) != 2:
        return

    try:
        customer_id = int(parts[0])
        amount = int(parts[1])
    except ValueError:
        return

    async with AsyncSessionLocal() as session:
        # افزودن توکن
        await add_purchased_tokens(session, customer_id, amount)

        # گرفتن مشتری
        from app.database.models import Customer
        from sqlalchemy import select
        result = await session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = result.scalar_one_or_none()

    # آپدیت پیام ادمین
    original_text = query.message.caption or query.message.text or ""
    new_text = original_text + f"\n\n✅ تایید شد - {amount} توکن اضافه شد"

    try:
        if query.message.caption:
            await query.edit_message_caption(caption=new_text)
        else:
            await query.edit_message_text(text=new_text)
    except Exception as e:
        log.error(f"خطا در آپدیت پیام: {e}")

    # اطلاع به مشتری
    if customer:
        try:
            await context.bot.send_message(
                chat_id=customer.telegram_user_id,
                text=(
                    f"🎉 خرید شما تایید شد!\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"🤖 {amount} توکن AI به حساب شما اضافه شد\n"
                    f"⏰ این توکن‌ها انقضا ندارند\n"
                    f"━━━━━━━━━━━━━━━\n\n"
                    f"از منوی '🤖 توکن AI' موجودی خودتون رو ببینید."
                ),
            )
        except Exception as e:
            log.error(f"خطا در ارسال به مشتری: {e}")


async def ai_admin_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ادمین خرید توکن رو رد می‌کنه"""
    query = update.callback_query
    await query.answer()

    customer_telegram_id = int(query.data.replace("ai_admin_reject_", ""))

    # آپدیت پیام ادمین
    original_text = query.message.caption or query.message.text or ""
    new_text = original_text + "\n\n❌ رد شد"

    try:
        if query.message.caption:
            await query.edit_message_caption(caption=new_text)
        else:
            await query.edit_message_text(text=new_text)
    except Exception as e:
        log.error(f"خطا: {e}")

    # اطلاع به مشتری
    try:
        await context.bot.send_message(
            chat_id=customer_telegram_id,
            text=(
                "❌ متأسفانه خرید توکن شما تایید نشد.\n\n"
                "لطفاً با پشتیبانی تماس بگیرید."
            ),
        )
    except Exception as e:
        log.error(f"خطا در ارسال به مشتری: {e}")