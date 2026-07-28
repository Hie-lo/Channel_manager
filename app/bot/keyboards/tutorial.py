"""
کیبوردهای بخش آموزش
"""

from telegram import InlineKeyboardMarkup, InlineKeyboardButton


CATEGORIES = {
    "general": "🚀 راهنماهای عمومی",
    "channel": "📢 کانال",
    "upload": "📤 آپلود محصولات",
    "sheet": "📊 Google Sheet",
    "ai": "🤖 هوش مصنوعی",
    "subscription": "💳 اشتراک",
    "faq": "❓ سوالات متداول",
}


def get_tutorial_main_menu() -> InlineKeyboardMarkup:
    """منوی اصلی آموزش‌ها"""
    keyboard = []

    for cat_key, cat_name in CATEGORIES.items():
        keyboard.append([
            InlineKeyboardButton(cat_name, callback_data=f"tut_cat_{cat_key}")
        ])

    return InlineKeyboardMarkup(keyboard)


def get_category_tutorials_keyboard(tutorials: list) -> InlineKeyboardMarkup:
    """لیست آموزش‌های یک دسته"""
    keyboard = []

    for tut in tutorials:
        # برای FAQ، سوال رو نمایش بده
        if tut.content_type == "faq" and tut.faq_question:
            display = f"❓ {tut.faq_question[:50]}"
        else:
            display = tut.title[:60]

        keyboard.append([
            InlineKeyboardButton(display, callback_data=f"tut_view_{tut.key}")
        ])

    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت به دسته‌ها", callback_data="tut_menu")
    ])

    return InlineKeyboardMarkup(keyboard)


def get_tutorial_back_keyboard(category: str) -> InlineKeyboardMarkup:
    """دکمه بازگشت بعد از نمایش آموزش"""
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"tut_cat_{category}")],
        [InlineKeyboardButton("🏠 منوی آموزش", callback_data="tut_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_inline_help_keyboard(tutorial_key: str) -> InlineKeyboardMarkup:
    """
    کیبورد کوچیک برای دکمه راهنمای درون‌مرحله‌ای
    (کنار دیگر دکمه‌ها استفاده میشه)
    """
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❓ راهنما", callback_data=f"tut_inline_{tutorial_key}")
    ]])