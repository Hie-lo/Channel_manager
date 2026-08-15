"""
هندلرهای مدیریت اشتراک‌ها (فقط ادمین)
"""

from telegram import Update
from telegram.ext import ContextTypes

from app.config import settings
from app.database.connection import AsyncSessionLocal
from app.database.models import SubscriptionStatus, Customer
from app.services.admin_service import (
    get_subscriptions_by_status,
    get_subscription_by_id,
    extend_subscription_manual,
    cancel_subscription,
    delete_subscription,
    get_revenue_stats,
    get_customer_of_subscription,
)
from app.services.subscription.plans import (
    get_plan,
    get_all_plans,
    format_price,
)
from app.services.subscription.service import calculate_days_remaining
from app.bot.keyboards.admin import (
    get_subscriptions_menu_keyboard,
    get_subscriptions_list_keyboard,
    get_subscription_detail_keyboard,
    get_extend_days_keyboard,
    get_cancel_confirm_keyboard,
    get_delete_confirm_keyboard,
)
from app.utils.logger import log
from sqlalchemy import select


SUBS_PER_PAGE = 8


def _is_admin(user_id: int) -> bool:
    from app.utils.admin_check import is_admin
    return is_admin(user_id)


# ═══════════════════════════════════════════════
# منوی اشتراک‌ها
# ═══════════════════════════════════════════════

async def admin_subs_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """منوی مدیریت اشتراک‌ها"""
    user = update.effective_user
    if not _is_admin(user.id):
        return

    async with AsyncSessionLocal() as session:
        _, active_count = await get_subscriptions_by_status(session, "active", 0, 1)
        _, pending_count = await get_subscriptions_by_status(session, "pending", 0, 1)

    await update.message.reply_text(
        f"💳 مدیریت اشتراک‌ها\n"
        f"━━━━━━━━━━━━━━━\n"
        f"✅ فعال: {active_count}\n"
        f"⏳ در انتظار: {pending_count}\n"
        f"━━━━━━━━━━━━━━━",
        reply_markup=get_subscriptions_menu_keyboard(),
    )


async def admin_subs_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """بازگشت به منوی اشتراک‌ها"""
    query = update.callback_query
    await query.answer()

    if not _is_admin(query.from_user.id):
        return

    async with AsyncSessionLocal() as session:
        _, active_count = await get_subscriptions_by_status(session, "active", 0, 1)
        _, pending_count = await get_subscriptions_by_status(session, "pending", 0, 1)

    await query.edit_message_text(
        f"💳 مدیریت اشتراک‌ها\n"
        f"━━━━━━━━━━━━━━━\n"
        f"✅ فعال: {active_count}\n"
        f"⏳ در انتظار: {pending_count}\n"
        f"━━━━━━━━━━━━━━━",
        reply_markup=get_subscriptions_menu_keyboard(),
    )


# ═══════════════════════════════════════════════
# لیست اشتراک‌ها
# ═══════════════════════════════════════════════

async def admin_subs_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    لیست اشتراک‌ها با فیلتر
    callback_data: admin_subs_{filter}_{page}
    """
    query = update.callback_query
    await query.answer()

    if not _is_admin(query.from_user.id):
        return

    parts = query.data.replace("admin_subs_", "").split("_")
    filter_type = parts[0]  # active | pending | expired | grace
    try:
        page = int(parts[1])
    except (ValueError, IndexError):
        page = 0

    async with AsyncSessionLocal() as session:
        subscriptions, total = await get_subscriptions_by_status(
            session, filter_type, page, SUBS_PER_PAGE
        )

        # گرفتن اطلاعات مشتری‌ها
        customer_ids = [s.customer_id for s in subscriptions]
        customers_result = await session.execute(
            select(Customer).where(Customer.id.in_(customer_ids))
        )
        customers = list(customers_result.scalars().all())
        customers_map = {c.id: c for c in customers}

    if not subscriptions:
        filter_names = {
            "active": "فعال",
            "pending": "در انتظار",
            "expired": "منقضی",
            "grace": "در مهلت",
        }
        await query.edit_message_text(
            f"📋 اشتراک‌های {filter_names.get(filter_type, filter_type)}\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"❌ هیچ اشتراکی پیدا نشد.",
            reply_markup=get_subscriptions_menu_keyboard(),
        )
        return

    total_pages = (total + SUBS_PER_PAGE - 1) // SUBS_PER_PAGE

    filter_names = {
        "active": "✅ فعال",
        "pending": "⏳ در انتظار پرداخت",
        "expired": "❌ منقضی شده",
        "grace": "⏰ در مهلت تمدید",
    }

    text = (
        f"📋 اشتراک‌های {filter_names.get(filter_type, filter_type)}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📄 صفحه {page + 1} از {total_pages}\n"
        f"📊 تعداد کل: {total}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"روی اشتراک کلیک کنید:"
    )

    await query.edit_message_text(
        text,
        reply_markup=get_subscriptions_list_keyboard(
            subscriptions=subscriptions,
            customers_map=customers_map,
            page=page,
            total_pages=total_pages,
            filter_type=filter_type,
        ),
    )


# ═══════════════════════════════════════════════
# جزئیات یک اشتراک
# ═══════════════════════════════════════════════

async def admin_sub_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش جزئیات یک اشتراک"""
    query = update.callback_query
    await query.answer()

    if not _is_admin(query.from_user.id):
        return

    subscription_id = int(query.data.replace("admin_sub_view_", ""))
    await _show_subscription_detail(query, subscription_id)


