"""
هندلر دستور /start
اولین تعامل کاربر با ربات
"""

from telegram import Update
from telegram.ext import ContextTypes
from app.config import settings
from app.database.connection import AsyncSessionLocal
from app.services.customer_service import (
    get_customer_by_telegram_id,
    create_customer,
)
from app.database.models import CustomerStatus
from app.bot.keyboards.main_menu import (
    get_customer_main_menu,
    get_business_type_keyboard,
)
from app.bot.keyboards.admin import get_admin_main_menu  
from app.utils.logger import log


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندلر دستور /start"""

    user = update.effective_user
    telegram_id = user.id

    log.info(f"دستور /start از کاربر: {telegram_id} - {user.first_name}")

    # چک کن آیا سوپر ادمین است
    if telegram_id == settings.ADMIN_CHAT_ID:
        await update.message.reply_text(
            f"👑 سلام ادمین عزیز!\n"
            f"به پنل مدیریت خوش آمدید.",
            reply_markup=get_admin_main_menu(),
        )
        return

    # بررسی وضعیت مشتری در دیتابیس
    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, telegram_id)

        # مشتری جدید است
        if not customer:
            await _handle_new_customer(update, context, session, user)
            return

        # مشتری قبلاً ثبت‌نام کرده - بررسی وضعیت
        if customer.customer_status == CustomerStatus.PENDING:
            await update.message.reply_text(
                "⏳ حساب شما در انتظار تایید است.\n"
                "پس از تایید توسط ادمین پیام دریافت خواهید کرد."
            )

        elif customer.customer_status == CustomerStatus.ACTIVE:
            await update.message.reply_text(
                f"سلام {user.first_name} عزیز! 👋\n"
                f"خوش برگشتید.",
                reply_markup=get_customer_main_menu(),
            )

        elif customer.customer_status == CustomerStatus.REJECTED:
            await update.message.reply_text(
                "❌ متأسفانه درخواست شما تایید نشد.\n"
                "برای اطلاعات بیشتر با پشتیبانی تماس بگیرید."
            )

        elif customer.customer_status == CustomerStatus.SUSPENDED:
            await update.message.reply_text(
                "⛔ حساب شما معلق شده است.\n"
                "برای فعال‌سازی مجدد با پشتیبانی تماس بگیرید."
            )


async def _handle_new_customer(update, context, session, user) -> None:
    """مدیریت مشتری جدید - ثبت‌نام"""

    # ساخت مشتری در دیتابیس با وضعیت PENDING
    await create_customer(
        session=session,
        telegram_user_id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
    )

    # درخواست نام کسب‌وکار
    await update.message.reply_text(
        f"👋 سلام {user.first_name} عزیز!\n\n"
        f"به ربات مدیریت کانال خوش آمدید.\n\n"
        f"برای شروع، لطفاً نوع کسب‌وکار خود را انتخاب کنید:",
        reply_markup=get_business_type_keyboard(),
    )