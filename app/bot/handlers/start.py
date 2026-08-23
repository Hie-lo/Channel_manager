"""
هندلر دستور /start
اولین تعامل کاربر با ربات (تلگرام یا بله)
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.config import settings
from app.database.connection import AsyncSessionLocal
from app.services.customer_service import get_customer_by_platform_id
from app.database.models import CustomerStatus
from app.bot.keyboards.main_menu import (
    get_customer_main_menu,
    get_business_type_keyboard,
)
from app.bot.keyboards.admin import get_admin_main_menu
from app.utils.logger import log
from app.utils.admin_check import (
    is_admin,
    detect_platform_from_context,
)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندلر دستور /start"""

    user = update.effective_user
    user_id = user.id

    # تشخیص پلتفرم
    platform = detect_platform_from_context(context)
    platform_display = "تلگرام" if platform == "TELEGRAM" else "بله"

    log.info(
        f"دستور /start از کاربر: {user_id} - {user.first_name} "
        f"در پلتفرم {platform_display}"
    )

    # چک ادمین
    if is_admin(user_id):
        await update.message.reply_text(
            f"👑 سلام ادمین عزیز!\n"
            f"به پنل مدیریت خوش آمدید.\n"
            f"🤖 پلتفرم: {platform_display}",
            reply_markup=get_admin_main_menu(),
        )
        return

    # بررسی وضعیت مشتری در دیتابیس
    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_platform_id(session, user_id, platform)

        # اگر مشتری وجود ندارد یا هنوز نوع کسب‌وکار خود را انتخاب نکرده است
        if not customer or (customer.customer_status == CustomerStatus.PENDING and not customer.business_type_key):
            await _handle_new_customer(update, context, user, platform)
            return

        # مشتری قبلاً ثبت‌نام کرده و کسب‌وکارش را هم انتخاب کرده است
        if customer.customer_status == CustomerStatus.PENDING:
            # کیبورد کمکی برای حالت انتظار (جلوگیری از بن‌بست)
            pending_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 اتصال به حساب قبلی من", callback_data="link_account_start")],
                [InlineKeyboardButton("💬 ارتباط با پشتیبانی", callback_data="tut_inline_support_help")]
            ])
            
            await update.message.reply_text(
                "⏳ <b>حساب شما در انتظار تایید ادمین است.</b>\n"
                "پس از تایید توسط ادمین، پیام فعال‌سازی برای شما ارسال خواهد شد.\n\n"
                "💡 اگر قبلاً حساب فعال داشته‌اید و می‌خواهید به آن متصل شوید، دکمه زیر را بزنید:",
                parse_mode="HTML",
                reply_markup=pending_keyboard
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


async def _handle_new_customer(update, context, user, platform) -> None:
    """نمایش منوی اولیه ثبت نام / اتصال حساب (بدون ساخت رکورد اجباری در دیتابیس)"""

    log.info(f"[NEW VISITOR] platform={platform}, user_id={user.id}")

    platform_display = "تلگرام" if platform == "TELEGRAM" else "بله"

    # گرفتن کیبورد کسب و کارها
    raw_biz_keyboard = get_business_type_keyboard().inline_keyboard
    biz_keyboard = [list(row) for row in raw_biz_keyboard]

    # دکمه اتصال حساب
    link_button = [InlineKeyboardButton("🔗 اتصال به حساب قبلی من", callback_data="link_account_start")]
    
    combined_keyboard = [link_button] + biz_keyboard
    final_markup = InlineKeyboardMarkup(combined_keyboard)

    await update.message.reply_text(
        f"👋 سلام {user.first_name} عزیز!\n\n"
        f"به ربات مدیریت کانال خوش آمدید.\n"
        f"🤖 پلتفرم: {platform_display}\n\n"
        f"اگر قبلاً در پلتفرم دیگری ثبت‌نام کرده‌اید، دکمه «اتصال به حساب قبلی من» را بزنید.\n\n"
        f"در غیر این صورت، برای ثبت‌نام جدید لطفاً نوع کسب‌وکار خود را انتخاب کنید:",
        reply_markup=final_markup,
    )