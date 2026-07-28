"""
راه‌اندازی و تنظیم ربات تلگرام
"""

from turtle import update

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
from app.bot.handlers.subscription import (
    subscription_menu_handler,
    sub_menu_callback,
    sub_buy_callback,
    sub_plan_callback,
    sub_duration_callback,
    sub_cancel_payment_callback,
    sub_admin_approve_callback,
    sub_admin_reject_callback,
    sub_status_callback,
    payment_receipt_handler,
)
from app.bot.handlers.upload import (
    upload_menu_handler,
    upload_download_template_callback,
    upload_send_excel_callback,
    upload_cancel_callback,
    excel_file_received_handler,
)
from app.bot.handlers.product import (
    product_menu_handler,
    prod_list_callback,
    prod_view_callback,
    prod_preview_callback,
    prod_publish_callback,
)
from app.bot.handlers.posting_settings import (
    posting_settings_handler,
    posting_toggle_auto_callback,
    posting_set_interval_callback,
    posting_interval_selected_callback,
    posting_set_hours_callback,
    posting_hours_selected_callback,
    posting_back_callback,
    posting_toggle_ai_callback
)
from app.bot.handlers.admin import (
    admin_test_publish_job_handler,
    admin_test_reminder_job_handler,
    admin_test_sheet_sync_handler,
    admin_test_daily_report_handler,
)
from app.bot.handlers.sheet_connection import (
    sheet_menu_handler,
    sheet_add_callback,
    sheet_url_received_handler,
    sheet_cancel_callback,
    sheet_change_callback,
    sheet_delete_callback,
    sheet_delete_confirm_callback,
    sheet_sync_now_callback,
    sheet_get_template_callback,
    sheet_back_to_menu_callback,
)
from app.bot.handlers.ai_tokens import (
    ai_tokens_menu_handler,
    ai_buy_tokens_callback,
    ai_package_selected_callback,
    ai_cancel_purchase_callback,
    ai_menu_back_callback,
    ai_token_receipt_handler,
    ai_admin_approve_callback,
    ai_admin_reject_callback,
)
from app.bot.handlers.product_ai import (
    ai_start_generation_callback,
    ai_confirm_generation_callback,
    ai_regenerate_callback,
    ai_accept_result_callback,
)
from app.bot.handlers.admin_panel import (
    admin_customers_menu_handler,
    admin_customers_menu_callback,
    admin_customers_list_callback,
    admin_customer_view_callback,
    admin_customer_suspend_callback,
    admin_customer_activate_callback,
    admin_customer_message_callback,
    admin_message_text_handler,
    admin_customer_gift_tokens_callback,
    admin_gift_tokens_handler,
    admin_stats_handler,
    admin_ai_stats_handler,
    admin_broadcast_handler,
    admin_broadcast_text_handler,
    admin_broadcast_confirm_callback,
    admin_broadcast_cancel_callback,
    admin_cancel_callback,
    admin_customer_search_callback,
    admin_search_customer_handler,
)
from app.bot.handlers.admin_subscriptions import (
    admin_subs_menu_handler,
    admin_subs_menu_callback,
    admin_subs_list_callback,
    admin_sub_view_callback,
    admin_sub_extend_callback,
    admin_sub_extend_days_callback,
    admin_sub_cancel_callback,
    admin_sub_cancel_confirm_callback,
    admin_sub_delete_callback,
    admin_sub_delete_confirm_callback,
    admin_subs_revenue_callback,
    admin_subs_view_plans_callback,
)
from app.bot.handlers.tutorial import (
    tutorial_menu_handler,
    tut_menu_callback,
    tut_category_callback,
    tut_view_callback,
    tut_inline_callback,
)

from app.bot.handlers.admin_tutorial import admin_get_file_id_handler
from app.bot.states.user_state import get_user_state, UserState
from app.utils.logger import log


async def on_startup(application: Application) -> None:
    log.info("🗄 در حال اتصال به دیتابیس...")
    await init_db()
    log.info("✅ دیتابیس آماده است")

    # ایجاد آموزش‌های پیش‌فرض
    from app.database.connection import AsyncSessionLocal
    from app.services.tutorial_seeder import seed_default_tutorials

    async with AsyncSessionLocal() as session:
        await seed_default_tutorials(session)

    # راه‌اندازی scheduler
    from app.tasks.scheduler import start_scheduler
    start_scheduler(application.bot)


