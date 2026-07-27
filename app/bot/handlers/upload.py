"""
هندلرهای آپلود محصولات
فعلاً فقط دانلود فایل نمونه رو داریم
پردازش اکسل در قدم بعدی اضافه میشه
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from app.database.connection import AsyncSessionLocal
from app.database.models import CustomerStatus
from app.services.customer_service import get_customer_by_telegram_id
from app.services.business_service import (
    get_business_config_for_customer,
    get_excel_template_path,
)
from app.services.subscription.service import get_active_subscription
from app.utils.logger import log


def get_upload_menu_keyboard() -> InlineKeyboardMarkup:
    """منوی آپلود محصولات"""
    keyboard = [
        [InlineKeyboardButton("📥 دانلود فایل نمونه", callback_data="upload_download_template")],
        [InlineKeyboardButton("📤 ارسال فایل اکسل", callback_data="upload_send_excel")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def upload_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش منوی آپلود محصولات"""

    user = update.effective_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)

        if not customer or customer.customer_status != CustomerStatus.ACTIVE:
            await update.message.reply_text("❌ حساب شما فعال نیست. /start بزنید.")
            return

        # چک اشتراک
        subscription = await get_active_subscription(session, customer.id)
        if not subscription:
            await update.message.reply_text(
                "❌ اشتراک فعالی ندارید!\n\n"
                "برای استفاده از این بخش، از منوی '💳 اشتراک من' یک پلن خریداری کنید."
            )
            return

        business_config = get_business_config_for_customer(customer)
        if not business_config:
            await update.message.reply_text("❌ کسب‌وکار شما تنظیم نشده!")
            return

    await update.message.reply_text(
        f"📤 آپلود محصولات\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🏢 کسب‌وکار: {business_config.emoji} {business_config.name_fa}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"چطور می‌خواهید محصولات را اضافه کنید؟\n\n"
        f"💡 پیشنهاد: ابتدا فایل نمونه را دانلود کنید،\n"
        f"محصولات خود را در آن وارد کنید،\n"
        f"سپس فایل را ارسال کنید.",
        reply_markup=get_upload_menu_keyboard(),
    )


async def upload_download_template_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ارسال فایل نمونه اکسل به مشتری"""

    query = update.callback_query
    await query.answer()

    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            return

        business_config = get_business_config_for_customer(customer)
        if not business_config:
            await query.message.reply_text("❌ کسب‌وکار شما تنظیم نشده!")
            return

    # پیدا کردن فایل نمونه
    template_path = get_excel_template_path(business_config.key)

    if not template_path:
        await query.message.reply_text(
            "❌ فایل نمونه پیدا نشد!\n"
            "لطفاً به ادمین اطلاع دهید."
        )
        log.error(f"فایل نمونه پیدا نشد: {business_config.key}")
        return

    # ارسال فایل
    try:
        with open(template_path, "rb") as f:
            await context.bot.send_document(
                chat_id=user.id,
                document=f,
                filename=f"{business_config.key}_template.xlsx",
                caption=(
                    f"📥 فایل نمونه محصولات\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"🏢 کسب‌وکار: {business_config.emoji} {business_config.name_fa}\n"
                    f"━━━━━━━━━━━━━━━\n\n"
                    f"📋 راهنما:\n"
                    f"1️⃣ فایل را دانلود کنید\n"
                    f"2️⃣ محصولات خود را وارد کنید\n"
                    f"3️⃣ ساختار ستون‌ها را تغییر ندید\n"
                    f"4️⃣ فایل را برای ربات ارسال کنید\n\n"
                    f"⚠️ نکات مهم:\n"
                    f"• ستون 'کد محصول' اجباری است\n"
                    f"• قیمت به تومان و فقط عدد باشد\n"
                    f"• موجودی: عدد صحیح (0 = ناموجود)\n"
                    f"• لینک عکس اختیاری است"
                ),
            )
        log.info(f"فایل نمونه ارسال شد: {user.id}")
    except Exception as e:
        log.error(f"خطا در ارسال فایل نمونه: {e}")
        await query.message.reply_text("❌ خطا در ارسال فایل!")


async def upload_send_excel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """راهنمای ارسال فایل اکسل (فعلاً فقط توضیح)"""

    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📤 ارسال فایل اکسل\n"
        "━━━━━━━━━━━━━━━\n\n"
        "⚠️ این قابلیت به زودی فعال می‌شود!\n\n"
        "فعلاً می‌تونید فایل نمونه رو دانلود کنید\n"
        "و محصولاتتون رو در اون وارد کنید."
    )