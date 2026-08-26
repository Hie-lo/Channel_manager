"""
هندلرهای اتصال Google Sheet
"""

from pathlib import Path
import json

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from app.config import settings
from app.database.connection import AsyncSessionLocal
from app.database.models import CustomerStatus
from app.services.customer_service import get_customer_by_telegram_id
from app.services.subscription.service import get_active_subscription
from app.services.sheet_connection_service import (
    get_sheet_connection,
    create_or_update_sheet_connection,
    delete_sheet_connection,
)
from app.services.data_input.sheet_reader import (
    test_sheet_connection,
    extract_sheet_id_from_url,
)
from app.bot.states.user_state import (
    UserState,
    get_user_data,
    set_user_state,
    get_user_state,
    clear_user_state,
)
from app.utils.logger import log
from app.utils.security import is_rate_limited


def _get_bot_service_account_email() -> str:
    """خواندن ایمیل service account از فایل credentials"""
    try:
        creds_path = Path(settings.GOOGLE_CREDENTIALS_FILE)
        if not creds_path.exists():
            return "❌ فایل credentials پیدا نشد"

        with open(creds_path, "r") as f:
            data = json.load(f)

        return data.get("client_email", "❌ ایمیل پیدا نشد")
    except Exception as e:
        log.error(f"خطا در خواندن ایمیل service account: {e}")
        return "❌ خطا در خواندن ایمیل"


def _get_sheet_menu_keyboard(has_connection: bool, has_template: bool = False) -> InlineKeyboardMarkup:
    """کیبورد منوی اتصال Sheet"""
    keyboard = []

    if has_connection:
        keyboard.append([
            InlineKeyboardButton("🔄 تغییر شیت", callback_data="sheet_change")
        ])
        keyboard.append([
            InlineKeyboardButton("🔃 همگام‌سازی الان", callback_data="sheet_sync_now")
        ])
        keyboard.append([
            InlineKeyboardButton("❌ حذف اتصال", callback_data="sheet_delete")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("➕ اتصال Google Sheet", callback_data="sheet_add")
        ])
        if has_template:
            keyboard.append([
                InlineKeyboardButton("📥 دریافت لینک شیت نمونه", callback_data="sheet_get_template")
            ])

    return InlineKeyboardMarkup(keyboard)


def _get_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❓ راهنمای اتصال Google Sheet", callback_data="tut_inline_connect_sheet")],
        [InlineKeyboardButton("❌ لغو", callback_data="sheet_cancel")],
    ])


def _get_delete_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ بله، حذف کن", callback_data="sheet_delete_confirm"),
            InlineKeyboardButton("❌ انصراف", callback_data="sheet_cancel"),
        ]
    ])


