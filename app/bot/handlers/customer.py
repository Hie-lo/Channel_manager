"""
هندلرهای مربوط به مشتری
"""

from telegram import Update
from telegram.ext import ContextTypes

from app.config import settings
from app.database.connection import AsyncSessionLocal
from app.services.customer_service import (
    get_customer_by_platform_id,
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
from app.utils.admin_check import (
    detect_platform_from_context,
    get_admin_id_for_platform,
)


async def business_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """وقتی مشتری نوع کسب‌وکار را انتخاب می‌کند"""

    query = update.callback_query
    await query.answer()

    user = query.from_user
    data = query.data
    business_key = data.replace("biz_", "")
    business_config = get_business(business_key)

    if not business_config:
        await query.edit_message_text(
            "❌ این نوع کسب‌وکار در حال حاضر پشتیبانی نمی‌شود."
        )
        return

    # تشخیص پلتفرم
    platform = detect_platform_from_context(context)
    business_name = f"{business_config.emoji} {business_config.name_fa}"

    async with AsyncSessionLocal() as session:
        # ذخیره نوع کسب‌وکار
        customer = await set_customer_business_type(
            session=session,
            telegram_user_id=user.id,
            business_type_key=business_key,
            platform=platform,
        )

        if not customer:
            await query.edit_message_text("❌ خطا! لطفاً دوباره /start بزنید.")
            return

        # ایجاد رکورد Business
        existing_business = await get_business_for_customer(session, customer.id)
        if not existing_business:
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
        await _notify_admin_new_customer(
            context, customer, business_name, platform, user.id
        )


async def _notify_admin_new_customer(
    context,
    customer,
    business_name: str,
    platform: str,
    user_id: int,
) -> None:
    """ارسال اطلاع به ادمین درباره مشتری جدید"""

    # نام و اطلاعات از پلتفرم فعلی
    if platform == "TELEGRAM":
        name = customer.telegram_first_name or ""
        if customer.telegram_last_name:
            name += f" {customer.telegram_last_name}"
        username_text = f"@{customer.telegram_username}" if customer.telegram_username else "ندارد"
    else:
        name = customer.bale_first_name or ""
        if customer.bale_last_name:
            name += f" {customer.bale_last_name}"
        username_text = f"@{customer.bale_username}" if customer.bale_username else "ندارد"

    platform_icon = "📱" if platform == "TELEGRAM" else "💬"
    platform_name = "تلگرام" if platform == "TELEGRAM" else "بله"

    message = (
        f"🔔 درخواست عضویت جدید\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{platform_icon} پلتفرم: {platform_name}\n"
        f"👤 نام: {name}\n"
        f"🔗 یوزرنیم: {username_text}\n"
        f"🆔 آیدی: {user_id}\n"
        f"🏢 کسب‌وکار: {business_name}\n"
        f"━━━━━━━━━━━━━━━"
    )

    # ارسال به ادمین همون پلتفرم
    admin_id = get_admin_id_for_platform(platform)

    try:
        await context.bot.send_message(
            chat_id=admin_id,
            text=message,
            reply_markup=get_pending_approval_keyboard(user_id),
        )
    except Exception as e:
        log.error(f"خطا در ارسال اطلاع به ادمین ({admin_id}): {e}")


async def approve_customer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ادمین مشتری را تایید می‌کند"""

    query = update.callback_query
    await query.answer()

    user_id = int(query.data.replace("approve_", ""))
    platform = detect_platform_from_context(context)

    async with AsyncSessionLocal() as session:
        customer = await approve_customer(session, user_id, platform)

        if not customer:
            await query.edit_message_text("❌ مشتری پیدا نشد!")
            return

        # نام از پلتفرم فعلی
        if platform == "TELEGRAM":
            name = customer.telegram_first_name or "کاربر"
        else:
            name = customer.bale_first_name or "کاربر"

        await query.edit_message_text(query.message.text + "\n\n✅ تایید شد")

        try:
            await context.bot.send_message(
                chat_id=user_id,
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

    user_id = int(query.data.replace("reject_", ""))
    platform = detect_platform_from_context(context)

    async with AsyncSessionLocal() as session:
        customer = await reject_customer(session, user_id, platform)

        if not customer:
            await query.edit_message_text("❌ مشتری پیدا نشد!")
            return

        await query.edit_message_text(query.message.text + "\n\n❌ رد شد")

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "❌ متأسفانه درخواست شما تایید نشد.\n"
                    "برای اطلاعات بیشتر با پشتیبانی تماس بگیرید."
                ),
            )
        except Exception as e:
            log.error(f"خطا در ارسال پیام: {e}")