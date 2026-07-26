"""
کیبوردهای مربوط به اشتراک و پرداخت
"""

from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from app.services.subscription.plans import (
    get_all_plans,
    get_plan,
    format_price,
)


def get_subscription_menu_keyboard(has_active_sub: bool) -> InlineKeyboardMarkup:
    """منوی اصلی اشتراک"""
    keyboard = []

    if has_active_sub:
        keyboard.append([
            InlineKeyboardButton("📊 وضعیت اشتراک من", callback_data="sub_status")
        ])
        keyboard.append([
            InlineKeyboardButton("🔄 تمدید / ارتقا", callback_data="sub_buy")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("💳 خرید اشتراک", callback_data="sub_buy")
        ])

    return InlineKeyboardMarkup(keyboard)


def get_plans_keyboard() -> InlineKeyboardMarkup:
    """نمایش لیست پلن‌ها"""
    keyboard = []

    for plan in get_all_plans():
        text = f"{plan.emoji} {plan.name_fa} - {format_price(plan.price_monthly)} ت/ماه"
        keyboard.append([
            InlineKeyboardButton(text, callback_data=f"sub_plan_{plan.key}")
        ])

    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت", callback_data="sub_menu")
    ])

    return InlineKeyboardMarkup(keyboard)


def get_duration_keyboard(plan_key: str) -> InlineKeyboardMarkup:
    """انتخاب مدت اشتراک"""
    plan = get_plan(plan_key)
    if not plan:
        return InlineKeyboardMarkup([])

    keyboard = [
        [InlineKeyboardButton(
            f"۱ ماهه - {format_price(plan.price_monthly)} ت",
            callback_data=f"sub_dur_{plan_key}_monthly"
        )],
        [InlineKeyboardButton(
            f"۳ ماهه - {format_price(plan.price_quarterly)} ت (💰 تخفیف)",
            callback_data=f"sub_dur_{plan_key}_quarterly"
        )],
        [InlineKeyboardButton(
            f"۶ ماهه - {format_price(plan.price_half_yearly)} ت (💰💰 تخفیف بیشتر)",
            callback_data=f"sub_dur_{plan_key}_half_yearly"
        )],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="sub_buy")],
    ]

    return InlineKeyboardMarkup(keyboard)


def get_cancel_payment_keyboard() -> InlineKeyboardMarkup:
    """لغو فرآیند پرداخت"""
    keyboard = [
        [InlineKeyboardButton("❌ لغو پرداخت", callback_data="sub_cancel_payment")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_payment_confirmation_keyboard(subscription_id: int) -> InlineKeyboardMarkup:
    """دکمه‌های تایید/رد پرداخت برای ادمین"""
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ تایید پرداخت",
                callback_data=f"sub_admin_approve_{subscription_id}"
            ),
            InlineKeyboardButton(
                "❌ رد",
                callback_data=f"sub_admin_reject_{subscription_id}"
            ),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)