async def sheet_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش منوی مدیریت Google Sheet"""
    user = update.effective_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)

        if not customer or customer.customer_status != CustomerStatus.ACTIVE:
            await update.message.reply_text("❌ حساب شما فعال نیست.")
            return

        subscription = await get_active_subscription(session, customer.id)
        if not subscription:
            await update.message.reply_text(
                "❌ اشتراک فعالی ندارید!\n\n"
                "برای استفاده از این بخش، از منوی '💳 اشتراک من' اشتراک تهیه کنید."
            )
            return

        connection = await get_sheet_connection(session, customer.id)

        from app.business.config import get_google_sheet_template_url
        template_url = get_google_sheet_template_url(customer.business_type_key)

    has_template = bool(template_url)

    if connection:
        sync_status = connection.last_sync_status or "هنوز sync نشده"
        last_sync = (
            connection.last_sync_at.strftime("%Y/%m/%d %H:%M")
            if connection.last_sync_at
            else "هرگز"
        )

        menu_text = (
            f"📊 Google Sheet\n"
            f"━━━━━━━━━━━━━━━\n"
            f"✅ اتصال فعال\n"
            f"📄 شیت: {connection.worksheet_name}\n"
            f"🕐 آخرین همگام‌سازی: {last_sync}\n"
            f"📊 وضعیت: {sync_status}\n"
        )

        if connection.last_error:
            menu_text += f"\n⚠️ آخرین خطا:\n{connection.last_error[:200]}\n"

        menu_text += (
            f"━━━━━━━━━━━━━━━\n\n"
            f"💡 قیمت و موجودی محصولات به صورت خودکار\n"
            f"از این شیت خوانده و آپدیت می‌شوند."
        )
    else:
        menu_text = (
            f"📊 Google Sheet\n"
            f"━━━━━━━━━━━━━━━\n"
            f"❌ هنوز شیتی متصل نکرده‌اید\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"💡 با اتصال Google Sheet:\n"
            f"├── قیمت‌ها خودکار آپدیت میشن\n"
            f"├── موجودی خودکار به‌روز میشه\n"
            f"└── نیازی به آپلود مکرر اکسل نیست\n\n"
        )
        if has_template:
            menu_text += (
                f"🎯 برای شروع سریع، از دکمه\n"
                f"'📥 دریافت لینک شیت نمونه' استفاده کنید.\n"
            )

    await update.message.reply_text(
        menu_text,
        reply_markup=_get_sheet_menu_keyboard(
            has_connection=connection is not None,
            has_template=has_template,
        ),
    )


async def sheet_add_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """شروع فرآیند اتصال شیت جدید"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    bot_email = _get_bot_service_account_email()

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            await query.edit_message_text("❌ خطا!")
            return

        from app.business.config import get_business, get_google_sheet_template_url
        business_config = get_business(customer.business_type_key)

    template_url = get_google_sheet_template_url(customer.business_type_key) if business_config else None

    text = (
        f"📊 <b>اتصال Google Sheet</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
    )

    if template_url:
        text += (
            f"🎯 <b>روش پیشنهادی (سریع‌ترین):</b>\n\n"
            f"1️⃣ روی لینک زیر کلیک کنید:\n"
            f"<a href=\"{template_url}\">📥 دریافت شیت نمونه</a>\n\n"
            f"2️⃣ در صفحه‌ای که باز می‌شود، دکمه <b>Make a copy</b> را بزنید\n\n"
            f"3️⃣ یه کپی از شیت در حساب گوگل شما ساخته می‌شود\n"
            f"(با ساختار آماده و صفحه‌های صحیح)\n\n"
            f"4️⃣ محصولات خودتون رو در هر صفحه وارد کنید\n\n"
            f"5️⃣ دکمه <b>Share</b> بالای شیت را بزنید و این ایمیل را اضافه کنید:\n"
            f"<code>{bot_email}</code>\n"
            f"(سطح دسترسی: <b>Editor</b>)\n\n"
            f"6️⃣ لینک شیت خودتون رو کپی و اینجا ارسال کنید\n\n"
            f"━━━━━━━━━━━━━━━\n\n"
        )
    else:
        text += (
            f"⚠️ برای این کسب‌وکار نمونه Google Sheet ندارد.\n"
            f"لطفاً از فایل اکسل نمونه استفاده کنید.\n\n"
            f"━━━━━━━━━━━━━━━\n\n"
        )

    text += (
        f"📝 <b>روش دستی (اگه از قبل شیت دارید):</b>\n\n"
        f"1️⃣ ساختار شیت شما باید مطابق فایل نمونه باشد\n"
        f"(نام صفحه‌ها و ستون‌ها مهم است)\n\n"
        f"2️⃣ در Share شیت، این ایمیل را با دسترسی Editor اضافه کنید:\n"
        f"<code>{bot_email}</code>\n\n"
        f"3️⃣ لینک شیت را ارسال کنید\n\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"💡 حالا لینک شیت خودتون رو ارسال کنید:"
    )

    set_user_state(user.id, UserState.WAITING_SHEET_URL)

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=_get_cancel_keyboard(),
        disable_web_page_preview=True,
    )


