"""
دکمه‌های منوی اصلی ربات
"""

from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_customer_main_menu() -> ReplyKeyboardMarkup:
    """منوی اصلی مشتری"""
    keyboard = [
        [KeyboardButton("📤 آپلود محصولات"), KeyboardButton("📦 مدیریت محصولات")],
        [KeyboardButton("📢 مدیریت کانال"), KeyboardButton("📊 آمار و گزارش")],
        [KeyboardButton("🤖 توکن AI"), KeyboardButton("💳 اشتراک من")],
        [KeyboardButton("⚙️ تنظیمات"), KeyboardButton("📚 آموزش و راهنما")],
        [KeyboardButton("💬 پشتیبانی")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


def get_admin_main_menu() -> ReplyKeyboardMarkup:
    """منوی اصلی سوپر ادمین"""
    keyboard = [
        [KeyboardButton("👥 مدیریت مشتریان"), KeyboardButton("💳 مدیریت اشتراک‌ها")],
        [KeyboardButton("🏢 مدیریت کسب‌وکارها"), KeyboardButton("📊 آمار کلی")],
        [KeyboardButton("🔔 ارسال اعلان"), KeyboardButton("🔧 تنظیمات سیستم")],
        [KeyboardButton("📚 مدیریت آموزش‌ها")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


def get_business_type_keyboard() -> InlineKeyboardMarkup:
    """دکمه‌های انتخاب نوع کسب‌وکار"""
    keyboard = [
        [InlineKeyboardButton("💻 فروش لپتاپ و کامپیوتر", callback_data="biz_laptop_store")],
        [InlineKeyboardButton("📱 فروش موبایل و تبلت", callback_data="biz_mobile_store")],
        [InlineKeyboardButton("👕 پوشاک", callback_data="biz_clothing_store")],
        [InlineKeyboardButton("📦 سایر", callback_data="biz_other")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_pending_approval_keyboard(customer_telegram_id: int) -> InlineKeyboardMarkup:
    """دکمه‌های تایید/رد مشتری جدید برای ادمین"""
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ تایید",
                callback_data=f"approve_{customer_telegram_id}"
            ),
            InlineKeyboardButton(
                "❌ رد",
                callback_data=f"reject_{customer_telegram_id}"
            ),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """دکمه لغو عملیات"""
    keyboard = [
        [InlineKeyboardButton("❌ لغو", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)