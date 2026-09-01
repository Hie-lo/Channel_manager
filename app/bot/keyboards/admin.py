"""
کیبوردهای پنل ادمین
"""

from telegram import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)


def get_admin_main_menu() -> ReplyKeyboardMarkup:
    """منوی اصلی سوپر ادمین"""
    keyboard = [
        [KeyboardButton("👥 مدیریت مشتریان"), KeyboardButton("💳 مدیریت اشتراک‌ها")],
        [KeyboardButton("📊 آمار کلی"), KeyboardButton("🤖 آمار AI")],
        [KeyboardButton("🔔 ارسال اعلان"), KeyboardButton("🎨 قالب‌های پست")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_customers_menu_keyboard() -> InlineKeyboardMarkup:
    """منوی مدیریت مشتریان"""
    keyboard = [
        [InlineKeyboardButton("📋 لیست کل مشتریان", callback_data="admin_customers_list_0")],
        [InlineKeyboardButton("✅ مشتریان فعال", callback_data="admin_customers_active_0")],
        [InlineKeyboardButton("⏳ در انتظار تایید", callback_data="admin_customers_pending_0")],
        [InlineKeyboardButton("⛔ مسدود شده", callback_data="admin_customers_suspended_0")],
        [InlineKeyboardButton("🔍 جستجو با آیدی", callback_data="admin_customer_search")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_customer_detail_keyboard(customer_id: int, is_active: bool, has_subscription: bool = False) -> InlineKeyboardMarkup:
    """جزئیات یک مشتری با دکمه‌های عملیات"""
    keyboard = []

    # اعطا یا حذف اشتراک
    if has_subscription:
        keyboard.append([
            InlineKeyboardButton(
                "❌ حذف اشتراک",
                callback_data=f"admin_customer_revoke_sub_{customer_id}"
            )
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(
                "💳 اعطای اشتراک",
                callback_data=f"admin_customer_grant_sub_{customer_id}"
            )
        ])

    if is_active:
        keyboard.append([
            InlineKeyboardButton(
                "⛔ مسدود کردن",
                callback_data=f"admin_customer_suspend_{customer_id}"
            )
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(
                "✅ فعال کردن",
                callback_data=f"admin_customer_activate_{customer_id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "💬 ارسال پیام",
            callback_data=f"admin_customer_message_{customer_id}"
        )
    ])

    keyboard.append([
        InlineKeyboardButton(
            "🎁 هدیه توکن AI",
            callback_data=f"admin_customer_gift_tokens_{customer_id}"
        )
    ])

    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="admin_customers_list_0")
    ])

    return InlineKeyboardMarkup(keyboard)


def get_customers_list_keyboard(
    customers: list,
    page: int,
    total_pages: int,
    filter_type: str,
) -> InlineKeyboardMarkup:
    """لیست مشتریان با صفحه‌بندی"""
    keyboard = []

    for customer in customers:
        # نام از پلتفرم مبدا
        if customer.source_platform == "TELEGRAM":
            name = customer.telegram_first_name or customer.first_name or "بدون نام"
            username = customer.telegram_username or customer.username
        else:
            name = customer.bale_first_name or "بدون نام"
            username = customer.bale_username

        if username:
            name += f" (@{username})"

        # آیکون پلتفرم مبدا
        source_icon = "📱" if customer.source_platform == "TELEGRAM" else "💬"

        # اگه چند پلتفرم داره، نشون بده
        multi_indicator = ""
        if customer.telegram_user_id and customer.bale_user_id:
            multi_indicator = " 🔗"  # دو پلتفرم متصل

        keyboard.append([
            InlineKeyboardButton(
                f"{source_icon}{multi_indicator} {name[:30]}",
                callback_data=f"admin_customer_view_{customer.id}"
            )
        ])

    # دکمه‌های صفحه‌بندی
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                "⬅️ قبلی",
                callback_data=f"admin_customers_{filter_type}_{page - 1}"
            )
        )
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(
                "بعدی ➡️",
                callback_data=f"admin_customers_{filter_type}_{page + 1}"
            )
        )

    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت", callback_data="admin_customers_menu")
    ])

    return InlineKeyboardMarkup(keyboard)


def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """تایید ارسال همگانی"""
    keyboard = [
        [
            InlineKeyboardButton("✅ ارسال", callback_data="admin_broadcast_confirm"),
            InlineKeyboardButton("❌ لغو", callback_data="admin_broadcast_cancel"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_cancel_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ لغو", callback_data="admin_cancel")
    ]])