async def sheet_url_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دریافت لینک شیت از مشتری + همگام‌سازی خودکار اولیه + ویزارد مپینگ در صورت نیاز"""
    user = update.effective_user

    if get_user_state(user.id) != UserState.WAITING_SHEET_URL:
        return

    url = update.message.text.strip()

    # کیبورد راهنمای گوگل شیت برای پیام‌های خطا
    from app.bot.keyboards.tutorial import get_inline_help_keyboard
    help_cancel_kb = get_inline_help_keyboard(
        tutorial_key="connect_sheet", 
        existing_buttons=[[InlineKeyboardButton("❌ لغو", callback_data="sheet_cancel")]]
    )

    # ۱. استخراج و اعتبارسنجی اولیه ID شیت
    sheet_id = extract_sheet_id_from_url(url)
    if not sheet_id:
        await update.message.reply_text(
            "❌ <b>لینک Google Sheet نامعتبر است!</b>\n\n"
            "لینک باید مشابه نمونه زیر باشد:\n"
            "<code>https://docs.google.com/spreadsheets/d/1abc.../edit</code>\n\n"
            "لطفاً لینک صحیح را ارسال کنید:",
            parse_mode="HTML",
            reply_markup=help_cancel_kb
        )
        return

    processing_msg = await update.message.reply_text(
        "🔍 در حال بررسی اتصال به شیت...\nلطفاً چند لحظه صبر کنید."
    )

    # ۲. تست اتصال با gspread
    result = test_sheet_connection(url)

    if not result.success:
        bot_email = _get_bot_service_account_email()
        await processing_msg.edit_text(
            f"❌ <b>اتصال ناموفق!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📝 دلیل: {result.error_message}\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"⚠️ <b>راهنمای سریع رفع مشکل:</b>\n"
            f"1️⃣ این ایمیل ربات را به دکمه Share شیت اضافه کنید:\n"
            f"<code>{bot_email}</code>\n"
            f"2️⃣ دسترسی را حتماً روی <b>Editor</b> قرار دهید.\n\n"
            f"لطفاً پس از تنظیم دسترسی، مجدداً لینک را بفرستید:",
            parse_mode="HTML",
            reply_markup=help_cancel_kb,
        )
        return

    # ۳. اتصال موفق اولیه - ذخیره در دیتابیس
    customer_id_for_sync = None
    recognized_sheets = []
    unrecognized_sheets = []

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            await processing_msg.edit_text("❌ خطا! حساب شما یافت نشد.")
            clear_user_state(user.id)
            return

        from app.business.config import get_business
        business_config = get_business(customer.business_type_key)

        if business_config:
            if business_config.key == "other":
                for ws_title in result.worksheet_titles:
                    if ws_title not in ("راهنما", "info", "Sheet1", "Sheet2"):
                        recognized_sheets.append(ws_title)
            else:
                expected_sheets = {sc.worksheet_name for sc in business_config.sub_categories}
                for ws_title in result.worksheet_titles:
                    if ws_title in expected_sheets:
                        recognized_sheets.append(ws_title)
                    elif ws_title not in ("راهنما", "info", "Sheet1", "Sheet2"):
                        unrecognized_sheets.append(ws_title)

        await create_or_update_sheet_connection(
            session=session,
            customer_id=customer.id,
            sheet_url=url,
            sheet_id=result.sheet_id,
            worksheet_name="multi_sheet",
        )
        customer_id_for_sync = customer.id

    clear_user_state(user.id)

    # ۴. اگر هیچ برگه معتبری پیدا نشد
    if not recognized_sheets:
        await processing_msg.edit_text(
            f"⚠️ <b>هیچ صفحه معتبری در شیت شما پیدا نشد!</b>\n"
            f"لطفاً از شیت نمونه استفاده کنید یا نام صفحه‌ها را بررسی کنید.",
            parse_mode="HTML",
            reply_markup=help_cancel_kb
        )
        return

    await processing_msg.edit_text(
        f"✅ <b>اتصال برقرار شد!</b>\n"
        f"🔄 در حال اجرای همگام‌سازی اولیه محصولات...\nلطفاً صبور باشید."
    )

     # مرحله بعد: شروع همگام‌سازی اولیه
    connection_text += (
        f"\n━━━━━━━━━━━━━━━\n\n"
        f"🔄 در حال شروع همگام‌سازی اولیه...\n"
        f"لطفاً چند لحظه صبر کنید."
    )
    await processing_msg.edit_text(connection_text)

    # اجرای sync
    try:
        from app.tasks.jobs.sheet_sync_job import sync_customer_sheet
        
        sync_result = await sync_customer_sheet(
            context.bot,
            customer_id_for_sync,
            is_manual=True,
            edit_posts_now=False,
        )

        # 🚨 اگر خطای مپینگ ستون‌ها (Missing Fields) رخ داده باشد، ویزارد را استارت می‌زنیم
        if sync_result.get("requires_mapping_wizard"):
            from app.bot.handlers.mapping_wizard import start_mapping_wizard_for_sheet
            
            await start_mapping_wizard_for_sheet(
                update=update,
                user_id=user.id,
                customer_id=customer_id_for_sync,
                missing_fields=sync_result["missing_fields"],
                headers=sync_result["headers"],
                sheet_id=sync_result["sheet_id"],
            )
            return  # خروج از این هندلر، بقیه کار به عهده ویزارد است

        # ساخت گزارش نهایی
        if sync_result.get("error"):
            final_text = (
                f"✅ اتصال برقرار شد ولی در همگام‌سازی خطا رخ داد.\n\n"
                f"⚠️ {sync_result['error']}\n\n"
                f"می‌تونید از منوی '📊 Google Sheet' →\n"
                f"' همگام‌سازی الان' دوباره امتحان کنید."
            )
        else:
            new_count = sync_result.get("new_count", 0)
            updated_count = sync_result.get("updated_count", 0)
            unchanged = sync_result.get("unchanged_count", 0)
            errors = sync_result.get("error_count", 0)

            final_text = (
                f"✅ اتصال و همگام‌سازی کامل شد!\n"
                f"━━━━━━━━━━━━━━━\n"
                f" شیت: {result.sheet_title}\n"
                f"📄 صفحه‌های فعال: {len(recognized_sheets)}\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"📊 نتیجه همگام‌سازی:\n"
                f"├── 🆕 محصولات جدید: {new_count}\n"
                f"├── 🔄 آپدیت شده: {updated_count}\n"
                f"├── ✅ بدون تغییر: {unchanged}\n"
                f"└── ❌ خطا: {errors}\n\n"
            )

            if new_count > 0:
                final_text += (
                    f" {new_count} محصول جدید به سیستم اضافه شد!\n\n"
                    f"از این به بعد:\n"
                    f"├── هر  ساعت خودکار همگام‌سازی میشه\n"
                    f"├── تغییر قیمت/موجودی در شیت → آپدیت پست‌ها\n"
                    f"└── محصولات جدید → اضافه به سیستم\n\n"
                    f"💡 برای دیدن محصولات از ' مدیریت محصولات'"
                )
            else:
                final_text += (
                    f"از این به بعد:\n"
                    f"├── هر ۲ ساعت خودکار همگام‌سازی میشه\n"
                    f"└── تغییرات خودکار اعمال میشن\n\n"
                    f"💡 اگه محصولی در شیت اضافه کنید،\n"
                    f"در همگام‌سازی بعدی اضافه میشه."
                )

        await processing_msg.edit_text(final_text)

    except Exception as e:
        log.error(f"خطا در sync اولیه: {e}", exc_info=True)
        await processing_msg.edit_text(
            f"✅ اتصال برقرار شد ولی در همگام‌سازی خطا رخ داد.\n\n"
            f"لطفاً از منوی '📊 Google Sheet' →\n"
            f"'🔃 همگام‌سازی الان' اقدام کنید.\n\n"
            f"جزئیات خطا:\n{str(e)[:200]}"
        )

async def sheet_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """لغو فرآیند اتصال"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    clear_user_state(user.id)

    await query.edit_message_text(
        "❌ لغو شد.\n\n"
        "برای شروع مجدد از منوی '📊 Google Sheet' استفاده کنید."
    )


