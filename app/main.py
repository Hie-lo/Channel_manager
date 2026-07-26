"""
نقطه شروع برنامه
"""

import asyncio

from app.utils.logger import log
from app.config import settings


def main():
    log.info("=" * 50)
    log.info("🤖 ربات مدیریت کانال در حال راه‌اندازی...")
    log.info("=" * 50)

    # چک تنظیمات ضروری
    if not settings.BOT_TOKEN:
        log.error("❌ BOT_TOKEN تنظیم نشده!")
        return

    if not settings.ADMIN_CHAT_ID:
        log.error("❌ ADMIN_CHAT_ID تنظیم نشده!")
        return

    if not settings.DATABASE_URL:
        log.error("❌ DATABASE_URL تنظیم نشده!")
        return

    # راه‌اندازی ربات
    from app.bot.bot import create_bot
    bot_app = create_bot()

    log.info("🚀 ربات شروع به کار کرد!")
    log.info(f"👑 ادمین: {settings.ADMIN_CHAT_ID}")

    # ساخت loop جدید برای سازگاری با Python 3.12 روی ویندوز
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # اجرای ربات
    bot_app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()