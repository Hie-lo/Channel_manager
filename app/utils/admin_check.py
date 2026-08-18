"""
تابع کمکی برای تشخیص ادمین در پلتفرم‌های مختلف
"""

from app.config import settings


def is_admin(user_id: int) -> bool:
    """
    چک می‌کنه که کاربر ادمین هست یا نه
    (چه در تلگرام، چه در بله، چه در پلتفرم‌های آینده)
    """
    if user_id == settings.ADMIN_CHAT_ID:
        return True

    if settings.BALE_ADMIN_CHAT_ID and user_id == settings.BALE_ADMIN_CHAT_ID:
        return True

    return False


def get_admin_id_for_platform(platform: str = "telegram") -> int:
    """
    گرفتن admin_id مناسب برای پلتفرم مورد نظر
    برای ارسال پیام به ادمین
    """
    if platform.lower() == "bale" and settings.BALE_ADMIN_CHAT_ID:
        return settings.BALE_ADMIN_CHAT_ID
    return settings.ADMIN_CHAT_ID


def detect_platform_from_context(context) -> str:
    """
    تشخیص پلتفرم از context ربات
    Returns: "TELEGRAM" یا "BALE"
    """
    # روش اول: از bot_data
    try:
        platform = context.bot_data.get("platform")
        if platform:
            return platform.upper()
    except Exception:
        pass

    # روش دوم: از base_url
    try:
        base_url = str(getattr(context.bot, "base_url", "") or "")
        if "bale" in base_url.lower():
            return "BALE"
        if "telegram" in base_url.lower():
            return "TELEGRAM"
    except Exception:
        pass

    # روش سوم (fallback): از token
    try:
        from app.config import settings
        bot_token = getattr(context.bot, "token", "")
        if bot_token and bot_token == settings.BALE_BOT_TOKEN:
            return "BALE"
    except Exception:
        pass

    return "TELEGRAM"