async def sheet_change_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تغییر شیت متصل"""
    await sheet_add_callback(update, context)


async def sheet_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """درخواست حذف اتصال"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "⚠️ حذف اتصال Google Sheet\n"
        "━━━━━━━━━━━━━━━\n\n"
        "با حذف اتصال:\n"
        "├── آپدیت خودکار قیمت متوقف می‌شود\n"
        "├── محصولات فعلی حفظ می‌شوند\n"
        "└── پست‌های کانال دست‌نخورده می‌مانند\n\n"
        "آیا مطمئن هستید؟",
        reply_markup=_get_delete_confirm_keyboard(),
    )


async def sheet_delete_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تایید حذف اتصال"""
    query = update.callback_query
    await query.answer()

    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if customer:
            await delete_sheet_connection(session, customer.id)

    await query.edit_message_text(
        "✅ اتصال Google Sheet حذف شد.\n\n"
        "برای اتصال مجدد از منوی '📊 Google Sheet' استفاده کنید."
    )


async def sheet_sync_now_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    همگام‌سازی دستی
    داده‌ها فوری آپدیت میشن
    برای ادیت پست‌ها از مشتری تایید می‌گیریم
    """
    query = update.callback_query
    await query.answer()

    user = query.from_user
    
    # چک rate limit
    if is_rate_limited(user.id, "sheet_sync", max_requests=3, time_window_seconds=300):
        await query.answer("️ شما بیش از حد مجاز درخواست داده‌اید. لطفاً ۵ دقیقه دیگر تلاش کنید.", show_alert=True)
        return

    await query.edit_message_text("🔄 در حال همگام‌سازی از Google Sheet...\nلطفاً چند لحظه صبر کنید.")

    try:
        from app.tasks.jobs.sheet_sync_job import sync_customer_sheet
        
        # گرفتن اطلاعات مشتری
        async with AsyncSessionLocal() as session:
            customer = await get_customer_by_telegram_id(session, user.id)
            if not customer:
                await query.edit_message_text("❌ مشتری یافت نشد!")
                return

        # اجرای همگام‌سازی
        sync_result = await sync_customer_sheet(
            context.bot,
            customer.id,
            edit_posts_now=False,
            is_manual=True,
        )

        #  اگر خطای مپینگ ستون‌ها رخ داده باشد، ویزارد را استارت می‌زنیم
        if sync_result.get("requires_mapping_wizard"):
            from app.bot.handlers.mapping_wizard import start_mapping_wizard_for_sheet
            await start_mapping_wizard_for_sheet(
                update=update,
                user_id=user.id,
                customer_id=customer.id,
                missing_fields=sync_result["missing_fields"],
                headers=sync_result["headers"],
                sheet_id=sync_result["sheet_id"],
            )
            return

        # بررسی خطا
        if sync_result.get("error"):
            await query.edit_message_text(
                f"❌ خطا در همگام‌سازی:\n"
                f"━━━━━━━━━━━━━━━\n"
                f"{sync_result['error']}\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"می‌تونید از منوی ' Google Sheet' →\n"
                f"'🔃 همگام‌سازی الان' دوباره امتحان کنید."
            )
            return

        # استخراج نتایج
        new_count = sync_result.get("new_count", 0)
        updated_count = sync_result.get("updated_count", 0)
        unchanged = sync_result.get("unchanged_count", 0)
        errors = sync_result.get("error_count", 0)
        price_changes = sync_result.get("price_changes", [])
        stock_changes = sync_result.get("stock_changes", [])
        pending_edits = sync_result.get("pending_edits_count", 0)

        # ساخت متن گزارش
        text = (
            f"✅ همگام‌سازی کامل شد!\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🆕 محصولات جدید: {new_count}\n"
            f"🔄 آپدیت شده: {updated_count}\n"
            f"✅ بدون تغییر: {unchanged}\n"
            f"❌ خطا: {errors}\n"
            f"━━━━━━━━━━━━━━━\n"
        )

        if price_changes:
            text += f"\n💰 تغییرات قیمت: {len(price_changes)} مورد\n"
        if stock_changes:
            text += f"📦 تغییرات موجودی: {len(stock_changes)} مورد\n"

        text += "━━━━━━━━━━━━━━━\n"

        # اگه پست‌های منتشر شده نیاز به ادیت دارن
        if pending_edits > 0:
            text += (
                f"\n⚠️ <b>توجه:</b>\n"
                f"📤 <b>{pending_edits} پست منتشر شده</b> در کانال، \n"
                f"با تغییرات جدید هنوز آپدیت نشده.\n\n"
                f"می‌خوای الان پست‌ها رو در کانال آپدیت کنم\n"
                f"یا صبر کنی در همگام‌سازی خودکار بعدی انجام بشه؟"
            )

            # ذخیره در state
            set_user_state(
                user.id,
                UserState.WAITING_EDIT_POSTS_DECISION,
                data={"customer_id": customer.id},
            )

            keyboard = [
                [
                    InlineKeyboardButton(
                        "✏️ الان آپدیت کن",
                        callback_data="sync_edit_posts_now"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⏰ بعداً (خودکار)",
                        callback_data="sync_edit_posts_later"
                    )
                ],
            ]

            await query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        else:
            # هیچ پست منتشر شده‌ای نیاز به ادیت نداره
            if price_changes or stock_changes:
                text += (
                    f"\n محصولاتی که تغییر کردن، هنوز در کانال\n"
                    f"منتشر نشدن. وقتی منتشر بشن، با قیمت جدید ارسال می‌شن."
                )
            else:
                text += "\n✅ همه چیز به‌روزه!"

            await query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="sheet_back_to_menu")]
                ]),
            )

    except Exception as e:
        log.error(f"خطا در sync دستی: {e}", exc_info=True)
        await query.edit_message_text(f"❌ خطا: {str(e)[:200]}")


