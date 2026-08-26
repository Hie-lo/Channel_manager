"""
هندلرهای مربوط به پست‌ساز دستی (ارسال پیام‌های عمومی به تمام کانال‌ها + پشتیبانی از مدیا)
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

    set_user_state(user.id, UserState.WAITING_CUSTOM_POST_TEXT)

    text = (
        "📝 <b>پست‌ساز دستی</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
        "با این بخش می‌توانید پیام‌های عمومی (اطلاعیه‌ها، تخفیف‌ها، تبریک‌ها) را به تمام کانال‌های خود بفرستید.\n\n"
        "✍️ <b>لطفاً متن پست خود را ارسال کنید:</b>"
    )

    keyboard = [[InlineKeyboardButton("❌ انصراف", callback_data="custom_post_cancel")]]
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def custom_post_text_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دریافت متن پست از کاربر"""
    user = update.effective_user
    post_text = update.message.text.strip() if update.message.text else ""

    if get_user_state(user.id) != UserState.WAITING_CUSTOM_POST_TEXT:
        return
        
    if not post_text:
        await update.message.reply_text("⚠️ لطفاً فقط متن ارسال کنید.")
        return

    # ذخیره متن در داده‌های موقت و تغییر به حالت انتظار برای مدیا (عکس/ویدیو)
    set_user_state(user.id, UserState.WAITING_CUSTOM_POST_PHOTOS, data={"text": post_text, "media": []})

    text = (
        "✅ <b>متن پست دریافت شد.</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
        "آیا می‌خواهید به این پست عکس یا ویدیو اضافه کنید؟\n\n"
        "💡 می‌توانید ۱ یا چند مدیا (عکس/ویدیو) ارسال کنید یا مستقیماً بدون مدیا ارسال کنید."
    )

    keyboard = [
        [InlineKeyboardButton("🚀 پیش‌نمایش و ارسال بدون مدیا", callback_data="custom_post_preview")],
        [InlineKeyboardButton("❌ انصراف", callback_data="custom_post_cancel")]
    ]

    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def custom_post_photo_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دریافت عکس/ویدیو از کاربر برای پست سفارشی"""
    user = update.effective_user
    state = get_user_state(user.id)

    if state != UserState.WAITING_CUSTOM_POST_PHOTOS:
        return

    media_file_id = None
    media_type = "photo"

    if update.message.photo:
        media_file_id = update.message.photo[-1].file_id
    elif update.message.video:
        media_file_id = update.message.video.file_id
        media_type = "video"
    elif update.message.document and update.message.document.mime_type.startswith("image/"):
        media_file_id = update.message.document.file_id

    if not media_file_id:
        await update.message.reply_text("⚠️ لطفاً فقط عکس یا ویدیو ارسال کنید.")
        return

    user_data = get_user_data(user.id)
    medias = user_data.get("media", [])
    
    # ذخیره فایل همراه با نوع آن
    medias.append({"file_id": media_file_id, "type": media_type})
    set_user_state(user.id, UserState.WAITING_CUSTOM_POST_PHOTOS, data={"media": medias})

    text = (
        f"✅ <b>فایل دریافت شد ({len(medias)} مدیا ثبت شده).</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"می‌توانید عکس/ویدیوی بیشتری بفرستید یا جهت پیش‌نمایش کلیک کنید:"
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
    medias = user_data.get("media", [])

    if not post_text:
        # پاک کردن با حذف پیام و ارسال پیام جدید در صورت خطا
        try:
            await query.message.delete()
        except:
            pass
        await context.bot.send_message(chat_id=user.id, text="❌ خطایی رخ داد. متن پست پیدا نشد.")
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
        f"📷 تعداد مدیا: {len(medias)}\n"
        f"📢 ارسال به کانال‌های زیر:\n"
        f"{channels_summary}\n\n"
        f"آیا برای ارسال اطمینان دارید؟"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 تایید و ارسال به تمام کانال‌ها", callback_data="custom_post_send_confirm")],
        [InlineKeyboardButton("❌ انصراف", callback_data="custom_post_cancel")]
    ])

    try:
        await query.message.delete()
    except Exception:
        pass

    try:
        if not medias:
            # حالت متنی
            await context.bot.send_message(
                chat_id=user.id,
                text=preview_msg,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        elif len(medias) == 1:
            # حالت تک مدیا (عکس یا ویدیو)
            media = medias[0]
            if media["type"] == "video":
                await context.bot.send_video(
                    chat_id=user.id,
                    video=media["file_id"],
                    caption=preview_msg,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            else:
                await context.bot.send_photo(
                    chat_id=user.id,
                    photo=media["file_id"],
                    caption=preview_msg,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
        else:
            # حالت آلبوم (ترکیب عکس و ویدیو)
            from telegram import InputMediaPhoto, InputMediaVideo
            media_group = []
            
            # تلگرام محدودیت کپشن 1024 کاراکتری دارد، پس کوتاه می‌کنیم
            short_preview = preview_msg[:1024-3] + "..." if len(preview_msg) > 1024 else preview_msg
            
            for i, m in enumerate(medias[:10]):
                caption_to_use = short_preview if i == 0 else None
                if m["type"] == "video":
                    media_group.append(InputMediaVideo(media=m["file_id"], caption=caption_to_use, parse_mode="HTML"))
                else:
                    media_group.append(InputMediaPhoto(media=m["file_id"], caption=caption_to_use, parse_mode="HTML"))
            
            await context.bot.send_media_group(chat_id=user.id, media=media_group)
            
            await context.bot.send_message(
                chat_id=user.id,
                text="👆 <b>پیش‌نمایش آلبوم شما</b>\nجهت تایید یا انصراف از دکمه‌های زیر استفاده کنید:",
                parse_mode="HTML",
                reply_markup=keyboard
            )
    except Exception as e:
        log.error(f"خطا در پیش‌نمایش مدیا سفارشی: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=user.id,
            text=f"⚠️ فایل‌ها برای پیش‌نمایش بارگیری نشدند.\n\n{preview_msg}",
            parse_mode="HTML",
            reply_markup=keyboard
        )


async def custom_post_send_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ارسال نهایی پست سفارشی به تمامی کانال‌ها"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_data = get_user_data(user.id)

    post_text = user_data.get("text", "")
    medias = user_data.get("media", [])

    clear_user_state(user.id)
    
    # 🛠 رفع خطای There is no text in message to edit
    try:
        # همیشه پیام قبلی (که حاوی کیبورد و دکمه‌ها بود) را پاک می‌کنیم
        await query.message.delete()
    except Exception:
        pass
        
    # یک پیام متنی جدید برای نشان دادن وضعیت ارسال می‌فرستیم
    progress_msg = await context.bot.send_message(
        chat_id=user.id, 
        text="⏳ در حال ارسال پست به کانال‌ها..."
    )

    async with AsyncSessionLocal() as session:
        from app.services.customer_service import get_customer_by_platform_id
        from app.utils.admin_check import detect_platform_from_context
        
        platform = detect_platform_from_context(context)
        customer = await get_customer_by_platform_id(session, user.id, platform)
        
        if not customer:
            await progress_msg.edit_text("❌ مشتری یافت نشد.")
            return

        channels = await get_customer_channels(session, customer.id, only_active=True)

        eitaa_token = None
        if any(c.platform == Platform.EITAA for c in channels):
            from app.services.customer_service import get_customer_eitaa_token
            eitaa_token = await get_customer_eitaa_token(session, customer.id)

    # استخراج فقط لینک‌ها یا فایل‌آیدی‌ها برای ارسال
    media_file_ids = [m["file_id"] for m in medias]

    from app.database.models import Product
    dummy_prod = Product(product_name="پست سفارشی", price=0, stock_qty=1, is_available=True, sku="CUSTOM")
    
    # قرار دادن اولین فایل‌آیدی برای ساپورت منطق‌های زیرین
    if media_file_ids:
        dummy_prod.image_url = media_file_ids[0]

    from app.services.publisher.publisher_manager import publish_to_channel
    import asyncio

    success_count = 0
    fail_count = 0

    for ch in channels:
        try:
            # ارسال مدیاها به Publisher Manager
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
                
            await asyncio.sleep(1) 

        except Exception as e:
            log.error(f"خطا در ارسال پست سفارشی به {ch.channel_identifier}: {e}", exc_info=True)
            fail_count += 1

    result_text = (
        f"✅ <b>عملیات ارسال نهایی شد!</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"✅ ارسال موفق: {success_count}\n"
        f"❌ ارسال ناموفق: {fail_count}"
    )

    await progress_msg.edit_text(result_text, parse_mode="HTML")


async def custom_post_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """انصراف از پست‌ساز دستی"""
    query = update.callback_query
    await query.answer()

    clear_user_state(query.from_user.id)
    
    try:
        await query.message.delete()
    except:
        pass
        
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text="❌ ارسال پست سفارشی لغو شد."
    )