async def text_router(update, context):
    """مسیریاب پیام‌های متنی بر اساس state"""
    user = update.effective_user
    state = get_user_state(user.id)

    if state == UserState.WAITING_CHANNEL_ID:
        await channel_id_received_handler(update, context)
    elif state == UserState.WAITING_PAYMENT_RECEIPT:
        await payment_receipt_handler(update, context)
    elif state == UserState.WAITING_SHEET_URL:
        await sheet_url_received_handler(update, context)
    elif state == UserState.ADMIN_SENDING_MESSAGE:
        await admin_message_text_handler(update, context)
    elif state == UserState.ADMIN_GIFTING_TOKENS:
        await admin_gift_tokens_handler(update, context)
    elif state == UserState.ADMIN_BROADCASTING:
        await admin_broadcast_text_handler(update, context)
    elif state == UserState.ADMIN_SEARCHING_CUSTOMER:
        await admin_search_customer_handler(update, context)


async def document_router(update, context):
    """مسیریاب فایل‌ها"""
    user = update.effective_user
    state = get_user_state(user.id)

    if state == UserState.WAITING_EXCEL_FILE:
        await excel_file_received_handler(update, context)
    elif state == UserState.WAITING_PAYMENT_RECEIPT:
        await payment_receipt_handler(update, context)
    elif state == UserState.WAITING_AI_TOKEN_RECEIPT:
        await ai_token_receipt_handler(update, context)
    elif user.id == settings.ADMIN_CHAT_ID:
            # اگه ادمین در حالتی نبود و فایلی فرستاد، file_id رو بده
        await admin_get_file_id_handler(update, context)

async def photo_router(update, context):
    """مسیریاب عکس‌ها"""
    user = update.effective_user
    state = get_user_state(user.id)

    if state == UserState.WAITING_PAYMENT_RECEIPT:
        await payment_receipt_handler(update, context)
    elif state == UserState.WAITING_AI_TOKEN_RECEIPT:
        await ai_token_receipt_handler(update, context)

async def video_router(update, context):
    """مسیریاب ویدیوها - فقط برای گرفتن file_id توسط ادمین"""
    user = update.effective_user
    if user.id == settings.ADMIN_CHAT_ID:
        await admin_get_file_id_handler(update, context)