async def sync_edit_posts_now_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """آپدیت الان پست‌های منتشر شده"""
    query = update.callback_query
    await query.answer()

    user = query.from_user

    if get_user_state(user.id) != UserState.WAITING_EDIT_POSTS_DECISION:
        await query.edit_message_text("❌ درخواست منقضی شده.")
        return

    user_data = get_user_data(user.id)
    customer_id = user_data.get("customer_id")

    clear_user_state(user.id)

    if not customer_id:
        await query.edit_message_text("❌ خطا!")
        return

    await query.edit_message_text("⏳ در حال آپدیت پست‌های کانال...")

    try:
        from app.tasks.jobs.sheet_sync_job import apply_pending_post_edits

        result = await apply_pending_post_edits(context.bot, customer_id)

        edited_count = result.get("edited_count", 0)

        if edited_count > 0:
            await query.edit_message_text(
                f"✅ پست‌ها آپدیت شدن!\n"
                f"━━━━━━━━━━━━━━━\n"
                f"✏️ تعداد پست‌های ویرایش شده: {edited_count}\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"💡 قیمت‌ها و موجودی‌های جدید در کانال اعمال شد."
            )
        else:
            message = result.get("message", "همه پست‌ها به‌روز بودن.")
            await query.edit_message_text(f"ℹ️ {message}")

    except Exception as e:
        log.error(f"خطا در ادیت پست‌ها: {e}", exc_info=True)
        await query.edit_message_text(f"❌ خطا: {str(e)[:200]}")


