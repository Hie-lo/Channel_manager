"""
هندلرهای مربوط به پست‌ساز دستی (ارسال پیام‌های عمومی به تمام کانال‌ها)
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from app.database.connection import AsyncSessionLocal
from app.database.models import CustomerStatus, Platform
from app.services.customer_service import get_customer_by_telegram_id
from app.services.channel_service import get_customer_channels
from app.services.subscription.service import get_active_subscription
from app.bot.states.user_state import (
    UserState,
    set_user_state,
    get_user_state,
    get_user_data,
    clear_user_state,
)
from app.utils.logger import log


async def custom_post_start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """شروع فرآیند پست‌ساز دستی"""
    user = update.effective_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)

        if not customer or customer.customer_status != CustomerStatus.ACTIVE:
            await update.message.reply_text("❌ حساب شما فعال نیست.")
            return

        subscription = await get_active_subscription(session, customer.id)
        if not subscription:
            await update.message.reply_text("❌ شما اشتراک فعالی ندارید. لطفاً ابتدا اشتراک تهیه کنید.")
            return

        channels = await get_customer_channels(session, customer.id, only_active=True)
        if not channels:
            await update.message.reply_text("❌ هیچ کانال فعالی برای ارسال پست پیدا نشد. ابتدا کانال متصل کنید.")
            return

    # تنظیم حالت انتظار برای متن
    set_user_state(user.id, UserState.WAITING_CUSTOM_POST_TEXT)

    text = (
        "📝 <b>پست‌ساز دستی</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
        "با این بخش می‌توانید پیام‌های عمومی (اعلاعیه‌ها، تخفیف‌ها، تبریک‌ها) را به تمام کانال‌های خود بفرستید.\n\n"
        "✍️ <b>لطفاً متن پست خود را ارسال کنید:</b>"
    )

    keyboard = [[InlineKeyboardButton("❌ انصراف", callback_data="custom_post_cancel")]]
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def custom_post_text_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دریافت متن پست از کاربر"""
    user = update.effective_user
    post_text = update.message.text.strip()

    if get_user_state(user.id) != UserState.WAITING_CUSTOM_POST_TEXT:
        return

    # ذخیره متن در داده‌های موقت
    set_user_state(user.id, UserState.WAITING_CUSTOM_POST_PHOTOS, data={"text": post_text, "photos": []})

    text = (
        "✅ <b>متن پست دریافت شد.</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
        "آیا می‌خواهید به این پست عکس اضافه کنید؟\n\n"
        "💡 می‌توانید ۱ یا چند عکس ارسال کنید یا مستقیماً بدون عکس ارسال کنید."
    )

    keyboard = [
        [InlineKeyboardButton("🚀 پیش‌نمایش و ارسال بدون عکس", callback_data="custom_post_preview")],
        [InlineKeyboardButton("❌ انصراف", callback_data="custom_post_cancel")]
    ]

    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def custom_post_photo_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دریافت عکس/عکس‌ها از کاربر برای پست سفارشی"""
    user = update.effective_user
    state = get_user_state(user.id)

    if state != UserState.WAITING_CUSTOM_POST_PHOTOS:
        return

    photo_file_id = None
    if update.message.photo:
        photo_file_id = update.message.photo[-1].file_id
    elif update.message.document and update.message.document.mime_type.startswith("image/"):
        photo_file_id = update.message.document.file_id

    if not photo_file_id:
        await update.message.reply_text("⚠️ لطفاً فقط عکس ارسال کنید.")
        return

    user_data = get_user_data(user.id)
    photos = user_data.get("photos", [])
    photos.append(photo_file_id)

    # آپدیت داده‌ها
    set_user_state(user.id, UserState.WAITING_CUSTOM_POST_PHOTOS, data={"photos": photos})

    text = (
        f"✅ <b>عکس دریافت شد ({len(photos)} عکس ثبت شده).</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"می‌توانید عکس‌های بیشتری بفرستید یا جهت پیش‌نمایش کلیک کنید:"
    )

    keyboard = [
        [InlineKeyboardButton("👁 پیش‌نمایش و ادامه", callback_data="custom_post_preview")],
        [InlineKeyboardButton("❌ انصراف", callback_data="custom_post_cancel")]
    ]

    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def custom_post_preview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش پیش‌نمایش پست سفارشی قبل از ارسال نهایی"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_data = get_user_data(user.id)

    post_text = user_data.get("text", "")
    photos = user_data.get("photos", [])

    if not post_text:
        await query.edit_message_text("❌ خطایی رخ داد. متن پست پیدا نشد.")
        clear_user_state(user.id)
        return

    set_user_state(user.id, UserState.VIEWING_CUSTOM_POST_PREVIEW)

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        channels = await get_customer_channels(session, customer.id, only_active=True)

    channels_summary = "\n".join([f"• {c.platform.value}: {c.channel_identifier}" for c in channels])

    preview_msg = (
        f"👁 <b>پیش‌نمایش پست سفارشی</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"{post_text}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📷 تعداد عکس‌ها: {len(photos)}\n"
        f"📢 ارسال به کانال‌های زیر:\n"
        f"{channels_summary}\n\n"
        f"آیا برای ارسال اطمینان دارید؟"
    )

    keyboard = [
        [InlineKeyboardButton("🚀 تایید و ارسال به تمام کانال‌ها", callback_data="custom_post_send_confirm")],
        [InlineKeyboardButton("❌ انصراف", callback_data="custom_post_cancel")]
    ]

    await query.edit_message_text(preview_msg, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def custom_post_send_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ارسال نهایی پست سفارشی به تمامی کانال‌ها"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_data = get_user_data(user.id)

    post_text = user_data.get("text", "")
    photos = user_data.get("photos", [])

    clear_user_state(user.id)
    await query.edit_message_text("⏳ در حال ارسال پست به کانال‌ها...")

    async with AsyncSessionLocal() as session:
        from app.services.customer_service import get_customer_by_platform_id
        from app.utils.admin_check import detect_platform_from_context
        
        platform = detect_platform_from_context(context)
        customer = await get_customer_by_platform_id(session, user.id, platform)
        
        if not customer:
            await query.edit_message_text("❌ مشتری یافت نشد.")
            return

        channels = await get_customer_channels(session, customer.id, only_active=True)

        eitaa_token = None
        if any(c.platform == Platform.EITAA for c in channels):
            from app.services.customer_service import get_customer_eitaa_token
            eitaa_token = await get_customer_eitaa_token(session, customer.id)

    # ساخت یک Dummy Product موقت فقط جهت استفاده از لایه Publisher Manager موجود
    from app.database.models import Product
    dummy_prod = Product(product_name="پست سفارشی", price=0, stock_qty=1, is_available=True, sku="CUSTOM")
    if photos:
        # برای لایه Manager، کافیست image_url را تنظیم کنیم
        # چون در حالت پست سفارشی، photos در واقع list of file_ids هستند.
        dummy_prod.image_url = photos[0]

    from app.services.publisher.publisher_manager import publish_to_channel
    import asyncio

    success_count = 0
    fail_count = 0

    for ch in channels:
        try:
            # 💡 جادوی معماری: publish_to_channel خودش تشخیص می‌دهد اگر در بله هستیم
            # و می‌خواهیم به تلگرام بفرستیم، یک Temporary Telegram Bot بسازد.
            res = await publish_to_channel(
                bot=context.bot,
                channel=ch,
                product=dummy_prod,
                caption=post_text,
                eitaa_token=eitaa_token
            )
            
            if res.success: 
                success_count += 1
            else: 
                fail_count += 1
                log.error(f"❌ ارسال پست سفارشی به {ch.channel_identifier} ناموفق: {res.error_message}")
                
            await asyncio.sleep(1) # تاخیر برای Rate Limit

        except Exception as e:
            log.error(f"خطا در ارسال پست سفارشی به {ch.channel_identifier}: {e}", exc_info=True)
            fail_count += 1

    result_text = (
        f"✅ <b>عملیات ارسال نهایی شد!</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"✅ ارسال موفق: {success_count}\n"
        f"❌ ارسال ناموفق: {fail_count}"
    )

    await query.edit_message_text(result_text, parse_mode="HTML")


async def custom_post_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """انصراف از پست‌ساز دستی"""
    query = update.callback_query
    await query.answer()

    clear_user_state(query.from_user.id)
    await query.edit_message_text("❌ ارسال پست سفارشی لغو شد.")