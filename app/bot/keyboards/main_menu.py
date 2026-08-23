"""
دکمه‌های منوی اصلی ربات
"""

from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from app.business.config import get_all_businesses


def get_customer_main_menu() -> ReplyKeyboardMarkup:
    """منوی اصلی مشتری"""
    keyboard = [
        [KeyboardButton("📤 آپلود محصولات"), KeyboardButton("📦 مدیریت محصولات")],
        [KeyboardButton("📢 مدیریت کانال"), KeyboardButton("📊 اتصال Google Sheet")],
        [KeyboardButton("🤖 توکن AI"), KeyboardButton("💳 اشتراک من")],
        [KeyboardButton("⚙️ تنظیمات"), KeyboardButton("📚 آموزش و راهنما")],
        [KeyboardButton("💬 پشتیبانی")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)



def get_business_type_keyboard() -> InlineKeyboardMarkup:
    """
    دکمه‌های انتخاب نوع کسب‌وکار
    از روی BUSINESSES ساخته میشه (داینامیک)
    """
    keyboard = []

    for business in get_all_businesses():
        text = f"{business.emoji} {business.name_fa}"
        keyboard.append([
            InlineKeyboardButton(text, callback_data=f"biz_{business.key}")
        ])

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
    keyboard = [
        [InlineKeyboardButton("❌ لغو", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_start_unregistered_keyboard() -> InlineKeyboardMarkup:
    """دکمه‌های اولیه برای فردی که هنوز ثبت نام نکرده"""
    keyboard = [
        [InlineKeyboardButton("🔗 اتصال به حساب موجود", callback_data="link_account_start")],
    ]
    return InlineKeyboardMarkup(keyboard)