"""
هندلرهای مربوط به مشتری
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
from app.services.business_service import (
    create_business_for_customer,
    get_business_for_customer,
)
from app.business.config import get_business
from app.bot.keyboards.main_menu import get_pending_approval_keyboard
from app.utils.logger import log


async def business_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """وقتی مشتری نوع کسب‌وکار را انتخاب می‌کند"""

    query = update.callback_query
    await query.answer()

    user = query.from_user
    data = query.data

    # استخراج کلید کسب‌وکار
    business_key = data.replace("biz_", "")
    business_config = get_business(business_key)

    if not business_config:
        # اگر "other" یا کسب‌وکار ناشناخته
        await query.edit_message_text(
            "❌ این نوع کسب‌وکار در حال حاضر پشتیبانی نمی‌شود.\n"
            "لطفاً یکی از موارد پشتیبانی شده را انتخاب کنید."
        )
        return

    business_name = f"{business_config.emoji} {business_config.name_fa}"

    async with AsyncSessionLocal() as session:
        # ذخیره نوع کسب‌وکار در جدول Customer
        customer = await set_customer_business_type(
            session=session,
            telegram_user_id=user.id,
            business_type_key=business_key,
        )

        if not customer:
            await query.edit_message_text("❌ خطا! لطفاً دوباره /start بزنید.")
            return

        # ایجاد رکورد در جدول Business
        existing_business = await get_business_for_customer(session, customer.id)
        if not existing_business:
            # استفاده از نام کاربر به عنوان نام موقت کسب‌وکار
            business_name_for_db = f"کسب‌وکار {user.first_name or 'جدید'}"
            await create_business_for_customer(
                session=session,
                customer_id=customer.id,
                business_type_key=business_key,
                business_name=business_name_for_db,
                contact_text=f"@{user.username}" if user.username else None,
            )

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

    customer_telegram_id = int(query.data.replace("approve_", ""))

    async with AsyncSessionLocal() as session:
        customer = await approve_customer(session, customer_telegram_id)

        if not customer:
            await query.edit_message_text("❌ مشتری پیدا نشد!")
            return

        name = customer.first_name or "کاربر"

        await query.edit_message_text(query.message.text + "\n\n✅ تایید شد")

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
            log.error(f"خطا در ارسال پیام: {e}")


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

        await query.edit_message_text(query.message.text + "\n\n❌ رد شد")

        try:
            await context.bot.send_message(
                chat_id=customer_telegram_id,
                text=(
                    "❌ متأسفانه درخواست شما تایید نشد.\n"
                    "برای اطلاعات بیشتر با پشتیبانی تماس بگیرید."
                ),
            )
        except Exception as e:
            log.error(f"خطا در ارسال پیام: {e}")