"""
هندلرهای مدیریت کانال
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from app.database.connection import AsyncSessionLocal
from app.database.models import CustomerStatus, Platform
from app.services.customer_service import get_customer_by_telegram_id
from app.services.channel_service import (
    check_bot_is_admin_in_channel,
    add_channel_for_customer,
    get_customer_channels,
    delete_channel,
    check_channel_already_exists,
    get_channel_by_id,
)
from app.services.subscription.service import get_active_subscription
from app.bot.keyboards.channel import (
    get_channel_management_keyboard,
    get_channel_list_keyboard,
    get_channel_delete_confirm_keyboard,
    get_cancel_channel_add_keyboard,
    get_platform_selection_keyboard,
)
from app.bot.states.user_state import (
    UserState,
    set_user_state,
    get_user_state,
    clear_user_state,
)
from app.utils.logger import log


# ═══════════════════════════════════════════════════════════
# منوی اصلی کانال
# ═══════════════════════════════════════════════════════════

async def channel_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش منوی مدیریت کانال"""
    user = update.effective_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)

        if not customer or customer.customer_status != CustomerStatus.ACTIVE:
            await update.message.reply_text(
                "❌ حساب شما فعال نیست. لطفاً /start بزنید."
            )
            return

        channels = await get_customer_channels(session, customer.id)
        channels_count = len(channels)

    await update.message.reply_text(
        f"📢 مدیریت کانال\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📊 تعداد کانال‌های شما: {channels_count}\n"
        f"━━━━━━━━━━━━━━━",
        reply_markup=get_channel_management_keyboard(),
    )


