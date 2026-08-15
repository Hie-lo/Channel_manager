"""
نقطه شروع برنامه - اجرای همزمان ربات تلگرام و بله
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

    # تنظیم event loop برای ویندوز
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # اجرای async main
    asyncio.run(_run_bots())


async def _run_bots():
    """اجرای همزمان ربات‌های تلگرام و بله"""
    from app.bot.bot import create_bot
    from app.bot.bot_bale import create_bale_bot

    # ساخت ربات تلگرام
    telegram_bot = create_bot()

    # ساخت ربات بله (اختیاری)
    bale_bot = create_bale_bot()

    log.info(f"👑 ادمین: {settings.ADMIN_CHAT_ID}")
    log.info(f"🤖 ربات تلگرام: فعال")
    log.info(f"🤖 ربات بله: {'فعال' if bale_bot else 'غیرفعال'}")

    # راه‌اندازی
    await telegram_bot.initialize()
    await telegram_bot.start()

    if bale_bot:
        await bale_bot.initialize()
        await bale_bot.start()

    # شروع polling برای هر دو
    await telegram_bot.updater.start_polling(drop_pending_updates=True)
    log.info("🚀 ربات تلگرام شروع به کار کرد!")

    if bale_bot:
        await bale_bot.updater.start_polling(drop_pending_updates=True)
        log.info("🚀 ربات بله شروع به کار کرد!")

    # نگه داشتن برنامه
    try:
        # منتظر بمون تا Ctrl+C
        stop_event = asyncio.Event()
        await stop_event.wait()
    except (KeyboardInterrupt, SystemExit):
        log.info("🛑 در حال توقف ربات‌ها...")

    # توقف
    await telegram_bot.updater.stop()
    await telegram_bot.stop()
    await telegram_bot.shutdown()

    if bale_bot:
        await bale_bot.updater.stop()
        await bale_bot.stop()
        await bale_bot.shutdown()

    log.info("✅ ربات‌ها متوقف شدن")


if __name__ == "__main__":
    main()