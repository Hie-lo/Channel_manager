"""
هندلرهای مربوط به فرآیند ورود کد و اتصال حساب‌ها
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from app.database.connection import AsyncSessionLocal
from app.services.account_link_service import verify_and_link_account
from app.utils.admin_check import detect_platform_from_context
from app.bot.states.user_state import UserState, set_user_state, get_user_state, clear_user_state
from app.utils.logger import log


async def link_account_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """وقتی کاربر جدید دکمه اتصال حساب را می‌زند"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    set_user_state(user.id, UserState.WAITING_FOR_LINK_CODE)
    
    await query.edit_message_text(
        "🔗 <b>اتصال به حساب موجود</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
        "برای اتصال این دستگاه به حساب فعلی خود:\n\n"
        "1️⃣ وارد ربات در پلتفرمی شوید که حساب شما در آن فعال است (مثلاً تلگرام).\n"
        "2️⃣ به بخش <b>⚙️ تنظیمات</b> بروید.\n"
        "3️⃣ روی <b>🔗 تولید کد اتصال</b> کلیک کنید.\n"
        "4️⃣ کد ۶ رقمی دریافت شده را دقیقاً در همینجا تایپ و ارسال کنید.\n\n"
        "⚠️ کدها به حروف کوچک و بزرگ حساس هستند.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ انصراف", callback_data="link_account_cancel")
        ]])
    )

async def link_account_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """انصراف از وارد کردن کد و بازگشت به منوی انتخاب اولیه"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    clear_user_state(user.id)
    
    from app.utils.admin_check import detect_platform_from_context
    from app.bot.keyboards.main_menu import get_business_type_keyboard
    
    platform = detect_platform_from_context(context)
    platform_display = "تلگرام" if platform == "TELEGRAM" else "بله"
    
    raw_biz_keyboard = get_business_type_keyboard().inline_keyboard
    biz_keyboard = [list(row) for row in raw_biz_keyboard]
    link_button = [InlineKeyboardButton("🔗 اتصال به حساب قبلی من", callback_data="link_account_start")]
    
    final_markup = InlineKeyboardMarkup([link_button] + biz_keyboard)

    await query.edit_message_text(
        f"👋 سلام {user.first_name} عزیز!\n\n"
        f"به ربات مدیریت کانال خوش آمدید.\n"
        f"🤖 پلتفرم: {platform_display}\n\n"
        f"اگر قبلاً در پلتفرم دیگری ثبت‌نام کرده‌اید، دکمه «اتصال به حساب قبلی من» را بزنید.\n\n"
        f"در غیر این صورت، برای ثبت‌نام جدید لطفاً نوع کسب‌وکار خود را انتخاب کنید:",
        reply_markup=final_markup,
    )


async def link_code_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دریافت کد متنی از کاربر و اعتبارسنجی آن"""
    user = update.effective_user
    
    if get_user_state(user.id) != UserState.WAITING_FOR_LINK_CODE:
        return
        
    code_input = update.message.text.strip()
    platform = detect_platform_from_context(context)
    
    # 1. پیام لودینگ
    wait_msg = await update.message.reply_text("🔄 در حال بررسی کد، لطفاً صبر کنید...")
    
    # 2. فراخوانی سرویس امنیتی
    async with AsyncSessionLocal() as session:
        success, msg, customer = await verify_and_link_account(
            session=session,
            code_str=code_input,
            new_user_id=user.id,
            new_platform=platform,
            new_first_name=user.first_name,
            new_username=user.username
        )
        
    clear_user_state(user.id)
    
    # 3. پاسخ به کاربر
    if not success:
        await wait_msg.edit_text(
            f"{msg}\n\n"
            f"برای تلاش مجدد، از دستور /start استفاده کنید."
        )
        return
        
    # موفقیت آمیز
    from app.bot.keyboards.main_menu import get_customer_main_menu
    
    await wait_msg.edit_text(
        f"✅ <b>اتصال موفق!</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"حساب شما با موفقیت به دستگاه متصل شد.\n"
        f"هم‌اکنون اطلاعات و محصولات شما در هر دو پلتفرم یکسان و هماهنگ (Sync) است.",
        parse_mode="HTML"
    )
    
    # نمایش منوی اصلی
    await update.message.reply_text(
        f"سلام {customer.first_name or user.first_name} عزیز! 👋\nخوش برگشتید.",
        reply_markup=get_customer_main_menu(),
    )
    
    # 4. هشدار امنیتی به دستگاه اصلی
    await _send_security_alert_to_original_device(context, customer, platform)


async def _send_security_alert_to_original_device(context, customer, new_platform: str):
    """ارسال پیام هشدار لاگین به دستگاه دیگر (مثل سیستم امنیتی تلگرام)"""
    try:
        # اگر کاربر در بله لاگین کرده، هشدار رو به تلگرامش بفرستیم
        target_chat_id = None
        platform_name = "بله" if new_platform == "BALE" else "تلگرام"
        
        if new_platform == "BALE" and customer.telegram_user_id:
            target_chat_id = customer.telegram_user_id
        elif new_platform == "TELEGRAM" and customer.bale_user_id:
            target_chat_id = customer.bale_user_id
            
        if target_chat_id:
            alert_text = (
                f"🚨 <b>هشدار امنیتی: اتصال حساب جدید</b>\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"یک حساب جدید از پلتفرم <b>{platform_name}</b> همین الان به حساب کاربری شما متصل شد.\n\n"
                f"اگر این کار توسط شما انجام شده است، این پیام را نادیده بگیرید.\n"
                f"در غیر این صورت، لطفاً فوراً با پشتیبانی تماس بگیرید!"
            )
            await context.bot.send_message(
                chat_id=target_chat_id,
                text=alert_text,
                parse_mode="HTML"
            )
    except Exception as e:
        log.error(f"خطا در ارسال هشدار امنیتی اتصال حساب: {e}")