async def channel_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بازگشت به منوی مدیریت کانال از callback"""
    query = update.callback_query
    await query.answer()

    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            await query.edit_message_text("❌ خطا!")
            return

        channels = await get_customer_channels(session, customer.id)

    clear_user_state(user.id)

    await query.edit_message_text(
        f"📢 مدیریت کانال\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📊 تعداد کانال‌های شما: {len(channels)}\n"
        f"━━━━━━━━━━━━━━━",
        reply_markup=get_channel_management_keyboard(),
    )


# ═══════════════════════════════════════════════════════════
# اضافه کردن کانال - انتخاب پلتفرم
# ═══════════════════════════════════════════════════════════

async def channel_add_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش انتخاب پلتفرم"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "➕ اتصال کانال جدید\n"
        "━━━━━━━━━━━━━━━\n\n"
        "کانالتون در کدوم پلتفرم هست؟\n\n"
        "📱 <b>تلگرام</b>: فعال و آماده استفاده\n"
        "📢 <b>ایتا</b>: به زودی فعال میشه\n"
        "🔵 <b>بله</b>: به زودی فعال میشه\n\n"
        "💡 می‌تونید کانال‌های ایتا/بله رو الان ثبت کنید\n"
        "تا آماده باشن برای زمان فعال‌سازی.",
        parse_mode="HTML",
        reply_markup=get_platform_selection_keyboard(),
    )


async def channel_platform_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """کاربر پلتفرم رو انتخاب کرد"""
    query = update.callback_query
    await query.answer()

    platform_str = query.data.replace("channel_platform_", "")
    user = query.from_user

    log.info(f"🎯 [DEBUG] پلتفرم انتخاب شد: {platform_str}")

    # چک محدودیت پلن
    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            await query.edit_message_text("❌ خطا!")
            return

        subscription = await get_active_subscription(session, customer.id)
        if not subscription:
            await query.edit_message_text(
                "❌ اشتراک فعالی ندارید!\n"
                "از منوی '💳 اشتراک من' اشتراک تهیه کنید."
            )
            return

        from app.services.subscription.plans import get_plan
        plan = get_plan(subscription.plan_key)

        channels = await get_customer_channels(session, customer.id)
        current_count = len(channels)

        if current_count >= plan.max_channels:
            max_ch = plan.max_channels if plan.max_channels < 9999 else "نامحدود"
            await query.edit_message_text(
                f"❌ محدودیت پلن پر شده!\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📦 پلن شما: {plan.emoji} {plan.name_fa}\n"
                f"📢 حداکثر کانال: {max_ch}\n"
                f"📊 کانال‌های فعلی: {current_count}\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"برای اضافه کردن کانال بیشتر:\n"
                f"• یه کانال قبلی رو حذف کنید\n"
                f"• یا پلن خودتون رو ارتقا بدید"
            )
            return

    # تنظیم state
    if platform_str == "TELEGRAM":
        set_user_state(user.id, UserState.WAITING_CHANNEL_ID_TELEGRAM)
        log.info(f"✅ [DEBUG] state ست شد: WAITING_CHANNEL_ID_TELEGRAM")
        text = (
            "📱 اتصال کانال تلگرام\n"
            "━━━━━━━━━━━━━━━\n\n"
            "📝 مراحل:\n\n"
            "1️⃣ به کانال خود برید\n"
            "2️⃣ روی نام کانال کلیک کنید\n"
            "3️⃣ Administrators را باز کنید\n"
            "4️⃣ ربات ما را ادمین کنید\n"
            "5️⃣ دسترسی 'Post Messages' را فعال کنید\n\n"
            "بعد آیدی کانال رو اینجا بفرستید:\n"
            "مثال: @my_channel\n"
            "یا -100123456789"
        )
    elif platform_str == "EITAA":
        # چک کن مشتری قبلاً توکن ایتا داده یا نه
        async with AsyncSessionLocal() as session:
            from app.services.customer_service import get_customer_eitaa_token
            eitaa_token = await get_customer_eitaa_token(session, customer.id)

        if not eitaa_token:
            # اولین بار - توکن رو بگیر
            set_user_state(user.id, UserState.WAITING_EITAA_TOKEN)
            log.info(f"✅ [DEBUG] state ست شد: WAITING_EITAA_TOKEN")
            text = (
                "📢 <b>اتصال کانال ایتا - مرحله ۱ از ۲</b>\n"
                "━━━━━━━━━━━━━━━\n\n"
                "🔑 <b>ابتدا توکن ربات ایتا رو نیاز داریم</b>\n\n"
                "📝 <b>راهنمای دریافت توکن:</b>\n\n"
                "1️⃣ به سایت <b>eitaayar.ir</b> برید و ثبت‌نام کنید\n\n"
                "2️⃣ در پنل، کانال ایتای خودتون رو اضافه کنید\n\n"
                "3️⃣ ربات ایتایار رو به عنوان ادمین به کانال اضافه کنید\n\n"
                "4️⃣ توکن API رو از پنل کپی کنید\n"
                "(چیزی شبیه: <code>bot123456:xxxx-xxxx-xxxx</code>)\n\n"
                "5️⃣ توکن رو اینجا ارسال کنید\n\n"
                "━━━━━━━━━━━━━━━\n"
                "💡 <b>نکته:</b> توکن فقط یک بار گرفته میشه\n"
                "و برای همه کانال‌های ایتای شما استفاده میشه."
            )
        else:
            # توکن قبلاً داده شده - فقط chat_id
            set_user_state(user.id, UserState.WAITING_EITAA_CHAT_ID)
            log.info(f"✅ [DEBUG] state ست شد: WAITING_EITAA_CHAT_ID")
            text = (
                "📢 <b>اتصال کانال ایتا</b>\n"
                "━━━━━━━━━━━━━━━\n\n"
                "✅ توکن ایتا از قبل ذخیره شده.\n\n"
                "🆔 <b>لطفاً chat_id کانال ایتا رو ارسال کنید</b>\n\n"
                "📝 <b>راهنما:</b>\n"
                "1️⃣ به پنل ایتایار برید (eitaayar.ir)\n"
                "2️⃣ کانالتون رو انتخاب کنید\n"
                "3️⃣ chat_id عددی رو کپی کنید\n"
                "(مثال: <code>11226043</code>)\n\n"
                "4️⃣ اینجا ارسال کنید"
            )
    elif platform_str == "BALE":
        set_user_state(user.id, UserState.WAITING_CHANNEL_ID_BALE)
        log.info(f"✅ [DEBUG] state ست شد: WAITING_CHANNEL_ID_BALE")
        text = (
            "🔵 اتصال کانال بله\n"
            "━━━━━━━━━━━━━━━\n\n"
            "⚠️ <b>توجه</b>: این پلتفرم به زودی فعال میشه.\n"
            "الان کانال رو ثبت می‌کنید و وقت فعال شدن،\n"
            "خودکار شروع به کار می‌کنه.\n\n"
            "لطفاً لینک یا آیدی کانال بله رو بفرستید:\n"
            "مثال: ble.ir/my_channel\n"
            "یا: @my_channel"
        )
    else:
        await query.edit_message_text("❌ پلتفرم نامعتبر!")
        return

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=get_cancel_channel_add_keyboard(),
    )


# ═══════════════════════════════════════════════════════════
# دریافت آیدی کانال - Router بر اساس platform
# ═══════════════════════════════════════════════════════════

async def channel_id_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دریافت آیدی کانال - بر اساس پلتفرم متفاوت عمل می‌کنه"""
    user = update.effective_user
    state = get_user_state(user.id)

    log.info(f"🎯 [DEBUG] channel_id_received_handler اجرا شد: state={state}")

    if state == UserState.WAITING_CHANNEL_ID_TELEGRAM:
        await _handle_telegram_channel(update, context)
    elif state == UserState.WAITING_EITAA_TOKEN:
        await _handle_eitaa_token(update, context)
    elif state == UserState.WAITING_EITAA_CHAT_ID:
        await _handle_eitaa_chat_id(update, context)
    elif state == UserState.WAITING_CHANNEL_ID_BALE:
        await _handle_bale_channel(update, context)
    elif state == UserState.WAITING_CHANNEL_ID:
        await _handle_telegram_channel(update, context)
    else:
        log.warning(f"⚠️ state نامعتبر: {state}")

