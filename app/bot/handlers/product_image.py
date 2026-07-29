"""
هندلرهای آپلود و مدیریت عکس محصول
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from sqlalchemy import select

from app.database.connection import AsyncSessionLocal
from app.database.models import Product, Platform, CustomerStatus
from app.services.customer_service import get_customer_by_telegram_id
from app.services.product_media_service import (
    set_product_media,
    remove_product_media,
    get_customer_uploaded_media,
)
from app.bot.states.user_state import (
    UserState,
    set_user_state,
    get_user_state,
    get_user_data,
    clear_user_state,
)
from app.utils.logger import log


async def prod_upload_image_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """درخواست آپلود عکس محصول"""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.replace("prod_upload_image_", ""))
    user = query.from_user

    # چک کن محصول مال این مشتریه
    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer or customer.customer_status != CustomerStatus.ACTIVE:
            await query.answer("❌ حساب شما فعال نیست", show_alert=True)
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

    # تنظیم state
    set_user_state(
        user.id,
        UserState.WAITING_PRODUCT_IMAGE,
        data={"product_id": product_id},
    )

    text = (
        f"🖼 آپلود عکس محصول\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📦 محصول: {product.product_name}\n"
        f"🔖 کد: {product.sku}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"لطفاً یک عکس برای این محصول ارسال کنید.\n\n"
        f"⚠️ نکات:\n"
        f"• فقط عکس بفرستید (نه فایل)\n"
        f"• کیفیت خوب رو انتخاب کنید\n"
        f"• عکس فعلی جایگزین میشه (اگه بود)\n"
        f"• این عکس اولویت داره نسبت به لینک اکسل\n\n"
        f"💡 با ارسال عکس، خودکار ذخیره میشه."
    )

    keyboard = [
        [InlineKeyboardButton("❌ انصراف", callback_data=f"prod_view_{product_id}")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def prod_remove_image_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """حذف عکس آپلود شده"""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.replace("prod_remove_image_", ""))
    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            return

        # چک محصول
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

        # حذف همه عکس‌های آپلود شده (همه پلتفرم‌ها)
        count = await remove_product_media(session, product_id)

    await query.answer(f"✅ عکس حذف شد ({count} پلتفرم)", show_alert=True)

    # نمایش مجدد جزئیات
    await _show_product_view_after_change(query, product_id, user.id)


async def product_image_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    دریافت عکس از مشتری برای محصول
    فقط وقتی state = WAITING_PRODUCT_IMAGE
    """
    user = update.effective_user

    if get_user_state(user.id) != UserState.WAITING_PRODUCT_IMAGE:
        return

    user_data = get_user_data(user.id)
    product_id = user_data.get("product_id")

    if not product_id:
        await update.message.reply_text("❌ خطا! لطفاً از اول شروع کنید.")
        clear_user_state(user.id)
        return

    # چک کن عکس ارسال شده
    if not update.message.photo:
        await update.message.reply_text(
            "⚠️ لطفاً یک عکس ارسال کنید (نه متن یا فایل)."
        )
        return

    # گرفتن file_id بزرگترین سایز
    photo = update.message.photo[-1]
    file_id = photo.file_id

    log.info(f"📷 عکس دریافت شد برای محصول {product_id}: file_id={file_id[:30]}...")

    # ذخیره در دیتابیس
    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            await update.message.reply_text("❌ خطا!")
            clear_user_state(user.id)
            return

        # چک محصول
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

        # ذخیره برای تلگرام
        await set_product_media(
            session=session,
            product_id=product_id,
            platform=Platform.TELEGRAM,
            file_id=file_id,
            uploaded_by_customer=True,
        )

    clear_user_state(user.id)

    await update.message.reply_text(
        f"✅ عکس با موفقیت ذخیره شد!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📦 محصول: {product.product_name}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"🎯 این عکس:\n"
        f"├── اولویت داره نسبت به لینک اکسل/شیت\n"
        f"├── همیشه از این استفاده میشه\n"
        f"└── تا وقتی که حذف نکنید یا عکس جدید نذارید\n\n"
        f"💡 نتیجه رو ببینید:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👁 پیش‌نمایش پست", callback_data=f"prod_preview_{product_id}")],
            [InlineKeyboardButton("📤 ارسال به کانال", callback_data=f"prod_publish_{product_id}")],
            [InlineKeyboardButton("🔙 بازگشت به محصول", callback_data=f"prod_view_{product_id}")],
        ]),
    )


async def _show_product_view_after_change(query, product_id: int, telegram_user_id: int) -> None:
    """نمایش مجدد جزئیات محصول بعد از تغییر عکس"""
    from app.bot.handlers.product import _show_product_detail

    try:
        await _show_product_detail(query, product_id, telegram_user_id)
    except Exception as e:
        log.error(f"خطا در نمایش مجدد: {e}")
        # اگه تابع نبود، پیام ساده
        await query.edit_message_text(
            "✅ تغییرات اعمال شد.\n\n"
            "برای مشاهده به منوی '📦 مدیریت محصولات' برید."
        )