async def _show_subscription_detail(query, subscription_id: int) -> None:
    """نمایش جزئیات اشتراک (helper)"""
    async with AsyncSessionLocal() as session:
        subscription = await get_subscription_by_id(session, subscription_id)
        if not subscription:
            await query.edit_message_text("❌ اشتراک پیدا نشد!")
            return

        customer = await get_customer_of_subscription(session, subscription)

    plan = get_plan(subscription.plan_key)
    days_remaining = calculate_days_remaining(subscription)

    status_emoji = {
        SubscriptionStatus.ACTIVE: "✅ فعال",
        SubscriptionStatus.PENDING: "⏳ در انتظار پرداخت",
        SubscriptionStatus.GRACE: "⏰ در مهلت تمدید",
        SubscriptionStatus.EXPIRED: "❌ منقضی شده",
        SubscriptionStatus.SUSPENDED: "⛔ معلق",
    }
    status_text = status_emoji.get(subscription.status, "نامشخص")

    text = (
        f"💳 جزئیات اشتراک #{subscription.id}\n"
        f"━━━━━━━━━━━━━━━\n"
    )

    if customer:
        name = customer.first_name or "بدون نام"
        username = f"@{customer.username}" if customer.username else "ندارد"
        text += (
            f"👤 مشتری: {name}\n"
            f"🔗 یوزرنیم: {username}\n"
            f"🆔 آیدی: {customer.telegram_user_id}\n"
        )

    text += (
        f"━━━━━━━━━━━━━━━\n"
        f"📦 پلن: {plan.emoji if plan else '?'} {plan.name_fa if plan else subscription.plan_key}\n"
        f"🎯 وضعیت: {status_text}\n"
        f"📅 شروع: {subscription.start_at.strftime('%Y/%m/%d')}\n"
        f"📅 پایان: {subscription.end_at.strftime('%Y/%m/%d')}\n"
        f"⏰ مهلت تمدید: {subscription.grace_end_at.strftime('%Y/%m/%d')}\n"
    )

    if subscription.status == SubscriptionStatus.ACTIVE:
        text += f"⏳ باقیمانده: {days_remaining} روز\n"

    if plan:
        text += (
            f"━━━━━━━━━━━━━━━\n"
            f"💰 قیمت ماهانه: {format_price(plan.price_monthly)} ت\n"
            f"📢 حداکثر کانال: {plan.max_channels if plan.max_channels < 9999 else 'نامحدود'}\n"
            f"📦 حداکثر محصول: {plan.max_products if plan.max_products < 9999 else 'نامحدود'}\n"
            f"🤖 توکن AI ماهانه: {plan.monthly_ai_tokens}\n"
        )

    text += f"━━━━━━━━━━━━━━━"

    await query.edit_message_text(
        text,
        reply_markup=get_subscription_detail_keyboard(
            subscription_id,
            subscription.status.value,
        ),
    )


# ═══════════════════════════════════════════════
# تمدید دستی
# ═══════════════════════════════════════════════