# ═══════════════════════════════════════════════════════════
# پردازش کانال تلگرام (با احراز واقعی)
# ═══════════════════════════════════════════════════════════

async def _handle_telegram_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پردازش کانال تلگرام"""
    user = update.effective_user
    channel_input = update.message.text.strip()

    log.info(f"🔍 [DEBUG] _handle_telegram_channel: input={channel_input}")

    # اعتبارسنجی
    if not channel_input.startswith("@") and not channel_input.startswith("-100"):
        await update.message.reply_text(
            "❌ فرمت آیدی کانال اشتباه است!\n\n"
            "آیدی باید یکی از این دو حالت باشه:\n"
            "• با @ شروع بشه (مثل @my_channel)\n"
            "• عددی و با -100 شروع بشه"
        )
        return

    checking_msg = await update.message.reply_text(
        "🔍 در حال بررسی کانال...\n"
        "لطفاً چند لحظه صبر کنید."
    )

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            await checking_msg.edit_text("❌ خطا! لطفاً /start بزنید.")
            clear_user_state(user.id)
            return

        # چک تکراری
        already_exists = await check_channel_already_exists(
            session, customer.id, channel_input
        )
        if already_exists:
            await checking_msg.edit_text("⚠️ این کانال قبلاً اضافه شده است.")
            clear_user_state(user.id)
            return

        # چک ادمین بودن ربات
        result = await check_bot_is_admin_in_channel(context.bot, channel_input)

        if not result.is_valid:
            await checking_msg.edit_text(
                f"❌ اتصال ناموفق!\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📝 دلیل: {result.error_message}\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"لطفاً مطمئن بشید:\n"
                f"• ربات ادمین کانال باشه\n"
                f"• دسترسی ارسال پیام داشته باشه\n\n"
                f"دوباره تلاش کنید."
            )
            clear_user_state(user.id)
            return

        # اضافه کردن
        channel = await add_channel_for_customer(
            session=session,
            customer_id=customer.id,
            channel_identifier=channel_input,
            platform=Platform.TELEGRAM,
            activation_status="ACTIVE",
        )

    clear_user_state(user.id)

    await checking_msg.edit_text(
        f"✅ کانال تلگرام با موفقیت متصل شد!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📱 پلتفرم: تلگرام\n"
        f"📢 نام کانال: {result.channel_title}\n"
        f"🆔 آیدی: {channel_input}\n"
        f"👥 تعداد اعضا: {result.member_count:,}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"حالا می‌تونید محصولات رو در این کانال منتشر کنید."
    )

async def _handle_eitaa_token(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    مرحله ۱: دریافت توکن ربات ایتا
    """
    user = update.effective_user
    token_input = update.message.text.strip()

    log.info(f"🔍 [Eitaa Token] دریافت شد از user={user.id}")

    # اعتبارسنجی فرمت توکن
    if not token_input.startswith("bot") or ":" not in token_input:
        await update.message.reply_text(
            "❌ فرمت توکن اشتباه است!\n\n"
            "توکن باید با <b>bot</b> شروع بشه و شامل <b>:</b> باشه.\n\n"
            "مثال:\n"
            "<code>bot123456:xxxxx-xxxxx-xxxxx</code>\n\n"
            "دوباره ارسال کنید یا لغو کنید.",
            parse_mode="HTML",
            reply_markup=get_cancel_channel_add_keyboard(),
        )
        return

    if len(token_input) < 30:
        await update.message.reply_text(
            "❌ توکن خیلی کوتاه است!\n\n"
            "لطفاً توکن کامل رو از پنل ایتایار کپی کنید.",
            reply_markup=get_cancel_channel_add_keyboard(),
        )
        return

    # ⚠️ ابتدا state رو تغییر بده تا اگه پیام دوم اومد، اشتباه هندل نشه
    # این کار جلوگیری از دوبار پاسخ می‌کنه
    from app.bot.states.user_state import UserState
    set_user_state(user.id, UserState.IDLE)   # موقتاً IDLE

    checking_msg = await update.message.reply_text(
        "🔍 در حال بررسی توکن..."
    )

    # تست توکن
    from app.services.publisher.eitaa_client import EitaaClient

    try:
        client = EitaaClient(token=token_input)
        # پیام تست به chat_id="0" (احتمالاً وجود نداره)
        # اگه توکن غلط باشه: 401
        # اگه توکن درست باشه: 400 (chat_id غلط) یا موفق
        test_result = await client.send_message(chat_id="0", text=".")

        # فقط 401 یعنی توکن غلطه
        if test_result.error_code == 401:
            # برگردون state رو تا مشتری بتونه دوباره امتحان کنه
            set_user_state(user.id, UserState.WAITING_EITAA_TOKEN)

            await checking_msg.edit_text(
                f"❌ توکن نامعتبر است!\n\n"
                f"دلیل: {test_result.error_message}\n\n"
                f"لطفاً توکن رو دوباره از پنل ایتایار کپی کنید.",
                reply_markup=get_cancel_channel_add_keyboard(),
            )
            return

        log.info(f"✅ [Eitaa Token] توکن معتبر برای user={user.id}")

    except Exception as e:
        log.error(f"[Eitaa Token] خطا در بررسی: {e}", exc_info=True)

        # برگردون state
        set_user_state(user.id, UserState.WAITING_EITAA_TOKEN)

        await checking_msg.edit_text(
            f"⚠️ خطا در بررسی توکن:\n{str(e)[:200]}\n\n"
            f"لطفاً دوباره تلاش کنید.",
            reply_markup=get_cancel_channel_add_keyboard(),
        )
        return

    # ذخیره توکن (با رمزنگاری)
    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            await checking_msg.edit_text("❌ خطا! لطفاً /start بزنید.")
            clear_user_state(user.id)
            return

        from app.services.customer_service import set_customer_eitaa_token
        await set_customer_eitaa_token(session, customer.id, token_input)

    # حالا state رو تنظیم کن برای گرفتن chat_id
    set_user_state(user.id, UserState.WAITING_EITAA_CHAT_ID)

    await checking_msg.edit_text(
        "✅ توکن ذخیره شد!\n"
        "━━━━━━━━━━━━━━━\n\n"
        "📢 <b>مرحله ۲ از ۲</b>\n\n"
        "🆔 حالا <b>chat_id کانال ایتا</b> رو ارسال کنید:\n\n"
        "📝 <b>راهنما:</b>\n"
        "1️⃣ به پنل ایتایار برید\n"
        "2️⃣ کانالتون رو انتخاب کنید\n"
        "3️⃣ chat_id عددی رو کپی کنید\n"
        "(مثال: <code>11226043</code>)\n\n"
        "4️⃣ اینجا ارسال کنید",
        parse_mode="HTML",
        reply_markup=get_cancel_channel_add_keyboard(),
    )

