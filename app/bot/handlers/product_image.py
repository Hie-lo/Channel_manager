"""
هندلرهای آپلود و مدیریت عکس محصول (چند عکس)
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from sqlalchemy import select

from app.database.connection import AsyncSessionLocal
from app.database.models import Product, Platform, CustomerStatus
from app.services.customer_service import get_customer_by_telegram_id
from app.services.product_media_service import (
    add_product_media,
    remove_all_product_media,
    get_product_medias,
    count_product_medias,
    MAX_PHOTOS_PER_PRODUCT,
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

        # شمارش عکس‌های فعلی
        current_count = await count_product_medias(session, product_id)

    remaining = MAX_PHOTOS_PER_PRODUCT - current_count

    if remaining <= 0:
        await query.edit_message_text(
            f"⚠️ به حداکثر تعداد عکس رسیدید!\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📷 تعداد فعلی: {current_count}\n"
            f"📊 حداکثر مجاز: {MAX_PHOTOS_PER_PRODUCT}\n\n"
            f"💡 برای اضافه کردن عکس جدید، اول باید همه رو حذف کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data=f"prod_view_{product_id}")]
            ]),
        )
        return

    # تنظیم state
    set_user_state(
        user.id,
        UserState.WAITING_PRODUCT_IMAGE,
        data={"product_id": product_id, "uploaded_count": 0},
    )

    text = (
        f"🖼 آپلود عکس محصول\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📦 محصول: {product.product_name}\n"
        f"🔖 کد: {product.sku}\n"
        f"📷 عکس‌های فعلی: {current_count}\n"
        f"📊 حداکثر مجاز: {MAX_PHOTOS_PER_PRODUCT}\n"
        f"➕ می‌تونید {remaining} عکس دیگه اضافه کنید\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"لطفاً عکس‌های محصول رو ارسال کنید.\n\n"
        f"💡 نکات:\n"
        f"• هر عکس رو جداگانه بفرستید\n"
        f"• یا چند عکس رو یکجا (آلبوم) بفرستید\n"
        f"• عکس‌ها به ترتیب ارسال ذخیره میشن\n"
        f"• برای پایان، دکمه '✅ اتمام' رو بزنید"
    )

    keyboard = [
        [InlineKeyboardButton("✅ اتمام آپلود", callback_data=f"prod_finish_upload_{product_id}")],
        [InlineKeyboardButton("❌ انصراف", callback_data=f"prod_view_{product_id}")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def prod_finish_upload_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پایان آپلود عکس‌ها"""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.replace("prod_finish_upload_", ""))
    user = query.from_user

    user_data = get_user_data(user.id)
    uploaded_count = user_data.get("uploaded_count", 0)

    clear_user_state(user.id)

    async with AsyncSessionLocal() as session:
        total_count = await count_product_medias(session, product_id)

    text = (
        f"✅ آپلود عکس تمام شد!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📷 عکس‌های اضافه شده: {uploaded_count}\n"
        f"📊 مجموع عکس‌های محصول: {total_count}\n"
        f"━━━━━━━━━━━━━━━\n\n"
    )

    if uploaded_count > 0:
        text += (
            f"🎯 این عکس‌ها به صورت آلبوم در کانال ارسال میشن.\n\n"
            f"💡 نتیجه رو ببینید:"
        )
    else:
        text += "هیچ عکسی اضافه نشد."

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👁 پیش‌نمایش پست", callback_data=f"prod_preview_{product_id}")],
            [InlineKeyboardButton("📤 ارسال به کانال", callback_data=f"prod_publish_{product_id}")],
            [InlineKeyboardButton("🔙 بازگشت به محصول", callback_data=f"prod_view_{product_id}")],
        ]),
    )


async def prod_remove_image_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """حذف همه عکس‌های آپلود شده"""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.replace("prod_remove_image_", ""))
    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
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

        count = await remove_all_product_media(session, product_id)

    await query.answer(f"✅ {count} عکس حذف شد", show_alert=True)

    from app.bot.handlers.product import _show_product_detail
    await _show_product_detail(query, product_id, user.id)


async def product_image_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    دریافت عکس از مشتری برای محصول (چند عکس)
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

    if not update.message.photo:
        await update.message.reply_text("⚠️ لطفاً عکس بفرستید.")
        return

    # گرفتن بزرگترین سایز
    photo = update.message.photo[-1]
    file_id = photo.file_id

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            await update.message.reply_text("❌ خطا!")
            clear_user_state(user.id)
            return

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

        # اضافه کردن عکس
        media = await add_product_media(
            session=session,
            product_id=product_id,
            file_id=file_id,
            platform=Platform.TELEGRAM,
            uploaded_by_customer=True,
        )

        if not media:
            await update.message.reply_text(
                f"⚠️ به حداکثر تعداد عکس ({MAX_PHOTOS_PER_PRODUCT}) رسیدید!\n"
                f"دکمه '✅ اتمام آپلود' رو بزنید."
            )
            return

        total_count = await count_product_medias(session, product_id)

    # آپدیت شمارش در state
    uploaded_count = user_data.get("uploaded_count", 0) + 1
    set_user_state(
        user.id,
        UserState.WAITING_PRODUCT_IMAGE,
        data={"product_id": product_id, "uploaded_count": uploaded_count},
    )

    remaining = MAX_PHOTOS_PER_PRODUCT - total_count

    if remaining > 0:
        response = (
            f"✅ عکس {uploaded_count} ذخیره شد!\n"
            f"📊 مجموع عکس‌ها: {total_count}/{MAX_PHOTOS_PER_PRODUCT}\n"
            f"➕ می‌تونید {remaining} عکس دیگه اضافه کنید.\n\n"
            f"عکس بعدی رو بفرستید یا دکمه '✅ اتمام آپلود' رو بزنید."
        )
    else:
        response = (
            f"✅ عکس {uploaded_count} ذخیره شد!\n"
            f"📊 به حداکثر تعداد رسیدید ({MAX_PHOTOS_PER_PRODUCT}).\n\n"
            f"دکمه '✅ اتمام آپلود' رو بزنید."
        )

    await update.message.reply_text(response)