async def admin_sub_extend_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش گزینه‌های تمدید"""
    query = update.callback_query
    await query.answer()

    if not _is_admin(query.from_user.id):
        return

    subscription_id = int(query.data.replace("admin_sub_extend_", ""))

    await query.edit_message_text(
        f"⏱ تمدید دستی اشتراک #{subscription_id}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"چند روز به اشتراک اضافه بشه؟\n\n"
        f"💡 اگه اشتراک فعاله، به تاریخ پایان اضافه میشه.\n"
        f"💡 اگه منقضی شده، از الان محاسبه میشه.",
        reply_markup=get_extend_days_keyboard(subscription_id),
    )


async def admin_sub_extend_days_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """اعمال تمدید"""
    query = update.callback_query
    await query.answer()

    if not _is_admin(query.from_user.id):
        return

    # admin_sub_extend_days_{sub_id}_{days}
    parts = query.data.replace("admin_sub_extend_days_", "").split("_")
    if len(parts) != 2:
        return

    try:
        subscription_id = int(parts[0])
        days = int(parts[1])
    except ValueError:
        return

    async with AsyncSessionLocal() as session:
        subscription = await extend_subscription_manual(session, subscription_id, days)
        if not subscription:
            await query.edit_message_text("❌ خطا در تمدید!")
            return

        customer = await get_customer_of_subscription(session, subscription)

    # اطلاع به مشتری
    if customer:
        try:
            plan = get_plan(subscription.plan_key)
            await context.bot.send_message(
                chat_id=customer.telegram_user_id,
                text=(
                    f"🎁 اشتراک شما تمدید شد!\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"📦 پلن: {plan.emoji if plan else '?'} {plan.name_fa if plan else '?'}\n"
                    f"⏱ {days} روز اضافه شد\n"
                    f"📅 تاریخ جدید انقضا: {subscription.end_at.strftime('%Y/%m/%d')}\n"
                    f"━━━━━━━━━━━━━━━"
                ),
            )
        except Exception as e:
            log.error(f"خطا در اطلاع به مشتری: {e}")

    await query.answer(f"✅ {days} روز اضافه شد", show_alert=True)
    await _show_subscription_detail(query, subscription_id)


# ═══════════════════════════════════════════════
# لغو اشتراک
# ═══════════════════════════════════════════════

async def admin_sub_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """درخواست تایید لغو"""
    query = update.callback_query
    await query.answer()

    if not _is_admin(query.from_user.id):
        return

    subscription_id = int(query.data.replace("admin_sub_cancel_", ""))

    await query.edit_message_text(
        f"⚠️ لغو اشتراک #{subscription_id}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"با لغو این اشتراک:\n"
        f"├── مشتری فوراً غیرفعال میشه\n"
        f"├── تاریخ پایان به الان تغییر می‌کنه\n"
        f"└── امکان تمدید بعداً هست\n\n"
        f"آیا مطمئن هستید؟",
        reply_markup=get_cancel_confirm_keyboard(subscription_id),
    )


async def admin_sub_cancel_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تایید نهایی لغو"""
    query = update.callback_query
    await query.answer()

    if not _is_admin(query.from_user.id):
        return

    subscription_id = int(query.data.replace("admin_sub_cancel_confirm_", ""))

    async with AsyncSessionLocal() as session:
        subscription = await cancel_subscription(session, subscription_id)
        if not subscription:
            await query.edit_message_text("❌ خطا!")
            return

        customer = await get_customer_of_subscription(session, subscription)

    # اطلاع به مشتری
    if customer:
        try:
            await context.bot.send_message(
                chat_id=customer.telegram_user_id,
                text=(
                    "⚠️ اشتراک شما توسط ادمین لغو شد.\n"
                    "برای اطلاعات بیشتر با پشتیبانی تماس بگیرید."
                ),
            )
        except Exception as e:
            log.error(f"خطا در اطلاع: {e}")

    await query.answer("✅ اشتراک لغو شد", show_alert=True)
    await _show_subscription_detail(query, subscription_id)


# ═══════════════════════════════════════════════
# حذف اشتراک (PENDING اشتباه)
# ═══════════════════════════════════════════════

async def admin_sub_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """درخواست تایید حذف"""
    query = update.callback_query
    await query.answer()

    if not _is_admin(query.from_user.id):
        return

    subscription_id = int(query.data.replace("admin_sub_delete_", ""))

    await query.edit_message_text(
        f"⚠️ حذف اشتراک #{subscription_id}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"این عملیات:\n"
        f"├── اشتراک رو کاملاً حذف می‌کنه\n"
        f"├── فقط برای رسیدهای اشتباه استفاده کنید\n"
        f"└── قابل بازگردانی نیست\n\n"
        f"آیا مطمئن هستید؟",
        reply_markup=get_delete_confirm_keyboard(subscription_id),
    )