async def _handle_eitaa_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    مرحله ۲: دریافت chat_id کانال ایتا و ذخیره
    """
    user = update.effective_user
    chat_id_input = update.message.text.strip()

    log.info(f"🔍 [Eitaa Chat ID] دریافت شد: {chat_id_input}")

    # اعتبارسنجی: باید عددی باشه
    if not chat_id_input.lstrip("-").isdigit():
        await update.message.reply_text(
            "❌ فرمت chat_id اشتباه است!\n\n"
            "chat_id باید فقط عدد باشه.\n"
            "مثال: <code>11226043</code>\n\n"
            "دوباره ارسال کنید.",
            parse_mode="HTML",
            reply_markup=get_cancel_channel_add_keyboard(),
        )
        return

    # ⚠️ state رو موقتاً IDLE کن تا پیام‌های اضافه نره به این handler
    from app.bot.states.user_state import UserState
    set_user_state(user.id, UserState.IDLE)

    checking_msg = await update.message.reply_text(
        "🔍 در حال بررسی کانال..."
    )

    # گرفتن مشتری و توکن
    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            await checking_msg.edit_text("❌ خطا!")
            clear_user_state(user.id)
            return

        from app.services.customer_service import get_customer_eitaa_token
        eitaa_token = await get_customer_eitaa_token(session, customer.id)

        if not eitaa_token:
            await checking_msg.edit_text(
                "❌ توکن ایتا پیدا نشد!\n"
                "لطفاً از اول شروع کنید.",
                reply_markup=get_channel_management_keyboard(),
            )
            clear_user_state(user.id)
            return

        # چک تکراری
        already_exists = await check_channel_already_exists(
            session, customer.id, chat_id_input
        )
        if already_exists:
            clear_user_state(user.id)
            await checking_msg.edit_text(
                "⚠️ این کانال قبلاً اضافه شده است.",
                reply_markup=get_channel_management_keyboard(),
            )
            return

    # تست ارسال یه پیام تست به chat_id
    from app.services.publisher.eitaa_client import EitaaClient

    try:
        client = EitaaClient(token=eitaa_token)
        test_result = await client.send_message(
            chat_id=chat_id_input,
            text="✅ اتصال با موفقیت برقرار شد!\n\nاز این پس محصولات شما در این کانال منتشر می‌شوند.",
        )

        if not test_result.ok:
            # برگردون state
            set_user_state(user.id, UserState.WAITING_EITAA_CHAT_ID)

            await checking_msg.edit_text(
                f"❌ اتصال به کانال ناموفق!\n"
                f"━━━━━━━━━━━━━━━\n"
                f"دلیل: {test_result.error_message}\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"⚠️ <b>مطمئن شوید:</b>\n"
                f"• chat_id درست باشه\n"
                f"• ربات ایتایار در کانال ادمین باشه\n"
                f"• کانال فعال باشه\n\n"
                f"دوباره تلاش کنید.",
                parse_mode="HTML",
                reply_markup=get_cancel_channel_add_keyboard(),
            )
            return

        log.info(f"✅ [Eitaa] تست موفق: message_id={test_result.message_id}")

    except Exception as e:
        log.error(f"[Eitaa Chat] خطا در تست: {e}", exc_info=True)

        # برگردون state
        set_user_state(user.id, UserState.WAITING_EITAA_CHAT_ID)

        await checking_msg.edit_text(
            f"⚠️ خطا در تست:\n{str(e)[:200]}\n\n"
            f"لطفاً دوباره تلاش کنید.",
            reply_markup=get_cancel_channel_add_keyboard(),
        )
        return

    # ذخیره کانال
    async with AsyncSessionLocal() as session:
        channel = await add_channel_for_customer(
            session=session,
            customer_id=customer.id,
            channel_identifier=chat_id_input,
            platform=Platform.EITAA,
            activation_status="ACTIVE",
        )

    clear_user_state(user.id)

    await checking_msg.edit_text(
        f"✅ کانال ایتا با موفقیت متصل شد!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📢 پلتفرم: ایتا\n"
        f"🆔 chat_id: {chat_id_input}\n"
        f"✅ وضعیت: فعال\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"💡 یک پیام تستی به کانال ارسال شد.\n"
        f"از الان محصولات شما در این کانال ایتا هم منتشر میشن."
    )
# ═══════════════════════════════════════════════════════════
# پردازش کانال ایتا (فقط ثبت)
# ═══════════════════════════════════════════════════════════

async def _handle_eitaa_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پردازش کانال ایتا (فقط ثبت، بدون احراز)"""
    user = update.effective_user
    channel_input = update.message.text.strip()

    log.info(f"🔍 [DEBUG] _handle_eitaa_channel: input={channel_input}")

    # اعتبارسنجی
    valid_prefixes = ["eitaa.com/", "https://eitaa.com/", "http://eitaa.com/", "@"]
    is_valid = any(channel_input.startswith(p) for p in valid_prefixes)

    if not is_valid:
        await update.message.reply_text(
            "❌ فرمت لینک ایتا اشتباه است!\n\n"
            "لینک باید یکی از این حالت‌ها باشه:\n"
            "• eitaa.com/my_channel\n"
            "• https://eitaa.com/my_channel\n"
            "• @my_channel"
        )
        return

    normalized = _normalize_eitaa_link(channel_input)

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            await update.message.reply_text("❌ خطا!")
            clear_user_state(user.id)
            return

        already_exists = await check_channel_already_exists(
            session, customer.id, normalized
        )
        if already_exists:
            await update.message.reply_text("⚠️ این کانال قبلاً اضافه شده است.")
            clear_user_state(user.id)
            return

        channel = await add_channel_for_customer(
            session=session,
            customer_id=customer.id,
            channel_identifier=normalized,
            platform=Platform.EITAA,
            activation_status="PENDING_ACTIVATION",
        )

    clear_user_state(user.id)

    await update.message.reply_text(
        f"✅ کانال ایتا ثبت شد!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📢 پلتفرم: ایتا\n"
        f"🆔 آیدی: {normalized}\n"
        f"⏳ وضعیت: در انتظار فعال‌سازی\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"💡 <b>نکته:</b>\n"
        f"این کانال روی ۱ ظرفیت از پلن شما حساب میشه.\n"
        f"وقتی سیستم ایتا فعال بشه، خودکار شروع به کار می‌کنه.",
        parse_mode="HTML",
    )