def get_subscriptions_menu_keyboard() -> InlineKeyboardMarkup:
    """منوی مدیریت اشتراک‌ها"""
    keyboard = [
        [InlineKeyboardButton("✅ اشتراک‌های فعال", callback_data="admin_subs_active_0")],
        [InlineKeyboardButton("⏳ در انتظار پرداخت", callback_data="admin_subs_pending_0")],
        [InlineKeyboardButton("⏰ در مهلت تمدید", callback_data="admin_subs_grace_0")],
        [InlineKeyboardButton("❌ منقضی شده", callback_data="admin_subs_expired_0")],
        [InlineKeyboardButton("💰 گزارش درآمد", callback_data="admin_subs_revenue")],
        [InlineKeyboardButton("📋 مشاهده پلن‌ها", callback_data="admin_subs_view_plans")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_subscriptions_list_keyboard(
    subscriptions: list,
    customers_map: dict,
    page: int,
    total_pages: int,
    filter_type: str,
) -> InlineKeyboardMarkup:
    """لیست اشتراک‌ها با صفحه‌بندی"""
    from app.services.subscription.plans import get_plan

    keyboard = []

    for sub in subscriptions:
        plan = get_plan(sub.plan_key)
        plan_emoji = plan.emoji if plan else "📦"
        plan_name = plan.name_fa if plan else sub.plan_key

        customer = customers_map.get(sub.customer_id)
        customer_name = customer.first_name if customer else "?"

        text = f"{plan_emoji} {plan_name} - {customer_name[:20]}"

        keyboard.append([
            InlineKeyboardButton(text, callback_data=f"admin_sub_view_{sub.id}")
        ])

    # صفحه‌بندی
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                "⬅️ قبلی",
                callback_data=f"admin_subs_{filter_type}_{page - 1}"
            )
        )
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(
                "بعدی ➡️",
                callback_data=f"admin_subs_{filter_type}_{page + 1}"
            )
        )

    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت", callback_data="admin_subs_menu")
    ])

    return InlineKeyboardMarkup(keyboard)


def get_subscription_detail_keyboard(subscription_id: int, status: str) -> InlineKeyboardMarkup:
    """کیبورد جزئیات یک اشتراک"""
    keyboard = []

    if status in ["ACTIVE", "GRACE", "EXPIRED"]:
        keyboard.append([
            InlineKeyboardButton("⏱ تمدید دستی", callback_data=f"admin_sub_extend_{subscription_id}")
        ])

    if status == "PENDING":
        keyboard.append([
            InlineKeyboardButton("🗑 حذف (رسید اشتباه)", callback_data=f"admin_sub_delete_{subscription_id}")
        ])

    if status == "ACTIVE":
        keyboard.append([
            InlineKeyboardButton("❌ لغو اشتراک", callback_data=f"admin_sub_cancel_{subscription_id}")
        ])

    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="admin_subs_menu")
    ])

    return InlineKeyboardMarkup(keyboard)


def get_extend_days_keyboard(subscription_id: int) -> InlineKeyboardMarkup:
    """کیبورد انتخاب تعداد روز برای تمدید"""
    keyboard = [
        [
            InlineKeyboardButton("۷ روز", callback_data=f"admin_sub_extend_days_{subscription_id}_7"),
            InlineKeyboardButton("۱۵ روز", callback_data=f"admin_sub_extend_days_{subscription_id}_15"),
        ],
        [
            InlineKeyboardButton("۳۰ روز", callback_data=f"admin_sub_extend_days_{subscription_id}_30"),
            InlineKeyboardButton("۹۰ روز", callback_data=f"admin_sub_extend_days_{subscription_id}_90"),
        ],
        [
            InlineKeyboardButton("۱۸۰ روز", callback_data=f"admin_sub_extend_days_{subscription_id}_180"),
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin_sub_view_{subscription_id}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_cancel_confirm_keyboard(subscription_id: int) -> InlineKeyboardMarkup:
    """تایید لغو اشتراک"""
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ بله، لغو کن",
                callback_data=f"admin_sub_cancel_confirm_{subscription_id}"
            ),
            InlineKeyboardButton(
                "❌ انصراف",
                callback_data=f"admin_sub_view_{subscription_id}"
            ),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_delete_confirm_keyboard(subscription_id: int) -> InlineKeyboardMarkup:
    """تایید حذف اشتراک"""
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ بله، حذف کن",
                callback_data=f"admin_sub_delete_confirm_{subscription_id}"
            ),
            InlineKeyboardButton(
                "❌ انصراف",
                callback_data=f"admin_sub_view_{subscription_id}"
            ),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)



def get_grant_sub_plan_keyboard(customer_id: int) -> InlineKeyboardMarkup:
    """کیبورد انتخاب پلن برای اعطای اشتراک"""
    from app.services.subscription.plans import get_all_plans

    keyboard = []
    for plan in get_all_plans():
        keyboard.append([
            InlineKeyboardButton(
                f"{plan.emoji} {plan.name_fa}",
                callback_data=f"admin_customer_grant_sub_plan_{customer_id}_{plan.key}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin_customer_view_{customer_id}")
    ])

    return InlineKeyboardMarkup(keyboard)


def get_grant_sub_duration_keyboard(customer_id: int, plan_key: str) -> InlineKeyboardMarkup:
    """کیبورد انتخاب مدت زمان اشتراک"""
    durations = [
        ("7 روز (آزمایشی)", 7),
        ("30 روز (1 ماه)", 30),
        ("90 روز (3 ماه)", 90),
        ("180 روز (6 ماه)", 180),
        ("365 روز (1 سال)", 365),
    ]

    keyboard = []
    for label, days in durations:
        keyboard.append([
            InlineKeyboardButton(
                label,
                callback_data=f"admin_customer_grant_sub_confirm_{customer_id}_{plan_key}_{days}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin_customer_grant_sub_{customer_id}")
    ])

    return InlineKeyboardMarkup(keyboard)


def get_revoke_sub_confirm_keyboard(customer_id: int) -> InlineKeyboardMarkup:
    """تایید حذف اشتراک"""
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ بله، حذف شود",
                callback_data=f"admin_customer_revoke_sub_confirm_{customer_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "❌ انصراف",
                callback_data=f"admin_customer_view_{customer_id}"
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
