"""
راه‌اندازی ربات بله
از همون handlers تلگرام استفاده می‌کنه (چون بله سازگاره)
ولی با base_url متفاوت
"""

from telegram.ext import Application

from app.config import settings
from app.utils.logger import log


def create_bale_bot() -> Application | None:
    if not settings.BALE_ENABLED:
        log.info("⚠️ بله غیرفعال است (BALE_ENABLED=False)")
        return None

    if not settings.BALE_BOT_TOKEN:
        log.warning("⚠️ BALE_BOT_TOKEN تنظیم نشده است")
        return None

    log.info("🤖 در حال ساخت ربات بله...")

    try:
        app = (
            Application.builder()
            .token(settings.BALE_BOT_TOKEN)
            .base_url(settings.BALE_API_BASE)
            .base_file_url(settings.BALE_FILE_API_BASE)
            .build()
        )

        # ⚠️ مشخص کن این ربات بله‌ست
        app.bot_data["platform"] = "BALE"

        # ثبت handlers مشترک با تلگرام
        _register_handlers(app)

        log.info("✅ ربات بله آماده است")
        return app

    except Exception as e:
        log.error(f"❌ خطا در ساخت ربات بله: {e}", exc_info=True)
        return None


def _register_handlers(app: Application) -> None:
    """
    ثبت handlers برای ربات بله
    این تابع همون handlers ربات تلگرام رو ثبت می‌کنه
    """
    # این تابع رو از bot.py قرض می‌گیریم
    from app.bot.bot import _register_all_handlers
    _register_all_handlers(app)