def create_bot() -> Application:
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
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^💳 اشتراک من$"),
        subscription_menu_handler
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^🤖 توکن AI$"),
        ai_tokens_menu_handler
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^📤 آپلود محصولات$"),
        upload_menu_handler
    ))
    app.add_handler(MessageHandler(
    filters.TEXT & filters.Regex("^📦 مدیریت محصولات$"),
    product_menu_handler
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^⚙️ تنظیمات$"),
        posting_settings_handler
    ))
    app.add_handler(MessageHandler(
    filters.TEXT & filters.Regex("^📊 اتصال Google Sheet$"),
    sheet_menu_handler
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^📚 آموزش و راهنما$"),
        tutorial_menu_handler
    ))

    # ─── دکمه‌های ادمین ───
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^👥 مدیریت مشتریان$"),
        admin_customers_menu_handler
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^💳 مدیریت اشتراک‌ها$"),
        admin_subs_menu_handler
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^📊 آمار کلی$"),
        admin_stats_handler
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^🤖 آمار AI$"),
        admin_ai_stats_handler
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^🔔 ارسال اعلان$"),
        admin_broadcast_handler
    ))

    # ─── کالبک‌های ادمین ───
    app.add_handler(CallbackQueryHandler(admin_customers_menu_callback, pattern="^admin_customers_menu$"))
    app.add_handler(CallbackQueryHandler(admin_customer_search_callback, pattern="^admin_customer_search$"))
    app.add_handler(CallbackQueryHandler(admin_customers_list_callback, pattern="^admin_customers_(list|active|pending|suspended)_"))
    app.add_handler(CallbackQueryHandler(admin_customer_view_callback, pattern="^admin_customer_view_"))
    app.add_handler(CallbackQueryHandler(admin_customer_suspend_callback, pattern="^admin_customer_suspend_"))
    app.add_handler(CallbackQueryHandler(admin_customer_activate_callback, pattern="^admin_customer_activate_"))
    app.add_handler(CallbackQueryHandler(admin_customer_message_callback, pattern="^admin_customer_message_"))
    app.add_handler(CallbackQueryHandler(admin_customer_gift_tokens_callback, pattern="^admin_customer_gift_tokens_"))
    app.add_handler(CallbackQueryHandler(admin_broadcast_confirm_callback, pattern="^admin_broadcast_confirm$"))
    app.add_handler(CallbackQueryHandler(admin_broadcast_cancel_callback, pattern="^admin_broadcast_cancel$"))
    app.add_handler(CallbackQueryHandler(admin_cancel_callback, pattern="^admin_cancel$"))

    # ─── کالبک‌های مدیریت اشتراک ادمین ───
    app.add_handler(CallbackQueryHandler(admin_subs_menu_callback, pattern="^admin_subs_menu$"))
    app.add_handler(CallbackQueryHandler(admin_subs_revenue_callback, pattern="^admin_subs_revenue$"))
    app.add_handler(CallbackQueryHandler(admin_subs_view_plans_callback, pattern="^admin_subs_view_plans$"))

    # ترتیب مهمه: cancel_confirm قبل از cancel
    app.add_handler(CallbackQueryHandler(admin_sub_cancel_confirm_callback, pattern="^admin_sub_cancel_confirm_"))
    app.add_handler(CallbackQueryHandler(admin_sub_cancel_callback, pattern="^admin_sub_cancel_"))

    app.add_handler(CallbackQueryHandler(admin_sub_delete_confirm_callback, pattern="^admin_sub_delete_confirm_"))
    app.add_handler(CallbackQueryHandler(admin_sub_delete_callback, pattern="^admin_sub_delete_"))

    app.add_handler(CallbackQueryHandler(admin_sub_extend_days_callback, pattern="^admin_sub_extend_days_"))
    app.add_handler(CallbackQueryHandler(admin_sub_extend_callback, pattern="^admin_sub_extend_"))
    app.add_handler(CommandHandler("test_daily_report", admin_test_daily_report_handler))
    app.add_handler(CallbackQueryHandler(admin_sub_view_callback, pattern="^admin_sub_view_"))
    app.add_handler(CallbackQueryHandler(admin_subs_list_callback, pattern="^admin_subs_(active|pending|expired|grace)_"))

    app.add_handler(CommandHandler("test_sheet_sync", admin_test_sheet_sync_handler))
    app.add_handler(CommandHandler("test_publish", admin_test_publish_job_handler))
    app.add_handler(CommandHandler("test_reminder", admin_test_reminder_job_handler))
    # ─── کالبک‌های ثبت‌نام ───
    app.add_handler(CallbackQueryHandler(business_type_callback, pattern="^biz_"))
    app.add_handler(CallbackQueryHandler(approve_customer_callback, pattern="^approve_"))
    app.add_handler(CallbackQueryHandler(reject_customer_callback, pattern="^reject_"))

    # ─── کالبک‌های مدیریت کانال ───
    app.add_handler(CallbackQueryHandler(channel_delete_confirm_callback, pattern="^channel_delete_confirm_"))
    app.add_handler(CallbackQueryHandler(channel_delete_callback, pattern="^channel_delete_"))
    app.add_handler(CallbackQueryHandler(channel_menu_callback, pattern="^channel_menu$"))
    app.add_handler(CallbackQueryHandler(channel_add_callback, pattern="^channel_add$"))
    app.add_handler(CallbackQueryHandler(channel_list_callback, pattern="^channel_list$"))

    # ─── کالبک‌های اشتراک ───
    app.add_handler(CallbackQueryHandler(sub_admin_approve_callback, pattern="^sub_admin_approve_"))
    app.add_handler(CallbackQueryHandler(sub_admin_reject_callback, pattern="^sub_admin_reject_"))
    app.add_handler(CallbackQueryHandler(sub_cancel_payment_callback, pattern="^sub_cancel_payment$"))
    app.add_handler(CallbackQueryHandler(sub_duration_callback, pattern="^sub_dur_"))
    app.add_handler(CallbackQueryHandler(sub_plan_callback, pattern="^sub_plan_"))
    app.add_handler(CallbackQueryHandler(sub_status_callback, pattern="^sub_status$"))
    app.add_handler(CallbackQueryHandler(sub_buy_callback, pattern="^sub_buy$"))
    app.add_handler(CallbackQueryHandler(sub_menu_callback, pattern="^sub_menu$"))

    # ─── کالبک‌های آپلود ───
    app.add_handler(CallbackQueryHandler(upload_download_template_callback, pattern="^upload_download_template$"))
    app.add_handler(CallbackQueryHandler(upload_send_excel_callback, pattern="^upload_send_excel$"))
    app.add_handler(CallbackQueryHandler(upload_cancel_callback, pattern="^upload_cancel$"))

    # ─── کالبک‌های محصولات ───
    app.add_handler(CallbackQueryHandler(prod_preview_callback, pattern="^prod_preview_"))
    app.add_handler(CallbackQueryHandler(prod_publish_callback, pattern="^prod_publish_"))
    app.add_handler(CallbackQueryHandler(prod_view_callback, pattern="^prod_view_"))
    app.add_handler(CallbackQueryHandler(prod_list_callback, pattern="^prod_list_"))
    # ─── کالبک‌های تنظیمات ارسال ───
    # ⚠️ ترتیب مهم! interval_ و hours_ باید قبل از set_interval و set_hours ثبت شوند
    app.add_handler(CallbackQueryHandler(posting_interval_selected_callback, pattern="^posting_interval_"))
    app.add_handler(CallbackQueryHandler(posting_hours_selected_callback, pattern="^posting_hours_"))
    app.add_handler(CallbackQueryHandler(posting_toggle_auto_callback, pattern="^posting_toggle_auto$"))
    app.add_handler(CallbackQueryHandler(posting_set_interval_callback, pattern="^posting_set_interval$"))
    app.add_handler(CallbackQueryHandler(posting_set_hours_callback, pattern="^posting_set_hours$"))
    app.add_handler(CallbackQueryHandler(posting_back_callback, pattern="^posting_back$"))
    app.add_handler(CallbackQueryHandler(posting_toggle_ai_callback, pattern="^posting_toggle_ai$"))

    # ─── کالبک‌های Google Sheet ───
    app.add_handler(CallbackQueryHandler(sheet_delete_confirm_callback, pattern="^sheet_delete_confirm$"))
    app.add_handler(CallbackQueryHandler(sheet_delete_callback, pattern="^sheet_delete$"))
    app.add_handler(CallbackQueryHandler(sheet_add_callback, pattern="^sheet_add$"))
    app.add_handler(CallbackQueryHandler(sheet_change_callback, pattern="^sheet_change$"))
    app.add_handler(CallbackQueryHandler(sheet_sync_now_callback, pattern="^sheet_sync_now$"))
    app.add_handler(CallbackQueryHandler(sheet_cancel_callback, pattern="^sheet_cancel$"))
    app.add_handler(CallbackQueryHandler(sheet_get_template_callback, pattern="^sheet_get_template$"))
    app.add_handler(CallbackQueryHandler(sheet_back_to_menu_callback, pattern="^sheet_back_to_menu$"))

    # ─── کالبک‌های AI Tokens ───
    app.add_handler(CallbackQueryHandler(ai_admin_approve_callback, pattern="^ai_admin_approve_"))
    app.add_handler(CallbackQueryHandler(ai_admin_reject_callback, pattern="^ai_admin_reject_"))
    app.add_handler(CallbackQueryHandler(ai_buy_tokens_callback, pattern="^ai_buy_tokens$"))
    app.add_handler(CallbackQueryHandler(ai_package_selected_callback, pattern="^ai_pkg_"))
    app.add_handler(CallbackQueryHandler(ai_cancel_purchase_callback, pattern="^ai_cancel_purchase$"))
    app.add_handler(CallbackQueryHandler(ai_menu_back_callback, pattern="^ai_menu_back$"))

    # ─── کالبک‌های AI Generation ───
    app.add_handler(CallbackQueryHandler(ai_confirm_generation_callback, pattern="^ai_confirm_gen_"))
    app.add_handler(CallbackQueryHandler(ai_accept_result_callback, pattern="^ai_accept_"))
    app.add_handler(CallbackQueryHandler(ai_regenerate_callback, pattern="^ai_regen_"))
    app.add_handler(CallbackQueryHandler(ai_start_generation_callback, pattern="^ai_start_"))

    # ─── کالبک‌های آموزش ───
    app.add_handler(CallbackQueryHandler(tut_inline_callback, pattern="^tut_inline_"))
    app.add_handler(CallbackQueryHandler(tut_view_callback, pattern="^tut_view_"))
    app.add_handler(CallbackQueryHandler(tut_category_callback, pattern="^tut_cat_"))
    app.add_handler(CallbackQueryHandler(tut_menu_callback, pattern="^tut_menu$"))

    # ─── پیام‌های متنی (router) ───
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        text_router
    ))

    # ─── فایل‌ها (router) ───
    app.add_handler(MessageHandler(
        filters.Document.ALL,
        document_router
    ))

    # ─── عکس‌ها (router) ───
    app.add_handler(MessageHandler(
        filters.PHOTO,
        photo_router
    ))
    # ─── ویدیوها (برای ادمین فقط - گرفتن file_id) ───
    app.add_handler(MessageHandler(
        filters.VIDEO | filters.ANIMATION,
        video_router
    ))
    # ─── هندلر خطاها ───
    app.add_error_handler(error_handler)

    log.info("✅ ربات آماده است")
    return app