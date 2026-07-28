"""
هندلرهای پنل ادمین
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from app.config import settings
from app.database.connection import AsyncSessionLocal
from app.database.models import CustomerStatus
from app.services.admin_service import (
    get_customers_by_status,
    get_customer_by_id,
    get_customer_full_info,
    suspend_customer,
    activate_customer,
    get_system_stats,
    get_ai_stats,
    get_all_active_customers,
)
from app.services.subscription.plans import get_plan
from app.services.subscription.service import calculate_days_remaining
from app.services.ai_token_service import add_purchased_tokens
from app.bot.keyboards.admin import (
    get_customers_menu_keyboard,
    get_customer_detail_keyboard,
    get_customers_list_keyboard,
    get_broadcast_confirm_keyboard,
    get_cancel_admin_keyboard,
)
from app.bot.states.user_state import (
    UserState,
    set_user_state,
    get_user_state,
    get_user_data,
    clear_user_state,
)
from app.utils.logger import log


CUSTOMERS_PER_PAGE = 8


def _is_admin(user_id: int) -> bool:
    """چک کن آیا کاربر ادمینه"""
    return user_id == settings.ADMIN_CHAT_ID


# ═══════════════════════════════════════════════
# منوی مشتریان
# ═══════════════════════════════════════════════

async def admin_customers_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش منوی مدیریت مشتریان"""
    user = update.effective_user
    if not _is_admin(user.id):
        return

    async with AsyncSessionLocal() as session:
        _, total = await get_customers_by_status(session, "all", 0, 1)

    await update.message.reply_text(
        f"👥 مدیریت مشتریان\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📊 تعداد کل مشتریان: {total}\n"
        f"━━━━━━━━━━━━━━━",
        reply_markup=get_customers_menu_keyboard(),
    )


async def admin_customers_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بازگشت به منوی مشتریان"""
    query = update.callback_query
    await query.answer()

    if not _is_admin(query.from_user.id):
        return

    async with AsyncSessionLocal() as session:
        _, total = await get_customers_by_status(session, "all", 0, 1)

    await query.edit_message_text(
        f"👥 مدیریت مشتریان\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📊 تعداد کل مشتریان: {total}\n"
        f"━━━━━━━━━━━━━━━",
        reply_markup=get_customers_menu_keyboard(),
    )


# ═══════════════════════════════════════════════
# لیست مشتریان (با فیلتر)
# ═══════════════════════════════════════════════

async def admin_customers_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    نمایش لیست مشتریان با فیلتر و صفحه‌بندی
    callback_data: admin_customers_{filter}_{page}
    مثال: admin_customers_active_0
    """
    query = update.callback_query
    await query.answer()

    if not _is_admin(query.from_user.id):
        return

    # استخراج فیلتر و صفحه
    parts = query.data.replace("admin_customers_", "").split("_")
    filter_type = parts[0]  # list | active | pending | suspended
    try:
        page = int(parts[1])
    except (ValueError, IndexError):
        page = 0

    # تعیین وضعیت
    status_map = {
        "list": "all",
        "active": "active",
        "pending": "pending",
        "suspended": "suspended",
    }
    status = status_map.get(filter_type, "all")

    async with AsyncSessionLocal() as session:
        customers, total = await get_customers_by_status(
            session, status, page, CUSTOMERS_PER_PAGE
        )

    if not customers:
        await query.edit_message_text(
            f"📋 لیست مشتریان ({filter_type})\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"❌ هیچ مشتری‌ای پیدا نشد.",
            reply_markup=get_customers_menu_keyboard(),
        )
        return

    total_pages = (total + CUSTOMERS_PER_PAGE - 1) // CUSTOMERS_PER_PAGE

    filter_names = {
        "list": "همه",
        "active": "فعال",
        "pending": "در انتظار",
        "suspended": "مسدود",
    }

    text = (
        f"📋 لیست مشتریان - {filter_names.get(filter_type, filter_type)}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📄 صفحه {page + 1} از {total_pages}\n"
        f"📊 تعداد کل: {total}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"روی نام مشتری کلیک کنید:"
    )

    await query.edit_message_text(
        text,
        reply_markup=get_customers_list_keyboard(
            customers=customers,
            page=page,
            total_pages=total_pages,
            filter_type=filter_type,
        ),
    )


