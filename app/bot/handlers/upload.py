"""
هندلرهای آپلود محصولات
"""

import os
import tempfile
from pathlib import Path

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from app.database.connection import AsyncSessionLocal
from app.database.models import CustomerStatus
from app.services.customer_service import get_customer_by_telegram_id
from app.services.business_service import (
    get_business_config_for_customer,
    get_business_for_customer,
    get_excel_template_path,
)
from app.services.subscription.service import get_active_subscription
from app.services.subscription.plans import get_plan
from app.services.data_input.excel_reader import read_excel_file
from app.services.product_service import save_products_from_excel
from app.bot.states.user_state import (
    UserState,
    set_user_state,
    get_user_state,
    clear_user_state,
)
from app.utils.logger import log


def get_upload_menu_keyboard() -> InlineKeyboardMarkup:
    """منوی آپلود محصولات"""
    keyboard = [
        [InlineKeyboardButton("📥 دانلود فایل نمونه", callback_data="upload_download_template")],
        [InlineKeyboardButton("📤 ارسال فایل اکسل", callback_data="upload_send_excel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_cancel_upload_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("❌ لغو", callback_data="upload_cancel")]
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

        plan = get_plan(subscription.plan_key)

    await update.message.reply_text(
        f"📤 آپلود محصولات\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🏢 کسب‌وکار: {business_config.emoji} {business_config.name_fa}\n"
        f"📦 حداکثر محصول: {plan.max_products if plan.max_products < 9999 else 'نامحدود'}\n"
        f"━━━━━━━━━━━━━━━\n\n"
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

    template_path = get_excel_template_path(business_config.key)

    if not template_path:
        await query.message.reply_text("❌ فایل نمونه پیدا نشد!")
        return

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
                    f"• موجودی: عدد صحیح (0 = ناموجود)"
                ),
            )
    except Exception as e:
        log.error(f"خطا در ارسال فایل نمونه: {e}")


async def upload_send_excel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """درخواست ارسال فایل اکسل"""

    query = update.callback_query
    await query.answer()

    user = query.from_user

    # تنظیم state
    set_user_state(user.id, UserState.WAITING_EXCEL_FILE)

    await query.edit_message_text(
        "📤 ارسال فایل اکسل\n"
        "━━━━━━━━━━━━━━━\n\n"
        "لطفاً فایل اکسل (.xlsx) خودتون رو ارسال کنید.\n\n"
        "⚠️ نکته:\n"
        "• فقط فرمت .xlsx پذیرفته میشه\n"
        "• حجم فایل نباید بیش از ۱۰ مگابایت باشه\n"
        "• حتماً از ساختار فایل نمونه استفاده کنید",
        reply_markup=get_cancel_upload_keyboard(),
    )


async def upload_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """لغو آپلود"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    clear_user_state(user.id)

    await query.edit_message_text(
        "❌ آپلود لغو شد.\n\n"
        "هر وقت خواستید از منوی '📤 آپلود محصولات' دوباره شروع کنید."
    )


async def excel_file_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    دریافت و پردازش فایل اکسل
    این handler فقط زمانی فعال میشه که state = WAITING_EXCEL_FILE باشه
    """
    user = update.effective_user

    if get_user_state(user.id) != UserState.WAITING_EXCEL_FILE:
        return

    document = update.message.document

    # چک نوع فایل
    if not document:
        await update.message.reply_text(
            "❌ لطفاً یک فایل اکسل ارسال کنید (نه عکس یا متن)"
        )
        return

    file_name = document.file_name or ""
    if not file_name.lower().endswith(('.xlsx', '.xls')):
        await update.message.reply_text(
            "❌ فرمت فایل نامعتبر است!\n"
            "لطفاً فایل با فرمت .xlsx ارسال کنید."
        )
        return

    # چک حجم فایل (حداکثر ۱۰ مگابایت)
    if document.file_size > 10 * 1024 * 1024:
        await update.message.reply_text(
            "❌ حجم فایل بیش از حد است!\n"
            "حداکثر حجم مجاز: ۱۰ مگابایت"
        )
        return

    processing_msg = await update.message.reply_text(
        "🔄 در حال دریافت فایل...\n"
        "لطفاً چند لحظه صبر کنید."
    )

    # دانلود فایل
    temp_file_path = None
    try:
        telegram_file = await context.bot.get_file(document.file_id)

        # ساخت فایل موقت
        with tempfile.NamedTemporaryFile(
            suffix='.xlsx',
            delete=False,
        ) as temp_file:
            temp_file_path = temp_file.name

        await telegram_file.download_to_drive(temp_file_path)

        await processing_msg.edit_text("🔄 در حال پردازش فایل...")

        # پردازش فایل
        async with AsyncSessionLocal() as session:
            customer = await get_customer_by_telegram_id(session, user.id)
            if not customer:
                await processing_msg.edit_text("❌ خطا!")
                return

            business_config = get_business_config_for_customer(customer)
            if not business_config:
                await processing_msg.edit_text("❌ کسب‌وکار تنظیم نشده!")
                return

            # خواندن فایل
            read_result = read_excel_file(temp_file_path, business_config)

           # چک اگه فقط خطا داشت (هیچ محصول معتبری نداشت)
            if read_result.is_empty and read_result.has_errors:
                error_text = _format_errors(read_result.errors)
                await processing_msg.edit_text(
                    f"❌ فایل قابل پردازش نیست!\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"{error_text}"
                )
                clear_user_state(user.id)
                return

            # چک اگه واقعاً خالی بود
            if read_result.is_empty:
                await processing_msg.edit_text(
                    "❌ فایل خالی است!\n"
                    "لطفاً محصولات را در فایل وارد کنید."
                )
                clear_user_state(user.id)
                return

            # گرفتن اشتراک برای محدودیت
            subscription = await get_active_subscription(session, customer.id)
            plan = get_plan(subscription.plan_key)

            # گرفتن business
            business = await get_business_for_customer(session, customer.id)
            business_id = business.id if business else None

            # ذخیره محصولات
            await processing_msg.edit_text("💾 در حال ذخیره محصولات...")

            save_result = await save_products_from_excel(
                session=session,
                customer_id=customer.id,
                business_id=business_id,
                products_data=read_result.products,
                max_products_limit=plan.max_products,
            )

        # نمایش خلاصه
        summary_text = _format_summary(
            read_result=read_result,
            save_result=save_result,
        )

        await processing_msg.edit_text(summary_text)

        # اگر محصولات ذخیره شدند، پیشنهاد پیش‌نمایش پست
        if save_result.new_count + save_result.updated_count > 0:
            await update.message.reply_text(
                "🎉 محصولات با موفقیت ذخیره شدند!\n\n"
                "برای مشاهده لیست محصولات، از منوی '📦 مدیریت محصولات' استفاده کنید.\n\n"
                "برای انتشار در کانال، این قابلیت به زودی اضافه می‌شود!"
            )

        clear_user_state(user.id)

    except Exception as e:
        log.error(f"خطا در پردازش فایل اکسل: {e}", exc_info=True)
        await processing_msg.edit_text(
            f"❌ خطا در پردازش فایل!\n"
            f"لطفاً دوباره تلاش کنید.\n\n"
            f"جزئیات: {str(e)[:200]}"
        )
        clear_user_state(user.id)

    finally:
        # پاک کردن فایل موقت
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                log.error(f"خطا در حذف فایل موقت: {e}")


def _format_errors(errors: list) -> str:
    """فرمت کردن خطاها برای نمایش"""
    if not errors:
        return "بدون خطا"

    lines = []
    for err in errors[:10]:  # حداکثر ۱۰ خطای اول
        if err.row_number == 0:
            lines.append(f"• {err.message}")
        else:
            lines.append(f"• ردیف {err.row_number}: {err.message}")

    if len(errors) > 10:
        lines.append(f"... و {len(errors) - 10} خطای دیگر")

    return "\n".join(lines)


def _format_summary(read_result, save_result) -> str:
    """فرمت کردن خلاصه نتیجه"""

    # محاسبه تعداد خطای واقعی
    total_errors = len(read_result.errors) + save_result.error_count

    text = (
        f"✅ پردازش کامل شد!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📊 خلاصه فایل:\n"
        f"├── کل ردیف‌ها: {read_result.total_rows}\n"
        f"├── ردیف‌های معتبر: {read_result.valid_rows}\n"
        f"└── ردیف‌های خطادار: {len(read_result.errors)}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💾 نتیجه ذخیره:\n"
        f"├── 🆕 محصولات جدید: {save_result.new_count}\n"
        f"├── 🔄 آپدیت شده: {save_result.updated_count}\n"
        f"├── ✅ بدون تغییر: {save_result.unchanged_count}\n"
        f"└── ❌ خطا در ذخیره: {save_result.error_count}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📌 مجموع خطاها: {total_errors}"
    )

    if read_result.errors:
        text += f"\n\n⚠️ خطاهای فایل:\n{_format_errors(read_result.errors)}"

    if save_result.errors:
        text += f"\n\n⚠️ خطاهای ذخیره:\n"
        for err in save_result.errors[:5]:
            text += f"• {err}\n"

    return text