# ═══════════════════════════════════════════════════════════
# پردازش کانال بله (فقط ثبت)
# ═══════════════════════════════════════════════════════════

async def _handle_bale_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پردازش کانال بله"""
    user = update.effective_user
    channel_input = update.message.text.strip()

    log.info(f"🔍 [DEBUG] _handle_bale_channel: input={channel_input}")

    valid_prefixes = ["ble.ir/", "https://ble.ir/", "http://ble.ir/", "@"]
    is_valid = any(channel_input.startswith(p) for p in valid_prefixes)

    if not is_valid:
        await update.message.reply_text(
            "❌ فرمت لینک بله اشتباه است!\n\n"
            "لینک باید یکی از این حالت‌ها باشه:\n"
            "• ble.ir/my_channel\n"
            "• https://ble.ir/my_channel\n"
            "• @my_channel"
        )
        return

    normalized = _normalize_bale_link(channel_input)

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            await update.message.reply_text("❌ خطا!")
            clear_user_state(user.id)
            return

        already_exists = await check_channel_already_exists(
            session, customer.id, normalized
        )
        if already_exists:
            await update.message.reply_text("⚠️ این کانال قبلاً اضافه شده است.")
            clear_user_state(user.id)
            return

        channel = await add_channel_for_customer(
            session=session,
            customer_id=customer.id,
            channel_identifier=normalized,
            platform=Platform.BALE,
            activation_status="PENDING_ACTIVATION",
        )

    clear_user_state(user.id)

    await update.message.reply_text(
        f"✅ کانال بله ثبت شد!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔵 پلتفرم: بله\n"
        f"🆔 آیدی: {normalized}\n"
        f"⏳ وضعیت: در انتظار فعال‌سازی\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"💡 <b>نکته:</b>\n"
        f"این کانال روی ۱ ظرفیت از پلن شما حساب میشه.\n"
        f"وقتی سیستم بله فعال بشه، خودکار شروع به کار می‌کنه.",
        parse_mode="HTML",
    )


# ═══════════════════════════════════════════════════════════
# توابع کمکی - نرمال‌سازی لینک
# ═══════════════════════════════════════════════════════════

def _normalize_eitaa_link(input_str: str) -> str:
    """نرمال‌سازی لینک ایتا به @username"""
    input_str = input_str.strip()
    for prefix in ["https://eitaa.com/", "http://eitaa.com/", "eitaa.com/"]:
        if input_str.startswith(prefix):
            input_str = input_str[len(prefix):]
            return f"@{input_str}"
    return input_str


def _normalize_bale_link(input_str: str) -> str:
    """نرمال‌سازی لینک بله به @username"""
    input_str = input_str.strip()
    for prefix in ["https://ble.ir/", "http://ble.ir/", "ble.ir/"]:
        if input_str.startswith(prefix):
            input_str = input_str[len(prefix):]
            return f"@{input_str}"
    return input_str


# ═══════════════════════════════════════════════════════════
# لیست کانال‌ها
# ═══════════════════════════════════════════════════════════

async def channel_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش لیست کانال‌های مشتری"""
    query = update.callback_query
    await query.answer()

    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            await query.edit_message_text("❌ خطا!")
            return

        channels = await get_customer_channels(session, customer.id)
        subscription = await get_active_subscription(session, customer.id)

    if not channels:
        await query.edit_message_text(
            "📋 لیست کانال‌های شما\n"
            "━━━━━━━━━━━━━━━\n\n"
            "هنوز کانالی متصل نکرده‌اید.",
            reply_markup=get_channel_management_keyboard(),
        )
        return

    total = len(channels)
    telegram_count = sum(1 for c in channels if c.platform == Platform.TELEGRAM)
    eitaa_count = sum(1 for c in channels if c.platform == Platform.EITAA)
    bale_count = sum(1 for c in channels if c.platform == Platform.BALE)

    max_ch = "?"
    if subscription:
        from app.services.subscription.plans import get_plan
        plan = get_plan(subscription.plan_key)
        max_ch = plan.max_channels if plan.max_channels < 9999 else "نامحدود"

    text = (
        f"📋 لیست کانال‌های شما\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📊 تعداد کل: {total} از {max_ch}\n"
    )

    if telegram_count > 0:
        text += f"📱 تلگرام: {telegram_count}\n"
    if eitaa_count > 0:
        text += f"📢 ایتا: {eitaa_count} (در انتظار فعال‌سازی)\n"
    if bale_count > 0:
        text += f"🔵 بله: {bale_count} (در انتظار فعال‌سازی)\n"

    text += (
        f"━━━━━━━━━━━━━━━\n\n"
        f"برای مشاهده جزئیات یا حذف، روی کانال کلیک کنید:"
    )

    await query.edit_message_text(
        text,
        reply_markup=get_channel_list_keyboard(channels),
    )


