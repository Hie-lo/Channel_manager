"""
راه‌اندازی و تنظیم ربات تلگرام
"""

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from app.config import settings
from app.database.init_db import init_db
from app.bot.handlers.start import start_handler
from app.bot.handlers.error import error_handler
from app.bot.handlers.customer import (
    business_type_callback,
    approve_customer_callback,
    reject_customer_callback,
)
from app.bot.handlers.channel import (
    channel_menu_handler,
    channel_menu_callback,
    channel_add_callback,
    channel_list_callback,
    channel_delete_callback,
    channel_delete_confirm_callback,
    channel_id_received_handler,
)
from app.utils.logger import log


async def on_startup(application: Application) -> None:
    """کارهایی که قبل از شروع polling اجرا میشن"""
    log.info("🗄 در حال اتصال به دیتابیس...")
    await init_db()
    log.info("✅ دیتابیس آماده است")


def create_bot() -> Application:
    """ساخت و تنظیم ربات"""

    log.info("در حال ساخت ربات تلگرام...")

    app = (
        Application.builder()
        .token(settings.BOT_TOKEN)
        .post_init(on_startup)
        .build()
    )

    # ─── دستورات ───
    app.add_handler(CommandHandler("start", start_handler))

    # ─── دکمه‌های منوی اصلی (متنی) ───
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^📢 مدیریت کانال$"),
        channel_menu_handler
    ))

    # ─── کالبک‌های ثبت‌نام ───
    app.add_handler(CallbackQueryHandler(
        business_type_callback,
        pattern="^biz_"
    ))
    app.add_handler(CallbackQueryHandler(
        approve_customer_callback,
        pattern="^approve_"
    ))
    app.add_handler(CallbackQueryHandler(
        reject_customer_callback,
        pattern="^reject_"
    ))

    # ─── کالبک‌های مدیریت کانال ───
    # ⚠️ ترتیب مهمه! چون channel_delete_confirm_ شامل channel_delete_ هم میشه
    # پس اول confirm رو ثبت می‌کنیم
    app.add_handler(CallbackQueryHandler(
        channel_delete_confirm_callback,
        pattern="^channel_delete_confirm_"
    ))
    app.add_handler(CallbackQueryHandler(
        channel_delete_callback,
        pattern="^channel_delete_"
    ))
    app.add_handler(CallbackQueryHandler(
        channel_menu_callback,
        pattern="^channel_menu$"
    ))
    app.add_handler(CallbackQueryHandler(
        channel_add_callback,
        pattern="^channel_add$"
    ))
    app.add_handler(CallbackQueryHandler(
        channel_list_callback,
        pattern="^channel_list$"
    ))

    # ─── پیام‌های متنی (برای دریافت آیدی کانال) ───
    # این handler آخر باشه چون کلی گیرندست
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        channel_id_received_handler
    ))

    # ─── هندلر خطاها ───
    app.add_error_handler(error_handler)

    log.info("✅ ربات آماده است")
    return app