"""
هندلرهای مدیریت کانال
"""

from telegram import Update
from telegram.ext import ContextTypes

from app.database.connection import AsyncSessionLocal
from app.database.models import CustomerStatus
from app.services.customer_service import get_customer_by_telegram_id
from app.services.channel_service import (
    check_bot_is_admin_in_channel,
    add_channel_for_customer,
    get_customer_channels,
    delete_channel,
    check_channel_already_exists,
    get_channel_by_id,
)
from app.bot.keyboards.channel import (
    get_channel_management_keyboard,
    get_channel_list_keyboard,
    get_channel_delete_confirm_keyboard,
    get_cancel_channel_add_keyboard,
)
from app.bot.states.user_state import (
    UserState,
    set_user_state,
    get_user_state,
    clear_user_state,
)
from app.utils.logger import log


async def channel_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    نمایش منوی مدیریت کانال
    وقتی مشتری دکمه '📢 مدیریت کانال' رو میزنه
    """
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


async def channel_add_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    شروع فرآیند اضافه کردن کانال جدید
    """
    query = update.callback_query
    await query.answer()

    user = query.from_user

    # تنظیم وضعیت کاربر
    set_user_state(user.id, UserState.WAITING_CHANNEL_ID)

    await query.edit_message_text(
        "➕ اتصال کانال جدید\n"
        "━━━━━━━━━━━━━━━\n\n"
        "📝 برای اتصال کانال این مراحل رو انجام بدید:\n\n"
        "1️⃣ به کانال خود برید\n"
        "2️⃣ روی نام کانال کلیک کنید\n"
        "3️⃣ Administrators را باز کنید\n"
        "4️⃣ ربات ما را ادمین کنید\n"
        "5️⃣ دسترسی 'Post Messages' را فعال کنید\n\n"
        "بعد آیدی کانال رو اینجا بفرستید:\n"
        "مثال: @my_channel\n"
        "یا -100123456789",
        reply_markup=get_cancel_channel_add_keyboard(),
    )


async def channel_id_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    وقتی مشتری آیدی کانال رو میفرسته
    این handler برای پیام‌های متنی هست
    """
    user = update.effective_user

    # چک کن کاربر در حالت انتظار آیدی کانال هست
    if get_user_state(user.id) != UserState.WAITING_CHANNEL_ID:
        return  # این پیام برای این handler نیست

    channel_input = update.message.text.strip()

    # اعتبارسنجی اولیه
    if not channel_input.startswith("@") and not channel_input.startswith("-100"):
        await update.message.reply_text(
            "❌ فرمت آیدی کانال اشتباه است!\n\n"
            "آیدی باید یکی از این دو حالت باشه:\n"
            "• با @ شروع بشه (مثل @my_channel)\n"
            "• عددی و با -100 شروع بشه"
        )
        return

    # پیام در حال بررسی
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

        # چک کن قبلاً اضافه نشده باشه
        already_exists = await check_channel_already_exists(
            session, customer.id, channel_input
        )

        if already_exists:
            await checking_msg.edit_text(
                "⚠️ این کانال قبلاً اضافه شده است."
            )
            clear_user_state(user.id)
            return

        # چک کن ربات ادمین کانال هست
        result = await check_bot_is_admin_in_channel(
            context.bot, channel_input
        )

        if not result.is_valid:
            await checking_msg.edit_text(
                f"❌ اتصال ناموفق!\n"
                f"━━━━━━━━━━━━━━━\n"
                f"📝 دلیل: {result.error_message}\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"لطفاً مطمئن بشید:\n"
                f"• ربات ادمین کانال باشه\n"
                f"• دسترسی ارسال پیام داشته باشه\n\n"
                f"بعد دوباره تلاش کنید."
            )
            clear_user_state(user.id)
            return

        # اضافه کن به دیتابیس
        channel = await add_channel_for_customer(
            session, customer.id, channel_input
        )

        clear_user_state(user.id)

        await checking_msg.edit_text(
            f"✅ کانال با موفقیت متصل شد!\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📢 نام کانال: {result.channel_title}\n"
            f"🆔 آیدی: {channel_input}\n"
            f"👥 تعداد اعضا: {result.member_count:,}\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"حالا می‌تونید محصولات رو آپلود کنید."
        )


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

    if not channels:
        await query.edit_message_text(
            "📋 لیست کانال‌های شما\n"
            "━━━━━━━━━━━━━━━\n\n"
            "هنوز کانالی متصل نکرده‌اید.",
            reply_markup=get_channel_management_keyboard(),
        )
        return

    await query.edit_message_text(
        f"📋 لیست کانال‌های شما\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📊 تعداد: {len(channels)}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"برای مشاهده جزئیات یا حذف، روی کانال کلیک کنید:",
        reply_markup=get_channel_list_keyboard(channels),
    )


async def channel_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بازگشت به منوی مدیریت کانال (از callback)"""
    query = update.callback_query
    await query.answer()

    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)

        if not customer:
            await query.edit_message_text("❌ خطا!")
            return

        channels = await get_customer_channels(session, customer.id)

    # پاک کردن وضعیت کاربر
    clear_user_state(user.id)

    await query.edit_message_text(
        f"📢 مدیریت کانال\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📊 تعداد کانال‌های شما: {len(channels)}\n"
        f"━━━━━━━━━━━━━━━",
        reply_markup=get_channel_management_keyboard(),
    )


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