# ═══════════════════════════════════════════════
# جزئیات یک مشتری
# ═══════════════════════════════════════════════

async def admin_customer_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش جزئیات یک مشتری"""
    query = update.callback_query
    await query.answer()

    if not _is_admin(query.from_user.id):
        return

    customer_id = int(query.data.replace("admin_customer_view_", ""))
    await _show_customer_detail(query, customer_id)

# ═══════════════════════════════════════════════
# عملیات روی مشتری
# ═══════════════════════════════════════════════

async def admin_customer_suspend_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """مسدود کردن مشتری"""
    query = update.callback_query
    await query.answer()

    if not _is_admin(query.from_user.id):
        return

    customer_id = int(query.data.replace("admin_customer_suspend_", ""))

    async with AsyncSessionLocal() as session:
        customer = await suspend_customer(session, customer_id)

    if not customer:
        await query.edit_message_text("❌ مشتری پیدا نشد!")
        return

    # اطلاع به مشتری
    try:
        await context.bot.send_message(
            chat_id=customer.telegram_user_id,
            text=(
                "⛔ حساب شما توسط ادمین مسدود شد.\n\n"
                "برای اطلاعات بیشتر با پشتیبانی تماس بگیرید."
            ),
        )
    except Exception as e:
        log.error(f"خطا در اطلاع به مشتری: {e}")

    # نمایش مجدد جزئیات مشتری
    await _show_customer_detail(query, customer_id)


async def admin_customer_activate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """فعال کردن مشتری"""
    query = update.callback_query
    await query.answer()

    if not _is_admin(query.from_user.id):
        return

    customer_id = int(query.data.replace("admin_customer_activate_", ""))

    async with AsyncSessionLocal() as session:
        customer = await activate_customer(session, customer_id)

    if not customer:
        await query.edit_message_text("❌ مشتری پیدا نشد!")
        return

    try:
        await context.bot.send_message(
            chat_id=customer.telegram_user_id,
            text=(
                "✅ حساب شما مجدداً فعال شد!\n\n"
                "می‌تونید از خدمات ربات استفاده کنید."
            ),
        )
    except Exception as e:
        log.error(f"خطا در اطلاع به مشتری: {e}")

    # نمایش مجدد جزئیات مشتری
    await _show_customer_detail(query, customer_id)


async def _show_customer_detail(query, customer_id: int) -> None:
    """نمایش جزئیات مشتری (helper function)"""
    async with AsyncSessionLocal() as session:
        info = await get_customer_full_info(session, customer_id)

    if not info:
        await query.edit_message_text("❌ مشتری پیدا نشد!")
        return

    customer = info["customer"]
    subscription = info["subscription"]

    name = customer.first_name or ""
    if customer.last_name:
        name += f" {customer.last_name}"
    username_text = f"@{customer.username}" if customer.username else "ندارد"

    status_emoji = {
        CustomerStatus.ACTIVE: "✅ فعال",
        CustomerStatus.PENDING: "⏳ در انتظار تایید",
        CustomerStatus.SUSPENDED: "⛔ مسدود",
        CustomerStatus.REJECTED: "❌ رد شده",
    }
    status_text = status_emoji.get(customer.customer_status, "نامشخص")

    text = (
        f"👤 جزئیات مشتری\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📛 نام: {name}\n"
        f"🔗 یوزرنیم: {username_text}\n"
        f"🆔 آیدی تلگرام: {customer.telegram_user_id}\n"
        f"🎯 وضعیت: {status_text}\n"
        f"📅 عضویت: {customer.created_at.strftime('%Y/%m/%d')}\n"
        f"🏢 کسب‌وکار: {customer.business_type_key or 'نامشخص'}\n"
        f"━━━━━━━━━━━━━━━\n"
    )

    if subscription:
        plan = get_plan(subscription.plan_key)
        days = calculate_days_remaining(subscription)
        text += (
            f"💳 اشتراک: {plan.emoji} {plan.name_fa}\n"
            f"📅 پایان: {subscription.end_at.strftime('%Y/%m/%d')}\n"
            f"⏳ باقیمانده: {days} روز\n"
        )
    else:
        text += f"💳 اشتراک: ❌ ندارد\n"

    text += (
        f"━━━━━━━━━━━━━━━\n"
        f"📢 کانال‌ها: {info['channels_count']}\n"
        f"📦 محصولات: {info['products_count']}\n"
        f"🤖 توکن AI باقیمانده: {info['ai_tokens_remaining']}\n"
        f"🎯 مصرف AI کل: {info['ai_usage_count']} بار\n"
        f"━━━━━━━━━━━━━━━"
    )

    is_active = customer.customer_status == CustomerStatus.ACTIVE

    await query.edit_message_text(
        text,
        reply_markup=get_customer_detail_keyboard(customer_id, is_active),
    )


async def admin_customer_activate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """فعال کردن مشتری"""
    query = update.callback_query
    await query.answer()

    if not _is_admin(query.from_user.id):
        return

    customer_id = int(query.data.replace("admin_customer_activate_", ""))

    async with AsyncSessionLocal() as session:
        customer = await activate_customer(session, customer_id)

    if not customer:
        await query.edit_message_text("❌ مشتری پیدا نشد!")
        return

    try:
        await context.bot.send_message(
            chat_id=customer.telegram_user_id,
            text=(
                "✅ حساب شما مجدداً فعال شد!\n\n"
                "می‌تونید از خدمات ربات استفاده کنید."
            ),
        )
    except Exception as e:
        log.error(f"خطا در اطلاع به مشتری: {e}")

    await query.answer("✅ مشتری فعال شد", show_alert=True)

    await _show_customer_detail(query, customer_id)


# ═══════════════════════════════════════════════
# ارسال پیام به مشتری خاص
# ═══════════════════════════════════════════════

async def admin_customer_message_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """درخواست ارسال پیام به مشتری"""
    query = update.callback_query
    await query.answer()

    if not _is_admin(query.from_user.id):
        return

    customer_id = int(query.data.replace("admin_customer_message_", ""))

    set_user_state(
        query.from_user.id,
        UserState.ADMIN_SENDING_MESSAGE,
        data={"target_customer_id": customer_id},
    )

    await query.edit_message_text(
        f"💬 ارسال پیام به مشتری\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"لطفاً متن پیام رو ارسال کنید.\n\n"
        f"⚠️ این پیام مستقیم به مشتری ارسال میشه.",
        reply_markup=get_cancel_admin_keyboard(),
    )


async def admin_message_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    دریافت متن پیام ادمین برای ارسال به مشتری
    فقط وقتی state = ADMIN_SENDING_MESSAGE
    """
    user = update.effective_user
    if not _is_admin(user.id):
        return

    if get_user_state(user.id) != UserState.ADMIN_SENDING_MESSAGE:
        return

    user_data = get_user_data(user.id)
    target_id = user_data.get("target_customer_id")

    if not target_id:
        await update.message.reply_text("❌ خطا!")
        clear_user_state(user.id)
        return

    message_text = update.message.text

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_id(session, target_id)

    if not customer:
        await update.message.reply_text("❌ مشتری پیدا نشد!")
        clear_user_state(user.id)
        return

    # ارسال به مشتری
    try:
        await context.bot.send_message(
            chat_id=customer.telegram_user_id,
            text=(
                f"📢 پیام از پشتیبانی:\n"
                f"━━━━━━━━━━━━━━━\n"
                f"{message_text}\n"
                f"━━━━━━━━━━━━━━━"
            ),
        )
        await update.message.reply_text(
            f"✅ پیام به {customer.first_name or 'مشتری'} ارسال شد."
        )
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ارسال: {str(e)[:100]}")
        log.error(f"خطا در ارسال پیام ادمین: {e}")

    clear_user_state(user.id)