async def admin_sub_delete_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تایید نهایی حذف"""
    query = update.callback_query
    await query.answer()

    if not _is_admin(query.from_user.id):
        return

    subscription_id = int(query.data.replace("admin_sub_delete_confirm_", ""))

    async with AsyncSessionLocal() as session:
        # اول اطلاعات مشتری رو بگیر
        subscription = await get_subscription_by_id(session, subscription_id)
        customer = None
        if subscription:
            customer = await get_customer_of_subscription(session, subscription)

        success = await delete_subscription(session, subscription_id)

    if not success:
        await query.edit_message_text("❌ خطا در حذف!")
        return

    if customer:
        try:
            await context.bot.send_message(
                chat_id=customer.telegram_user_id,
                text=(
                    "❌ درخواست پرداخت شما رد شد.\n"
                    "لطفاً برای اطلاعات بیشتر با پشتیبانی تماس بگیرید."
                ),
            )
        except Exception as e:
            log.error(f"خطا در اطلاع: {e}")

    await query.edit_message_text(
        f"✅ اشتراک #{subscription_id} حذف شد.",
        reply_markup=get_subscriptions_menu_keyboard(),
    )


# ═══════════════════════════════════════════════
# گزارش درآمد
# ═══════════════════════════════════════════════

async def admin_subs_revenue_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """گزارش درآمد کل"""
    query = update.callback_query
    await query.answer()

    if not _is_admin(query.from_user.id):
        return

    async with AsyncSessionLocal() as session:
        stats = await get_revenue_stats(session)

    text = (
        f"💰 گزارش درآمد\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💵 درآمد کل: {format_price(stats['total_revenue'])} تومان\n"
        f"📊 تعداد اشتراک‌ها: {stats['total_subscriptions']}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"📈 بر اساس پلن:\n"
    )

    for plan_key, data in stats["revenue_by_plan"].items():
        plan = get_plan(plan_key)
        plan_name = f"{plan.emoji} {plan.name_fa}" if plan else plan_key
        text += (
            f"\n{plan_name}:\n"
            f"   📊 تعداد: {data['count']}\n"
            f"   💰 درآمد: {format_price(data['revenue'])} ت\n"
        )

    text += f"\n━━━━━━━━━━━━━━━"

    await query.edit_message_text(
        text,
        reply_markup=get_subscriptions_menu_keyboard(),
    )


# ═══════════════════════════════════════════════
# مشاهده پلن‌ها
# ═══════════════════════════════════════════════

async def admin_subs_view_plans_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش تنظیمات فعلی پلن‌ها"""
    query = update.callback_query
    await query.answer()

    if not _is_admin(query.from_user.id):
        return

    text = (
        f"📋 پلن‌های موجود\n"
        f"━━━━━━━━━━━━━━━\n\n"
    )

    for plan in get_all_plans():
        text += (
            f"{plan.emoji} <b>{plan.name_fa}</b>\n"
            f"├── 💰 ماهانه: {format_price(plan.price_monthly)} ت\n"
            f"├── 💰 ۳ ماهه: {format_price(plan.price_quarterly)} ت\n"
            f"├── 💰 ۶ ماهه: {format_price(plan.price_half_yearly)} ت\n"
            f"├── 📢 کانال: {plan.max_channels if plan.max_channels < 9999 else 'نامحدود'}\n"
            f"├── 📦 محصول: {plan.max_products if plan.max_products < 9999 else 'نامحدود'}\n"
            f"├── 🤖 توکن AI ماهانه: {plan.monthly_ai_tokens}\n"
            f"├── ✨ قالب سفارشی: {'✅' if plan.can_customize_template else '❌'}\n"
            f"├── 🤖 استفاده از AI: {'✅' if plan.can_use_ai else '❌'}\n"
            f"└── 🔔 گزارش لحظه‌ای: {'✅' if plan.realtime_reports else '❌'}\n\n"
        )

    text += (
        f"━━━━━━━━━━━━━━━\n"
        f"💡 برای تغییر مشخصات پلن‌ها، فایل زیر رو ادیت کنید:\n"
        f"<code>app/services/subscription/plans.py</code>\n\n"
        f"بعد ربات رو ری‌استارت کنید."
    )

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=get_subscriptions_menu_keyboard(),
    )