# ═══════════════════════════════════════════════════════════
# حذف کانال
# ═══════════════════════════════════════════════════════════

async def channel_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """درخواست تایید حذف کانال"""
    query = update.callback_query
    await query.answer()

    channel_id = int(query.data.replace("channel_delete_", ""))

    async with AsyncSessionLocal() as session:
        channel = await get_channel_by_id(session, channel_id)

        if not channel:
            await query.edit_message_text("❌ کانال پیدا نشد!")
            return

    await query.edit_message_text(
        f"⚠️ حذف کانال\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📢 کانال: {channel.channel_identifier}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"آیا مطمئن هستید؟\n\n"
        f"⚠️ توجه: با حذف کانال، پست‌های موجود در کانال حذف نمی‌شن\n"
        f"فقط ارتباط ربات با کانال قطع میشه.",
        reply_markup=get_channel_delete_confirm_keyboard(channel_id),
    )


async def channel_delete_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تایید نهایی حذف کانال"""
    query = update.callback_query
    await query.answer()

    channel_id = int(query.data.replace("channel_delete_confirm_", ""))

    async with AsyncSessionLocal() as session:
        success = await delete_channel(session, channel_id)

        if not success:
            await query.edit_message_text("❌ حذف ناموفق!")
            return

    await query.edit_message_text(
        "✅ کانال با موفقیت حذف شد.\n\n"
        "می‌تونید از منو کانال جدید اضافه کنید.",
        reply_markup=get_channel_management_keyboard(),
    )