# ═══════════════════════════════════════════════
# هدیه توکن AI
# ═══════════════════════════════════════════════

async def admin_customer_gift_tokens_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """درخواست تعداد توکن هدیه"""
    query = update.callback_query
    await query.answer()

    if not _is_admin(query.from_user.id):
        return

    customer_id = int(query.data.replace("admin_customer_gift_tokens_", ""))

    set_user_state(
        query.from_user.id,
        UserState.ADMIN_GIFTING_TOKENS,
        data={"target_customer_id": customer_id},
    )

    await query.edit_message_text(
        f"🎁 هدیه توکن AI\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"لطفاً تعداد توکن رو ارسال کنید (عدد):\n\n"
        f"مثال: 50",
        reply_markup=get_cancel_admin_keyboard(),
    )


async def admin_gift_tokens_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دریافت تعداد توکن برای هدیه"""
    user = update.effective_user
    if not _is_admin(user.id):
        return

    if get_user_state(user.id) != UserState.ADMIN_GIFTING_TOKENS:
        return

    try:
        amount = int(update.message.text.strip())
        if amount <= 0 or amount > 10000:
            raise ValueError()
    except ValueError:
        await update.message.reply_text("❌ عدد نامعتبر! (باید ۱ تا ۱۰۰۰۰ باشه)")
        return

    user_data = get_user_data(user.id)
    target_id = user_data.get("target_customer_id")

    if not target_id:
        clear_user_state(user.id)
        return

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_id(session, target_id)
        if not customer:
            await update.message.reply_text("❌ مشتری پیدا نشد!")
            clear_user_state(user.id)
            return

        await add_purchased_tokens(session, target_id, amount)

    try:
        await context.bot.send_message(
            chat_id=customer.telegram_user_id,
            text=(
                f"🎁 هدیه از طرف پشتیبانی!\n"
                f"━━━━━━━━━━━━━━━\n"
                f"🤖 {amount} توکن AI به حساب شما اضافه شد\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"از منوی '🤖 توکن AI' موجودی خودتون رو ببینید."
            ),
        )
    except Exception as e:
        log.error(f"خطا در اطلاع به مشتری: {e}")

    await update.message.reply_text(
        f"✅ {amount} توکن به {customer.first_name or 'مشتری'} هدیه داده شد."
    )
    clear_user_state(user.id)


# ═══════════════════════════════════════════════
# آمار کلی
# ═══════════════════════════════════════════════

async def admin_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش آمار کلی سیستم"""
    user = update.effective_user
    if not _is_admin(user.id):
        return

    async with AsyncSessionLocal() as session:
        stats = await get_system_stats(session)

    # ساخت متن پلن‌ها
    plans_text = ""
    for plan_key, count in stats["subs_by_plan"].items():
        plan = get_plan(plan_key)
        if plan:
            plans_text += f"   • {plan.emoji} {plan.name_fa}: {count}\n"

    text = (
        f"📊 آمار کلی سیستم\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"👥 مشتریان:\n"
        f"├── 📌 کل: {stats['total_customers']}\n"
        f"├── ✅ فعال: {stats['active_customers']}\n"
        f"├── ⏳ در انتظار: {stats['pending_customers']}\n"
        f"└── ⛔ مسدود: {stats['suspended_customers']}\n\n"
        f"💳 اشتراک‌ها:\n"
        f"├── ✅ فعال: {stats['active_subscriptions']}\n"
        f"└── بر اساس پلن:\n"
        f"{plans_text}\n"
        f"📢 کانال‌های متصل: {stats['channels_count']}\n"
        f"📦 کل محصولات: {stats['products_count']}\n"
        f"🤖 کل استفاده AI: {stats['ai_usage_total']}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await update.message.reply_text(text)


# ═══════════════════════════════════════════════
# آمار AI
# ═══════════════════════════════════════════════

async def admin_ai_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش آمار AI"""
    user = update.effective_user
    if not _is_admin(user.id):
        return

    async with AsyncSessionLocal() as session:
        stats = await get_ai_stats(session)

    by_type_text = ""
    for utype, count in stats["by_type"].items():
        by_type_text += f"   • {utype}: {count}\n"

    text = (
        f"🤖 آمار AI\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"📊 استفاده کل:\n"
        f"├── 🎯 کل درخواست‌ها: {stats['total_usage']}\n"
        f"├── ✅ قبول شده: {stats['accepted_count']}\n"
        f"└── 📈 نرخ قبولی: {stats['accepted_rate']:.1f}%\n\n"
        f"📋 بر اساس نوع:\n"
        f"{by_type_text}\n"
        f"💳 توکن‌های تخصیص یافته:\n"
        f"├── 📅 ماهانه: {stats['monthly_tokens_allocated']}\n"
        f"└── 💰 خریداری شده: {stats['purchased_tokens_allocated']}\n"
        f"━━━━━━━━━━━━━━━"
    )

    await update.message.reply_text(text)


# ═══════════════════════════════════════════════
# ارسال همگانی
# ═══════════════════════════════════════════════

async def admin_broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """شروع فرآیند ارسال همگانی"""
    user = update.effective_user
    if not _is_admin(user.id):
        return

    async with AsyncSessionLocal() as session:
        customers = await get_all_active_customers(session)

    set_user_state(user.id, UserState.ADMIN_BROADCASTING)

    await update.message.reply_text(
        f"🔔 ارسال اعلان همگانی\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"📊 پیام به {len(customers)} مشتری فعال ارسال میشه\n\n"
        f"لطفاً متن پیام رو ارسال کنید:",
        reply_markup=get_cancel_admin_keyboard(),
    )


async def admin_broadcast_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دریافت متن broadcast و تایید"""
    user = update.effective_user
    if not _is_admin(user.id):
        return

    if get_user_state(user.id) != UserState.ADMIN_BROADCASTING:
        return

    text = update.message.text

    # ذخیره متن در state برای تایید
    set_user_state(
        user.id,
        UserState.ADMIN_BROADCASTING,
        data={"broadcast_text": text},
    )

    await update.message.reply_text(
        f"📢 پیش‌نمایش پیام:\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{text}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"آیا ارسال کنم؟",
        reply_markup=get_broadcast_confirm_keyboard(),
    )


async def admin_broadcast_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تایید و اجرای ارسال همگانی"""
    query = update.callback_query
    await query.answer()

    if not _is_admin(query.from_user.id):
        return

    user_data = get_user_data(query.from_user.id)
    text = user_data.get("broadcast_text", "")

    if not text:
        await query.edit_message_text("❌ متن پیدا نشد!")
        return

    await query.edit_message_text("🔄 در حال ارسال...")

    async with AsyncSessionLocal() as session:
        customers = await get_all_active_customers(session)

    sent = 0
    failed = 0

    broadcast_message = (
        f"📢 پیام از پشتیبانی:\n"
        f"━━━━━━━━━━━━━━━\n"
        f"{text}\n"
        f"━━━━━━━━━━━━━━━"
    )

    for customer in customers:
        try:
            await context.bot.send_message(
                chat_id=customer.telegram_user_id,
                text=broadcast_message,
            )
            sent += 1
        except Exception as e:
            failed += 1
            log.warning(f"خطا در ارسال به {customer.telegram_user_id}: {e}")

    clear_user_state(query.from_user.id)

    await query.edit_message_text(
        f"✅ ارسال کامل شد\n"
        f"━━━━━━━━━━━━━━━\n"
        f"✅ موفق: {sent}\n"
        f"❌ ناموفق: {failed}\n"
        f"━━━━━━━━━━━━━━━"
    )


async def admin_broadcast_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """لغو ارسال همگانی"""
    query = update.callback_query
    await query.answer()

    clear_user_state(query.from_user.id)

    await query.edit_message_text("❌ ارسال لغو شد.")


async def admin_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """لغو عمومی ادمین"""
    query = update.callback_query
    await query.answer()

    clear_user_state(query.from_user.id)

    await query.edit_message_text("❌ لغو شد.")


# ═══════════════════════════════════════════════
# جستجوی مشتری
# ═══════════════════════════════════════════════

async def admin_customer_search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """درخواست آیدی مشتری برای جستجو"""
    query = update.callback_query
    await query.answer()

    if not _is_admin(query.from_user.id):
        return

    set_user_state(query.from_user.id, UserState.ADMIN_SEARCHING_CUSTOMER)

    await query.edit_message_text(
        f"🔍 جستجوی مشتری\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"لطفاً آیدی عددی تلگرام مشتری رو ارسال کنید:\n"
        f"مثال: 123456789",
        reply_markup=get_cancel_admin_keyboard(),
    )


async def admin_search_customer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """جستجو با آیدی تلگرام"""
    user = update.effective_user
    if not _is_admin(user.id):
        return

    if get_user_state(user.id) != UserState.ADMIN_SEARCHING_CUSTOMER:
        return

    try:
        telegram_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ آیدی نامعتبر! باید عدد باشه.")
        return

    from app.services.customer_service import get_customer_by_telegram_id

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, telegram_id)

    if not customer:
        await update.message.reply_text(
            "❌ مشتری با این آیدی پیدا نشد."
        )
        clear_user_state(user.id)
        return

    clear_user_state(user.id)

    # نمایش جزئیات مثل callback
    async with AsyncSessionLocal() as session:
        info = await get_customer_full_info(session, customer.id)

    if not info:
        await update.message.reply_text("❌ خطا!")
        return

    customer_obj = info["customer"]
    subscription = info["subscription"]

    name = customer_obj.first_name or ""
    if customer_obj.last_name:
        name += f" {customer_obj.last_name}"
    username_text = f"@{customer_obj.username}" if customer_obj.username else "ندارد"

    status_emoji = {
        CustomerStatus.ACTIVE: "✅ فعال",
        CustomerStatus.PENDING: "⏳ در انتظار",
        CustomerStatus.SUSPENDED: "⛔ مسدود",
        CustomerStatus.REJECTED: "❌ رد شده",
    }
    status_text = status_emoji.get(customer_obj.customer_status, "نامشخص")

    text = (
        f"👤 جزئیات مشتری\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📛 نام: {name}\n"
        f"🔗 یوزرنیم: {username_text}\n"
        f"🆔 آیدی: {customer_obj.telegram_user_id}\n"
        f"🎯 وضعیت: {status_text}\n"
        f"━━━━━━━━━━━━━━━\n"
    )

    if subscription:
        plan = get_plan(subscription.plan_key)
        days = calculate_days_remaining(subscription)
        text += f"💳 اشتراک: {plan.emoji} {plan.name_fa} ({days} روز)\n"
    else:
        text += f"💳 اشتراک: ❌ ندارد\n"

    text += (
        f"📢 کانال‌ها: {info['channels_count']}\n"
        f"📦 محصولات: {info['products_count']}\n"
        f"🤖 توکن باقیمانده: {info['ai_tokens_remaining']}\n"
    )

    is_active = customer_obj.customer_status == CustomerStatus.ACTIVE

    await update.message.reply_text(
        text,
        reply_markup=get_customer_detail_keyboard(customer_obj.id, is_active),
    )