"""
کیبوردهای مربوط به مدیریت کانال
"""

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from app.database.models import Channel


def get_channel_management_keyboard() -> InlineKeyboardMarkup:
    """منوی مدیریت کانال"""
    keyboard = [
        [InlineKeyboardButton("➕ اتصال کانال جدید", callback_data="channel_add")],
        [InlineKeyboardButton("📋 لیست کانال‌های من", callback_data="channel_list")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_channel_list_keyboard(channels: list[Channel]) -> InlineKeyboardMarkup:
    """لیست کانال‌ها با دکمه حذف"""
    keyboard = []

    for channel in channels:
        # نمایش نام کانال
        display_name = channel.channel_identifier
        keyboard.append([
            InlineKeyboardButton(
                f"📢 {display_name}",
                callback_data=f"channel_info_{channel.id}"
            ),
            InlineKeyboardButton(
                "❌ حذف",
                callback_data=f"channel_delete_{channel.id}"
            ),
        ])

    keyboard.append([
        InlineKeyboardButton("➕ اتصال کانال جدید", callback_data="channel_add")
    ])
    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت", callback_data="channel_menu")
    ])

    return InlineKeyboardMarkup(keyboard)


def get_channel_delete_confirm_keyboard(channel_id: int) -> InlineKeyboardMarkup:
    """تایید حذف کانال"""
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ بله، حذف کن",
                callback_data=f"channel_delete_confirm_{channel_id}"
            ),
            InlineKeyboardButton(
                "❌ انصراف",
                callback_data="channel_list"
            ),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_cancel_channel_add_keyboard() -> InlineKeyboardMarkup:
    """لغو اضافه کردن کانال + راهنما"""
    keyboard = [
        [InlineKeyboardButton("❓ راهنمای اتصال کانال", callback_data="tut_inline_connect_channel")],
        [InlineKeyboardButton("❌ لغو", callback_data="channel_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)