async def sync_edit_posts_later_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """رد ادیت الان - بعداً در sync خودکار انجام میشه"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    clear_user_state(user.id)

    await query.edit_message_text(
        "⏰ باشه، بعداً!\n"
        "━━━━━━━━━━━━━━━\n"
        "💡 پست‌های کانال در همگام‌سازی خودکار بعدی\n"
        "(هر ۲ ساعت) آپدیت می‌شن.\n\n"
        "📊 داده‌های محصولات در سیستم ذخیره شدن."
    )


async def sheet_get_template_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ارسال لینک Google Sheet نمونه"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    bot_email = _get_bot_service_account_email()

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            return

        from app.business.config import get_business, get_google_sheet_template_url
        business_config = get_business(customer.business_type_key)

    template_url = get_google_sheet_template_url(customer.business_type_key) if business_config else None

    if not template_url:
        await query.edit_message_text(
            "❌ برای این کسب‌وکار نمونه Google Sheet موجود نیست.\n\n"
            "لطفاً از فایل اکسل نمونه استفاده کنید.",
            reply_markup=_get_sheet_menu_keyboard(has_connection=False),
        )
        return

    text = (
        f"📊 <b>دریافت شیت نمونه</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🏢 کسب‌وکار: {business_config.emoji} {business_config.name_fa}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"🎯 <b>مراحل:</b>\n\n"
        f"1️⃣ روی لینک زیر کلیک کنید:\n"
        f"<a href=\"{template_url}\">📥 باز کردن شیت نمونه</a>\n\n"
        f"2️⃣ در صفحه باز شده، دکمه <b>Make a copy</b> را بزنید\n"
        f"(یه کپی در Google Drive شما ساخته می‌شود)\n\n"
        f"3️⃣ محصولات خودتون رو در صفحه‌های مربوطه وارد کنید\n\n"
        f"4️⃣ دکمه <b>Share</b> را بزنید\n\n"
        f"5️⃣ این ایمیل را با دسترسی <b>Editor</b> اضافه کنید:\n"
        f"<code>{bot_email}</code>\n\n"
        f"6️⃣ لینک شیت خودتون رو کپی کنید\n\n"
        f"7️⃣ برگردید و از دکمه '➕ اتصال Google Sheet' استفاده کنید\n"
        f"━━━━━━━━━━━━━━━"
    )

    keyboard = [
        [InlineKeyboardButton("➕ اتصال Google Sheet", callback_data="sheet_add")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="sheet_back_to_menu")],
    ]

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True,
    )


async def sheet_back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """برگشت به منوی اصلی Sheet"""
    query = update.callback_query
    await query.answer()

    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            return

        connection = await get_sheet_connection(session, customer.id)

        from app.business.config import get_google_sheet_template_url
        template_url = get_google_sheet_template_url(customer.business_type_key)

    has_template = bool(template_url)

    if connection:
        sync_status = connection.last_sync_status or "هنوز sync نشده"
        last_sync = (
            connection.last_sync_at.strftime("%Y/%m/%d %H:%M")
            if connection.last_sync_at
            else "هرگز"
        )

        menu_text = (
            f"📊 Google Sheet\n"
            f"━━━━━━━━━━━━━━━\n"
            f"✅ اتصال فعال\n"
            f"📄 شیت: {connection.worksheet_name}\n"
            f"🕐 آخرین همگام‌سازی: {last_sync}\n"
            f"📊 وضعیت: {sync_status}\n"
        )

        if connection.last_error:
            menu_text += f"\n⚠️ آخرین خطا:\n{connection.last_error[:200]}\n"

        menu_text += (
            f"━━━━━━━━━━━━━━━\n\n"
            f"💡 قیمت و موجودی محصولات به صورت خودکار\n"
            f"از این شیت خوانده و آپدیت می‌شوند."
        )
    else:
        menu_text = (
            f"📊 Google Sheet\n"
            f"━━━━━━━━━━━━━━━\n"
            f"❌ هنوز شیتی متصل نکرده‌اید\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"💡 با اتصال Google Sheet:\n"
            f"├── قیمت‌ها خودکار آپدیت میشن\n"
            f"├── موجودی خودکار به‌روز میشه\n"
            f"└── نیازی به آپلود مکرر اکسل نیست\n"
        )

    await query.edit_message_text(
        menu_text,
        reply_markup=_get_sheet_menu_keyboard(
            has_connection=connection is not None,
            has_template=has_template,
        ),
    )