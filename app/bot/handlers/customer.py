"""
هندلرهای مربوط به مشتری
انتخاب کسب‌وکار، تایید/رد و ...
"""

from telegram import Update
from telegram.ext import ContextTypes

from app.config import settings
from app.database.connection import AsyncSessionLocal
from app.services.customer_service import (
    get_customer_by_telegram_id,
    set_customer_business_type,
    approve_customer,
    reject_customer,
)
from app.bot.keyboards.main_menu import get_pending_approval_keyboard
from app.utils.logger import log

# نام‌های فارسی کسب‌وکارها
BUSINESS_TYPE_NAMES = {
    "laptop_store": "💻 فروش لپتاپ و کامپیوتر",
    "mobile_store": "📱 فروش موبایل و تبلت",
    "clothing_store": "👕 پوشاک",
    "other": "📦 سایر",
}


async def business_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """وقتی مشتری نوع کسب‌وکار را انتخاب می‌کند"""

    query = update.callback_query
    await query.answer()

    user = query.from_user
    data = query.data  # مثال: biz_laptop_store

    # استخراج کلید کسب‌وکار
    business_key = data.replace("biz_", "")
    business_name = BUSINESS_TYPE_NAMES.get(business_key, "سایر")

    async with AsyncSessionLocal() as session:
        # ذخیره نوع کسب‌وکار
        customer = await set_customer_business_type(
            session=session,
            telegram_user_id=user.id,
            business_type_key=business_key,
        )

        if not customer:
            await query.edit_message_text("❌ خطا! لطفاً دوباره /start بزنید.")
            return

        # اطلاع به مشتری
        await query.edit_message_text(
            f"✅ نوع کسب‌وکار ثبت شد: {business_name}\n\n"
            f"⏳ درخواست شما ثبت شد.\n"
            f"منتظر تایید ادمین باشید.\n"
            f"بعد از تایید پیام دریافت خواهید کرد."
        )

        # ارسال اطلاع به ادمین
        await _notify_admin_new_customer(context, customer, business_name)


async def _notify_admin_new_customer(context, customer, business_name: str) -> None:
    """ارسال اطلاع به ادمین درباره مشتری جدید"""

    name = customer.first_name or ""
    if customer.last_name:
        name += f" {customer.last_name}"

    username_text = f"@{customer.username}" if customer.username else "ندارد"

    message = (
        f"🔔 درخواست عضویت جدید\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 نام: {name}\n"
        f"🔗 یوزرنیم: {username_text}\n"
        f"🆔 آیدی: {customer.telegram_user_id}\n"
        f"🏢 کسب‌وکار: {business_name}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await context.bot.send_message(
        chat_id=settings.ADMIN_CHAT_ID,
        text=message,
        reply_markup=get_pending_approval_keyboard(customer.telegram_user_id),
    )


async def approve_customer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ادمین مشتری را تایید می‌کند"""

    query = update.callback_query
    await query.answer()

    # استخراج آیدی مشتری از callback_data
    customer_telegram_id = int(query.data.replace("approve_", ""))

    async with AsyncSessionLocal() as session:
        customer = await approve_customer(session, customer_telegram_id)

        if not customer:
            await query.edit_message_text("❌ مشتری پیدا نشد!")
            return

        name = customer.first_name or "کاربر"

        # آپدیت پیام ادمین
        await query.edit_message_text(
            query.message.text + "\n\n✅ تایید شد"
        )

        # اطلاع به مشتری
        try:
            await context.bot.send_message(
                chat_id=customer_telegram_id,
                text=(
                    f"🎉 {name} عزیز!\n\n"
                    f"حساب شما تایید شد.\n"
                    f"برای شروع دستور /start را بزنید."
                ),
            )
        except Exception as e:
            log.error(f"خطا در ارسال پیام به مشتری {customer_telegram_id}: {e}")


async def reject_customer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ادمین مشتری را رد می‌کند"""

    query = update.callback_query
    await query.answer()

    customer_telegram_id = int(query.data.replace("reject_", ""))

    async with AsyncSessionLocal() as session:
        customer = await reject_customer(session, customer_telegram_id)

        if not customer:
            await query.edit_message_text("❌ مشتری پیدا نشد!")
            return

        # آپدیت پیام ادمین
        await query.edit_message_text(
            query.message.text + "\n\n❌ رد شد"
        )

        # اطلاع به مشتری
        try:
            await context.bot.send_message(
                chat_id=customer_telegram_id,
                text=(
                    "❌ متأسفانه درخواست شما تایید نشد.\n"
                    "برای اطلاعات بیشتر با پشتیبانی تماس بگیرید."
                ),
            )
        except Exception as e:
            log.error(f"خطا در ارسال پیام به مشتری {customer_telegram_id}: {e}")