"""
کیبوردهای مربوط به مدیریت کانال
"""

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from app.database.models import Channel, Platform


def get_channel_management_keyboard() -> InlineKeyboardMarkup:
    """منوی مدیریت کانال"""
    keyboard = [
        [InlineKeyboardButton("➕ اتصال کانال جدید", callback_data="channel_add")],
        [InlineKeyboardButton("📋 لیست کانال‌های من", callback_data="channel_list")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_platform_selection_keyboard() -> InlineKeyboardMarkup:
    """انتخاب پلتفرم برای کانال جدید"""
    keyboard = [
        [InlineKeyboardButton("📱 تلگرام", callback_data="channel_platform_TELEGRAM")],
        [InlineKeyboardButton("📢 ایتا", callback_data="channel_platform_EITAA")],
        [InlineKeyboardButton("🔵 بله", callback_data="channel_platform_BALE")],
        [InlineKeyboardButton("❌ لغو", callback_data="channel_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_channel_list_keyboard(channels: list[Channel]) -> InlineKeyboardMarkup:
    """لیست کانال‌ها با دکمه حذف و جزئیات"""
    keyboard = []

    for channel in channels:
        # آیکون پلتفرم
        platform_icon = {
            Platform.TELEGRAM: "📱",
            Platform.EITAA: "📢",
            Platform.BALE: "🔵",
        }.get(channel.platform, "📌")

        # آیکون وضعیت
        if channel.activation_status == "PENDING_ACTIVATION":
            status_icon = "⏳"
        else:
            status_icon = "✅"

        display_name = f"{platform_icon} {status_icon} {channel.channel_identifier}"

        keyboard.append([
            InlineKeyboardButton(
                display_name[:60],
                callback_data=f"channel_detail_{channel.id}"
            )
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
    """لغو اضافه کردن کانال"""
    keyboard = [
        [InlineKeyboardButton("❓ راهنمای اتصال کانال", callback_data="tut_inline_connect_channel")],
        [InlineKeyboardButton("❌ لغو", callback_data="channel_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)



def get_channel_detail_keyboard(channel_id: int) -> InlineKeyboardMarkup:
    """کیبورد جزئیات کانال"""
    keyboard = [
        [InlineKeyboardButton("✏️ تنظیم آیدی تماس", callback_data=f"channel_set_contact_{channel_id}")],
        [InlineKeyboardButton("🗑 حذف آیدی تماس", callback_data=f"channel_delete_contact_{channel_id}")],
        [InlineKeyboardButton("📞 تنظیم شماره تلفن", callback_data=f"channel_set_phone_{channel_id}")],
        [InlineKeyboardButton("❌ حذف کانال", callback_data=f"channel_delete_{channel_id}")],
        [InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="channel_list")],
    ]
    return InlineKeyboardMarkup(keyboard)
