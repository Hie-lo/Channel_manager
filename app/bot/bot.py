"""
راه‌اندازی و تنظیم ربات تلگرام
"""
#sd

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    TypeHandler
)
from app.bot.middlewares import global_anti_spam_middleware
from app.bot.handlers.mapping_wizard import (
    process_mapping_answer_callback,
    mapping_cancel_callback,
)
from app.bot.handlers.smart_mapping_wizard import (
    wizard_sheet_selected_callback,
    wizard_subtype_selected_callback,
    wizard_req_col_callback,
    wizard_opt_col_callback,
    wizard_confirm_callback,
    wizard_restart_callback,
    wizard_cancel_callback,
)
from app.bot.handlers.post_template_editor import (
    post_template_menu_handler,
    post_template_main_callback,
    tpl_preset_view_callback,
    tpl_preset_preview_callback,
    tpl_preset_select_callback,
)
from app.bot.handlers.post_preset_admin import (
    admin_presets_menu_handler,
    admin_presets_root_callback,
    admin_presets_biz_selected_callback,
    admin_preset_view_callback,
    admin_preset_toggle_callback,
    admin_preset_delete_callback,
    admin_preset_new_callback,
    admin_preset_name_received_handler,
    admin_preset_text_received_handler,
    admin_preset_edit_name_callback,
    admin_preset_rename_received_handler,
    admin_preset_edit_text_callback,
    admin_preset_edit_text_received_handler,
)
from app.bot.handlers.custom_post import (
    custom_post_start_handler,
    custom_post_text_received_handler,
    custom_post_photo_received_handler,
    custom_post_preview_callback,
    custom_post_send_confirm_callback,
    custom_post_cancel_callback,
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
    channel_platform_selected_callback,
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
    posting_toggle_ai_callback,
    settings_generate_link_code_callback,
    settings_change_business_callback,
    change_business_confirm_callback,
)
from app.bot.handlers.admin import (
    admin_test_publish_job_handler,
    admin_test_reminder_job_handler,
    admin_test_sheet_sync_handler,
    admin_test_daily_report_handler,
    admin_force_ai_test_handler
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
    sync_edit_posts_now_callback,     
    sync_edit_posts_later_callback,   
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
    ai_edit_callback,
    ai_edit_saved_callback,
    ai_edit_field_callback,
    ai_edit_text_handler,
    ai_view_result_callback,
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
    admin_customer_grant_sub_callback,
    admin_customer_grant_sub_plan_callback,
    admin_customer_grant_sub_confirm_callback,
    admin_customer_revoke_sub_callback,
    admin_customer_revoke_sub_confirm_callback,
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
from app.bot.handlers.product_image import (
    prod_upload_image_callback,
    prod_remove_image_callback,
    product_image_received_handler,
    prod_finish_upload_callback,
    prod_img_replace_callback,        
    prod_img_add_callback,            
    prod_repost_callback,             
)
from app.bot.handlers.support import (
    support_menu_handler,
    support_message_received_handler,
    support_cancel_callback,
    support_reply_callback,
    support_reply_cancel_callback,
    admin_reply_message_handler,
)
from app.bot.handlers.account_link import (
    link_account_start_callback,
    link_account_cancel_callback,
    link_code_received_handler,
)
from app.bot.handlers.admin_tutorial import admin_get_file_id_handler
from app.bot.states.user_state import get_user_state, UserState
from app.utils.admin_check import is_admin
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

    # چک state های کانال - همه حالت‌ها
    if state in (
        UserState.WAITING_CHANNEL_ID,
        UserState.WAITING_CHANNEL_ID_TELEGRAM,
        UserState.WAITING_CHANNEL_ID_EITAA,
        UserState.WAITING_CHANNEL_ID_BALE,
        UserState.WAITING_EITAA_TOKEN,       # ← جدید
        UserState.WAITING_EITAA_CHAT_ID,     # ← جدید
    ):
        await channel_id_received_handler(update, context)
        await channel_id_received_handler(update, context)
    elif state == UserState.WAITING_CHANNEL_ID_EITAA:
        await channel_id_received_handler(update, context)
    elif state == UserState.WAITING_CHANNEL_ID_BALE:
        await channel_id_received_handler(update, context)
    elif state == UserState.WAITING_CHANNEL_ID:
        await channel_id_received_handler(update, context)
    elif state == UserState.WAITING_PAYMENT_RECEIPT:
        await payment_receipt_handler(update, context)
    elif state == UserState.WAITING_SHEET_URL:
        await sheet_url_received_handler(update, context)
    elif state == UserState.WAITING_FOR_LINK_CODE:
        from app.bot.handlers.account_link import link_code_received_handler
        await link_code_received_handler(update, context)
    elif state == UserState.WAITING_CUSTOM_POST_TEXT:
        from app.bot.handlers.custom_post import custom_post_text_received_handler
        await custom_post_text_received_handler(update, context)
    elif state == UserState.ADMIN_SENDING_MESSAGE:
        await admin_message_text_handler(update, context)
    elif state == UserState.ADMIN_GIFTING_TOKENS:
        await admin_gift_tokens_handler(update, context)
    elif state == UserState.ADMIN_BROADCASTING:
        await admin_broadcast_text_handler(update, context)
    elif state == UserState.ADMIN_SEARCHING_CUSTOMER:
        await admin_search_customer_handler(update, context)
    elif state == UserState.WAITING_SUPPORT_MESSAGE:  
        await support_message_received_handler(update, context)
    elif state == UserState.ADMIN_REPLYING_TO_SUPPORT:  
        await admin_reply_message_handler(update, context)
    elif state == UserState.WAITING_FOR_LINK_CODE:
        await link_code_received_handler(update, context)
    elif state == UserState.WAITING_CUSTOM_POST_TEXT:
        await custom_post_text_received_handler(update, context)
    elif state == UserState.WAITING_CUSTOM_POST_PHOTOS:
        from app.bot.handlers.custom_post import custom_post_photo_received_handler
        await custom_post_photo_received_handler(update, context)
    elif state in (
        UserState.EDITING_AI_DESCRIPTION,
        UserState.EDITING_AI_PROS,
        UserState.EDITING_AI_CONS,
    ):
        await ai_edit_text_handler(update, context)
    elif state == UserState.PADM_WAITING_NAME:
        await admin_preset_name_received_handler(update, context)
    elif state == UserState.PADM_WAITING_TEXT:
        await admin_preset_text_received_handler(update, context)
    elif state == UserState.PADM_WAITING_RENAME:
        await admin_preset_rename_received_handler(update, context)
    elif state == UserState.PADM_WAITING_EDIT_TEXT:
        await admin_preset_edit_text_received_handler(update, context)

async def _smwiz_col_router(update, context):
    """مسیریاب کالبک انتخاب ستون در ویزارد هوشمند — بر اساس مرحله جاری"""
    from app.bot.states.user_state import get_user_data, UserState, get_user_state
    from app.bot.handlers.smart_mapping_wizard import (
        wizard_req_col_callback,
        wizard_opt_col_callback,
        STEP_REQUIRED_COL,
        STEP_OPTIONAL_COL,
    )
    user_id = update.callback_query.from_user.id
    if get_user_state(user_id) != UserState.SMART_MAPPING_WIZARD:
        return
    step = get_user_data(user_id).get("step")
    if step == STEP_OPTIONAL_COL:
        await wizard_opt_col_callback(update, context)
    else:
        await wizard_req_col_callback(update, context)


async def document_router(update, context):
    """مسیریاب فایل‌ها"""
    user = update.effective_user
    state = get_user_state(user.id)

    log.info(
        f"📎 [DOCUMENT ROUTER] user={user.id}, state={state}, "
        f"has_photo={bool(update.message.photo)}, "
        f"has_document={bool(update.message.document)}"
    )

    # اگه در حالت آپلود عکس محصول هستیم و فایل عکس/document اومده
    if state == UserState.WAITING_PRODUCT_IMAGE:
        log.info("→ product_image_received_handler (from document router)")
        await product_image_received_handler(update, context)
        return

    if state == UserState.WAITING_EXCEL_FILE:
        log.info("→ excel_file_received_handler")
        await excel_file_received_handler(update, context)
        return

    if state == UserState.WAITING_PAYMENT_RECEIPT:
        log.info("→ payment_receipt_handler")
        await payment_receipt_handler(update, context)
        return

    if state == UserState.WAITING_AI_TOKEN_RECEIPT:
        log.info("→ ai_token_receipt_handler")
        await ai_token_receipt_handler(update, context)
        return
    
    if state == UserState.WAITING_CUSTOM_POST_PHOTOS:
        log.info("→ custom_post_photo_received_handler (from document router)")
        await custom_post_photo_received_handler(update, context)
        return
    # ادمین → gen file_id
    from app.utils.admin_check import is_admin
    if is_admin(user.id):
        from app.bot.handlers.admin_tutorial import admin_get_file_id_handler
        await admin_get_file_id_handler(update, context)
        
async def photo_router(update, context):
    """مسیریاب عکس‌ها"""
    user = update.effective_user
    state = get_user_state(user.id)

    # DEBUG
    log.info(
        f"📷 [PHOTO ROUTER] user={user.id}, state={state}, "
        f"has_photo={bool(update.message.photo)}, "
        f"has_document={bool(update.message.document)}"
    )

    if state == UserState.WAITING_PAYMENT_RECEIPT:
        log.info("→ payment_receipt_handler")
        await payment_receipt_handler(update, context)
    elif state == UserState.WAITING_AI_TOKEN_RECEIPT:
        log.info("→ ai_token_receipt_handler")
        await ai_token_receipt_handler(update, context)
    elif state == UserState.WAITING_PRODUCT_IMAGE:
        log.info("→ product_image_received_handler")
        await product_image_received_handler(update, context)
    elif state == UserState.WAITING_CUSTOM_POST_PHOTOS:
        await custom_post_photo_received_handler(update, context)

    else:
        from app.utils.admin_check import is_admin
        if is_admin(user.id):
            log.info("→ admin_get_file_id_handler")
            from app.bot.handlers.admin_tutorial import admin_get_file_id_handler
            await admin_get_file_id_handler(update, context)

async def video_router(update, context):
    """مسیریاب ویدیوها"""
    user = update.effective_user
    state = get_user_state(user.id)

    # هدایت ویدیو به هندلر پست‌ساز سفارشی در صورت نیاز
    if state == UserState.WAITING_CUSTOM_POST_PHOTOS:
        from app.bot.handlers.custom_post import custom_post_photo_received_handler
        await custom_post_photo_received_handler(update, context)
        return

    # برای ادمین جهت گرفتن file_id راهنمای آموزشی
    from app.utils.admin_check import is_admin
    if is_admin(user.id):
        from app.bot.handlers.admin_tutorial import admin_get_file_id_handler
        await admin_get_file_id_handler(update, context)

async def document_image_router(update, context):
    """
    مسیریاب برای فایل‌های تصویری که به صورت document می‌آن
    (بعضی پلتفرم‌ها مثل بله ممکنه عکس رو Document بفرستن)
    """
    user = update.effective_user
    state = get_user_state(user.id)

    log.info(f"📎 [DOCUMENT IMAGE] user={user.id}, state={state}")

    if state == UserState.WAITING_PRODUCT_IMAGE:
        # فایل رو به عنوان عکس در نظر بگیر
        log.info("→ product_image_received_handler (from document)")
        await product_image_received_handler(update, context)
    else:
        log.info(f"⚠️ سند تصویری بدون state خاص")

def create_bot() -> Application:
    """ساخت و تنظیم ربات"""
    log.info("در حال ساخت ربات تلگرام...")

    app = (
        Application.builder()
        .token(settings.BOT_TOKEN)
        .post_init(on_startup)
        .build()
    )

    # ⚠️ مشخص کن این ربات تلگرامه
    app.bot_data["platform"] = "TELEGRAM"

    _register_all_handlers(app)
    log.info("✅ ربات تلگرام آماده است")
    return app
def _register_all_handlers(app: Application) -> None:
    # ═══════════════════════════════════════════════════════════
    # ۰. لایه امنیتی ضد اسپم (اجرا قبل از همه چیز با گروه منفی)
    # ═══════════════════════════════════════════════════════════
    app.add_handler(TypeHandler(Update, global_anti_spam_middleware), group=-1)
    
    # ═══════════════════════════════════════════════════════════
    # ۱. Commands (اولویت اول)
    # ═══════════════════════════════════════════════════════════
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("test_publish", admin_test_publish_job_handler))
    app.add_handler(CommandHandler("test_reminder", admin_test_reminder_job_handler))
    app.add_handler(CommandHandler("test_sheet_sync", admin_test_sheet_sync_handler))
    app.add_handler(CommandHandler("test_daily_report", admin_test_daily_report_handler))
    app.add_handler(CommandHandler("force_ai_test", admin_force_ai_test_handler))
    # ═══════════════════════════════════════════════════════════
    # ۲. Callback Queries (دکمه‌های Inline)
    # ⚠️ ترتیب مهمه: از خاص‌ترین به عام‌ترین
    # ═══════════════════════════════════════════════════════════

    # ─── کالبک‌های ثبت‌نام مشتری ───
    app.add_handler(CallbackQueryHandler(business_type_callback, pattern="^biz_"))
    app.add_handler(CallbackQueryHandler(approve_customer_callback, pattern="^approve_"))
    app.add_handler(CallbackQueryHandler(reject_customer_callback, pattern="^reject_"))

    # ─── کالبک‌های ادمین - مشتریان ───
    app.add_handler(CallbackQueryHandler(admin_customers_menu_callback, pattern="^admin_customers_menu$"))
    app.add_handler(CallbackQueryHandler(admin_customer_search_callback, pattern="^admin_customer_search$"))
    app.add_handler(CallbackQueryHandler(admin_customers_list_callback, pattern="^admin_customers_(list|active|pending|suspended)_"))
    app.add_handler(CallbackQueryHandler(admin_customer_view_callback, pattern="^admin_customer_view_"))
    app.add_handler(CallbackQueryHandler(admin_customer_suspend_callback, pattern="^admin_customer_suspend_"))
    app.add_handler(CallbackQueryHandler(admin_customer_activate_callback, pattern="^admin_customer_activate_"))
    app.add_handler(CallbackQueryHandler(admin_customer_message_callback, pattern="^admin_customer_message_"))
    app.add_handler(CallbackQueryHandler(admin_customer_gift_tokens_callback, pattern="^admin_customer_gift_tokens_"))
    
    # اعطا و حذف اشتراک برای مشتری (confirm ها اول)
    app.add_handler(CallbackQueryHandler(admin_customer_grant_sub_confirm_callback, pattern="^admin_customer_grant_sub_confirm_"))
    app.add_handler(CallbackQueryHandler(admin_customer_revoke_sub_confirm_callback, pattern="^admin_customer_revoke_sub_confirm_"))
    app.add_handler(CallbackQueryHandler(admin_customer_grant_sub_plan_callback, pattern="^admin_customer_grant_sub_plan_"))
    app.add_handler(CallbackQueryHandler(admin_customer_grant_sub_callback, pattern="^admin_customer_grant_sub_"))
    app.add_handler(CallbackQueryHandler(admin_customer_revoke_sub_callback, pattern="^admin_customer_revoke_sub_"))
    
    app.add_handler(CallbackQueryHandler(admin_broadcast_confirm_callback, pattern="^admin_broadcast_confirm$"))
    app.add_handler(CallbackQueryHandler(admin_broadcast_cancel_callback, pattern="^admin_broadcast_cancel$"))
    app.add_handler(CallbackQueryHandler(admin_cancel_callback, pattern="^admin_cancel$"))
    app.add_handler(CommandHandler("force_ai_test", admin_force_ai_test_handler))

    # ─── کالبک‌های ادمین - مدیریت اشتراک ───
    # ⚠️ ترتیب مهم! confirm ها قبل از parent
    app.add_handler(CallbackQueryHandler(admin_sub_cancel_confirm_callback, pattern="^admin_sub_cancel_confirm_"))
    app.add_handler(CallbackQueryHandler(admin_sub_delete_confirm_callback, pattern="^admin_sub_delete_confirm_"))
    app.add_handler(CallbackQueryHandler(admin_sub_extend_days_callback, pattern="^admin_sub_extend_days_"))

    app.add_handler(CallbackQueryHandler(admin_sub_cancel_callback, pattern="^admin_sub_cancel_"))
    app.add_handler(CallbackQueryHandler(admin_sub_delete_callback, pattern="^admin_sub_delete_"))
    app.add_handler(CallbackQueryHandler(admin_sub_extend_callback, pattern="^admin_sub_extend_"))
    app.add_handler(CallbackQueryHandler(admin_sub_view_callback, pattern="^admin_sub_view_"))

    app.add_handler(CallbackQueryHandler(admin_subs_menu_callback, pattern="^admin_subs_menu$"))
    app.add_handler(CallbackQueryHandler(admin_subs_revenue_callback, pattern="^admin_subs_revenue$"))
    app.add_handler(CallbackQueryHandler(admin_subs_view_plans_callback, pattern="^admin_subs_view_plans$"))
    app.add_handler(CallbackQueryHandler(admin_subs_list_callback, pattern="^admin_subs_(active|pending|expired|grace)_"))

    # ─── کالبک‌های مدیریت کانال ───
    # ⚠️ ترتیب مهم!
    app.add_handler(CallbackQueryHandler(channel_delete_confirm_callback, pattern="^channel_delete_confirm_"))
    app.add_handler(CallbackQueryHandler(channel_platform_selected_callback, pattern="^channel_platform_"))
    app.add_handler(CallbackQueryHandler(channel_delete_callback, pattern="^channel_delete_"))
    app.add_handler(CallbackQueryHandler(channel_menu_callback, pattern="^channel_menu$"))
    app.add_handler(CallbackQueryHandler(channel_add_callback, pattern="^channel_add$"))
    app.add_handler(CallbackQueryHandler(channel_list_callback, pattern="^channel_list$"))
    app.add_handler(CallbackQueryHandler(custom_post_preview_callback, pattern="^custom_post_preview$"))
    app.add_handler(CallbackQueryHandler(custom_post_send_confirm_callback, pattern="^custom_post_send_confirm$"))
    app.add_handler(CallbackQueryHandler(custom_post_cancel_callback, pattern="^custom_post_cancel$"))

    # ─── کالبک‌های ویزارد مپینگ (قدیمی — Google Sheet) ───
    app.add_handler(CallbackQueryHandler(process_mapping_answer_callback, pattern="^map_col_"))
    app.add_handler(CallbackQueryHandler(mapping_cancel_callback, pattern="^map_cancel$"))

    # ─── کالبک‌های ویزارد هوشمند مپینگ اکسل (smwiz_) ───
    app.add_handler(CallbackQueryHandler(wizard_sheet_selected_callback,   pattern="^smwiz_sheet_"))
    app.add_handler(CallbackQueryHandler(wizard_subtype_selected_callback, pattern="^smwiz_sub_"))
    # smwiz_col_ برای هر دو مرحله اجباری و اختیاری — dispatch بر اساس step
    app.add_handler(CallbackQueryHandler(_smwiz_col_router,                pattern="^smwiz_col_"))
    app.add_handler(CallbackQueryHandler(wizard_confirm_callback,          pattern="^smwiz_confirm$"))
    app.add_handler(CallbackQueryHandler(wizard_restart_callback,          pattern="^smwiz_restart$"))
    app.add_handler(CallbackQueryHandler(wizard_cancel_callback,           pattern="^smwiz_cancel$"))

    # ─── کالبک‌های انتخاب preset پست توسط مشتری (tpl_) ───
    app.add_handler(CallbackQueryHandler(post_template_main_callback,  pattern="^tpl_menu$"))
    app.add_handler(CallbackQueryHandler(tpl_preset_view_callback,     pattern="^tpl_preset_view_"))
    app.add_handler(CallbackQueryHandler(tpl_preset_preview_callback,  pattern="^tpl_preset_preview_"))
    app.add_handler(CallbackQueryHandler(tpl_preset_select_callback,   pattern="^tpl_preset_select_"))

    # ─── کالبک‌های پنل مدیریت preset پست توسط ادمین (padm_) ───
    app.add_handler(CallbackQueryHandler(admin_presets_root_callback,        pattern="^padm_root$"))
    app.add_handler(CallbackQueryHandler(admin_presets_biz_selected_callback, pattern="^padm_biz_"))
    app.add_handler(CallbackQueryHandler(admin_preset_new_callback,          pattern="^padm_new_"))
    app.add_handler(CallbackQueryHandler(admin_preset_toggle_callback,       pattern="^padm_toggle_"))
    app.add_handler(CallbackQueryHandler(admin_preset_delete_callback,       pattern="^padm_delete_"))
    app.add_handler(CallbackQueryHandler(admin_preset_edit_name_callback,    pattern="^padm_edit_name_"))
    app.add_handler(CallbackQueryHandler(admin_preset_edit_text_callback,    pattern="^padm_edit_text_"))
    app.add_handler(CallbackQueryHandler(admin_preset_view_callback,         pattern="^padm_view_"))
        
    # ─── کالبک‌های لینک اکانت ───
    app.add_handler(CallbackQueryHandler(link_account_start_callback, pattern="^link_account_start$"))
    app.add_handler(CallbackQueryHandler(link_account_cancel_callback, pattern="^link_account_cancel$"))

    # ─── کالبک‌های اشتراک (مشتری) ───
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
    # ─── کالبک‌های عکس محصول ───
    app.add_handler(CallbackQueryHandler(prod_upload_image_callback, pattern="^prod_upload_image_"))
    app.add_handler(CallbackQueryHandler(prod_remove_image_callback, pattern="^prod_remove_image_"))
    app.add_handler(CallbackQueryHandler(prod_finish_upload_callback, pattern="^prod_finish_upload_"))
    # جدید:
    app.add_handler(CallbackQueryHandler(prod_img_replace_callback, pattern="^prod_img_replace_"))
    app.add_handler(CallbackQueryHandler(prod_img_add_callback, pattern="^prod_img_add_"))
    app.add_handler(CallbackQueryHandler(prod_repost_callback, pattern="^prod_repost_"))
    # ─── کالبک‌های محصولات ───
    app.add_handler(CallbackQueryHandler(prod_preview_callback, pattern="^prod_preview_"))
    app.add_handler(CallbackQueryHandler(prod_publish_callback, pattern="^prod_publish_"))
    app.add_handler(CallbackQueryHandler(prod_view_callback, pattern="^prod_view_"))
    app.add_handler(CallbackQueryHandler(prod_list_callback, pattern="^prod_list_"))
    app.add_handler(CallbackQueryHandler(prod_finish_upload_callback, pattern="^prod_finish_upload_"))
    # ─── کالبک‌های تنظیمات ارسال ───
    # ⚠️ ترتیب مهم! interval_ و hours_ قبل از set_
    app.add_handler(CallbackQueryHandler(posting_interval_selected_callback, pattern="^posting_interval_"))
    app.add_handler(CallbackQueryHandler(posting_hours_selected_callback, pattern="^posting_hours_"))
    app.add_handler(CallbackQueryHandler(posting_toggle_auto_callback, pattern="^posting_toggle_auto$"))
    app.add_handler(CallbackQueryHandler(posting_toggle_ai_callback, pattern="^posting_toggle_ai$"))
    app.add_handler(CallbackQueryHandler(posting_set_interval_callback, pattern="^posting_set_interval$"))
    app.add_handler(CallbackQueryHandler(posting_set_hours_callback, pattern="^posting_set_hours$"))
    app.add_handler(CallbackQueryHandler(posting_back_callback, pattern="^posting_back$"))
    app.add_handler(CallbackQueryHandler(settings_generate_link_code_callback, pattern="^settings_generate_link_code$"))
    app.add_handler(CallbackQueryHandler(settings_change_business_callback, pattern="^settings_change_business$"))
    app.add_handler(CallbackQueryHandler(change_business_confirm_callback, pattern="^change_business_confirm$"))

    # ─── کالبک‌های Google Sheet ───
    app.add_handler(CallbackQueryHandler(sheet_delete_confirm_callback, pattern="^sheet_delete_confirm$"))
    app.add_handler(CallbackQueryHandler(sheet_delete_callback, pattern="^sheet_delete$"))
    app.add_handler(CallbackQueryHandler(sheet_add_callback, pattern="^sheet_add$"))
    app.add_handler(CallbackQueryHandler(sheet_change_callback, pattern="^sheet_change$"))
    app.add_handler(CallbackQueryHandler(sheet_sync_now_callback, pattern="^sheet_sync_now$"))
    app.add_handler(CallbackQueryHandler(sheet_cancel_callback, pattern="^sheet_cancel$"))
    app.add_handler(CallbackQueryHandler(sheet_get_template_callback, pattern="^sheet_get_template$"))
    app.add_handler(CallbackQueryHandler(sheet_back_to_menu_callback, pattern="^sheet_back_to_menu$"))
    # ─── کالبک‌های ادیت پست‌ها بعد از sync ───
    app.add_handler(CallbackQueryHandler(sync_edit_posts_now_callback, pattern="^sync_edit_posts_now$"))
    app.add_handler(CallbackQueryHandler(sync_edit_posts_later_callback, pattern="^sync_edit_posts_later$"))
    # ─── کالبک‌های AI Tokens ───
    app.add_handler(CallbackQueryHandler(ai_admin_approve_callback, pattern="^ai_admin_approve_"))
    app.add_handler(CallbackQueryHandler(ai_admin_reject_callback, pattern="^ai_admin_reject_"))
    app.add_handler(CallbackQueryHandler(ai_buy_tokens_callback, pattern="^ai_buy_tokens$"))
    app.add_handler(CallbackQueryHandler(ai_package_selected_callback, pattern="^ai_pkg_"))
    app.add_handler(CallbackQueryHandler(ai_cancel_purchase_callback, pattern="^ai_cancel_purchase$"))
    app.add_handler(CallbackQueryHandler(ai_menu_back_callback, pattern="^ai_menu_back$"))

    # ─── کالبک‌های AI Generation ───
    # ⚠️ ai_confirm_gen_ قبل از ai_start_ (چون هر دو با ai_ شروع میشن)
    app.add_handler(CallbackQueryHandler(ai_confirm_generation_callback, pattern="^ai_confirm_gen_"))
    app.add_handler(CallbackQueryHandler(ai_accept_result_callback, pattern="^ai_accept_"))
    app.add_handler(CallbackQueryHandler(ai_regenerate_callback, pattern="^ai_regen_"))
    app.add_handler(CallbackQueryHandler(ai_start_generation_callback, pattern="^ai_start_"))
    app.add_handler(CallbackQueryHandler(ai_edit_field_callback, pattern="^ai_edit_(desc|pros|cons)_"))
    app.add_handler(CallbackQueryHandler(ai_edit_field_callback, pattern="^ai_edit_saved_(desc|pros|cons)_"))
    app.add_handler(CallbackQueryHandler(ai_edit_saved_callback, pattern="^ai_edit_saved_[0-9]+$"))
    app.add_handler(CallbackQueryHandler(ai_edit_callback, pattern="^ai_edit_[0-9]+_[0-9]+$"))
    app.add_handler(CallbackQueryHandler(ai_view_result_callback, pattern="^ai_view_result_"))

    # ─── کالبک‌های آموزش ───
    # ⚠️ tut_inline_ باید قبل از tut_ عمومی باشه
    app.add_handler(CallbackQueryHandler(tut_inline_callback, pattern="^tut_inline_"))
    app.add_handler(CallbackQueryHandler(tut_view_callback, pattern="^tut_view_"))
    app.add_handler(CallbackQueryHandler(tut_category_callback, pattern="^tut_cat_"))
    app.add_handler(CallbackQueryHandler(tut_menu_callback, pattern="^tut_menu$"))
    # ─── کالبک‌های پشتیبانی ───
    app.add_handler(CallbackQueryHandler(support_cancel_callback, pattern="^support_cancel$"))
    app.add_handler(CallbackQueryHandler(support_reply_cancel_callback, pattern="^support_reply_cancel$"))
    app.add_handler(CallbackQueryHandler(support_reply_callback, pattern="^support_reply_"))
    # ═══════════════════════════════════════════════════════════
    # ۳. Message Handlers - دکمه‌های ReplyKeyboard (خاص)
    # ⚠️ باید قبل از text_router عمومی باشن
    # ═══════════════════════════════════════════════════════════

    # ─── منوی مشتری ───
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^📢 مدیریت کانال$"),
        channel_menu_handler
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^📝 پست‌ساز دستی$"),
        custom_post_start_handler
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^💳 اشتراک من$"),
        subscription_menu_handler
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
        filters.TEXT & filters.Regex("^🤖 توکن AI$"),
        ai_tokens_menu_handler
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^📚 آموزش و راهنما$"),
        tutorial_menu_handler
    )) 
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^💬 پشتیبانی$"),
        support_menu_handler
    ))

    # ─── منوی ادمین ───
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
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Regex("^🎨 قالب‌های پست$"),
        admin_presets_menu_handler
    ))

    # ═══════════════════════════════════════════════════════════
    # ۴. Router عمومی برای پیام‌های متنی (state-based)
    # ⚠️ باید بعد از MessageHandler های خاص باشه
    # ═══════════════════════════════════════════════════════════
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        text_router
    ))

    # ═══════════════════════════════════════════════════════════
    # ۵. Router برای فایل‌ها و عکس‌ها
    # ═══════════════════════════════════════════════════════════
    app.add_handler(MessageHandler(
        filters.Document.ALL,
        document_router
    ))
 # عکس‌ها (photo message)
    app.add_handler(MessageHandler(
        filters.PHOTO,
        photo_router
    ))

    # همچنین چک برای فایل‌های image (بعضی پلتفرم‌ها به صورت document می‌فرستن)
    app.add_handler(MessageHandler(
        filters.Document.IMAGE,
        document_image_router
    ))
    app.add_handler(MessageHandler(
        filters.VIDEO | filters.ANIMATION,
        video_router
    ))

    # ═══════════════════════════════════════════════════════════
    # ۶. Error Handler (آخرین)
    # ═══════════════════════════════════════════════════════════
    app.add_error_handler(error_handler)

    log.info("✅ ربات آماده است")
    return app