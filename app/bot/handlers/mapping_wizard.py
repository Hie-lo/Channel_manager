"""
هندلرهای ویزارد مپینگ ستون‌ها (روش B)
وقتی هوش مصنوعی نتواند ستون‌ها را پیدا کند، این ویزارد اجرا می‌شود.
"""

import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from app.bot.states.user_state import (
    UserState,
    set_user_state,
    get_user_state,
    get_user_data,
    clear_user_state,
)
from app.bot.keyboards.mapping import get_column_mapping_keyboard
from app.services.data_input.excel_reader import read_excel_file
from app.services.product_service import save_products_from_excel
from app.services.customer_service import get_customer_by_telegram_id
from app.services.business_service import (
    get_business_config_for_customer,
    get_business_for_customer,
)
from app.services.subscription.service import get_active_subscription
from app.services.subscription.plans import get_plan
from app.database.connection import AsyncSessionLocal
from app.utils.logger import log


async def start_mapping_wizard(
    update,
    user_id: int,
    file_path: str,
    business_config,
    headers: list,
    missing_fields: list,
    context: ContextTypes.DEFAULT_TYPE,
):
    """استارت ویزارد سوالات مپینگ ستون‌ها برای اکسل"""
    set_user_state(
        user_id,
        UserState.WAITING_COLUMN_MAPPING,
        data={
            "source": "excel",
            "file_path": file_path,
            "headers": headers,
            "missing_fields": missing_fields,
            "custom_map": {},
            "ignored_fields": [],
        },
    )

    await _ask_next_mapping_question(update, user_id, context)


async def start_mapping_wizard_for_sheet(
    update: Update,
    user_id: int,
    customer_id: int,
    missing_fields: list,
    headers: list,
    sheet_id: str,
    context: ContextTypes.DEFAULT_TYPE,
):
    """شروع ویزارد مپینگ برای گوگل‌شیت"""
    set_user_state(
        user_id,
        UserState.WAITING_COLUMN_MAPPING,
        data={
            "source": "google_sheet",
            "customer_id": customer_id,
            "sheet_id": sheet_id,
            "headers": headers,
            "missing_fields": missing_fields,
            "custom_map": {},
            "ignored_fields": [],
        },
    )

    await _ask_next_mapping_question(update, user_id, context)


async def _ask_next_mapping_question(update, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """پرسیدن سوال بعدی از صف"""
    user_data = get_user_data(user_id)
    missing_fields = user_data.get("missing_fields", [])
    headers = user_data.get("headers", [])

    if not missing_fields:
        # سوالات تمام شد! اجرای پردازش نهایی
        await _finalize_and_process_file(update, user_id, context)
        return

    # گرفتن فیلد بعدی برای سوال
    next_field = missing_fields[0]

    text = (
        f"⚠️ <b>برخی از ستون‌ها به طور خودکار پیدا نشدند.</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"لطفاً به من کمک کنید:\n"
        f"در فایل شما، ستون مربوط به <b>«{next_field.label_fa}»</b> کدام است؟\n\n"
        f"<i>اگر این اطلاعات را در فایل ندارید، دکمه 'نادیده بگیر' را بزنید.</i>"
    )

    keyboard = get_column_mapping_keyboard(headers)

    if hasattr(update, "callback_query") and update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode="HTML", reply_markup=keyboard
        )
    elif hasattr(update, "message") and update.message:
        await update.message.reply_text(
            text, parse_mode="HTML", reply_markup=keyboard
        )


async def process_mapping_answer_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """کاربر یک ستون را انتخاب کرده یا دکمه ندارد/نادیده بگیر را زده است"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_data = get_user_data(user_id)

    if get_user_state(user_id) != UserState.WAITING_COLUMN_MAPPING:
        return

    data = query.data  # "map_col_2" یا "map_col_ignore"

    missing_fields = user_data.get("missing_fields", [])
    if not missing_fields:
        await _finalize_and_process_file(update, user_id, context)
        return

    current_field = missing_fields.pop(0)  # برداشتن از صف

    if data == "map_col_ignore":
        if "ignored_fields" not in user_data:
            user_data["ignored_fields"] = []
        user_data["ignored_fields"].append(current_field.key)
    elif data.startswith("map_col_"):
        col_index = int(data.replace("map_col_", ""))
        if "custom_map" not in user_data:
            user_data["custom_map"] = {}

        # 🛡️ جلوگیری از تخصیص یک ستون به دو فیلد مختلف (اشتباه کلیک کاربر)
        duplicate_field = next(
            (k for k, v in user_data["custom_map"].items() if v == col_index),
            None,
        )
        if duplicate_field:
            missing_fields.insert(0, current_field)  # همون سوال دوباره پرسیده بشه
            set_user_state(user_id, UserState.WAITING_COLUMN_MAPPING, data=user_data)
            headers = user_data.get("headers", [])
            await query.edit_message_text(
                f"⚠️ این ستون قبلاً برای فیلد دیگه‌ای انتخاب شده.\n\n"
                f"لطفاً ستون <b>«{current_field.label_fa}»</b> رو از بین ستون‌های "
                f"باقی‌مونده انتخاب کن یا 'نادیده بگیر' رو بزن.",
                parse_mode="HTML",
                reply_markup=get_column_mapping_keyboard(headers),
            )
            return

        user_data["custom_map"][current_field.key] = col_index

    # بروزرسانی state
    set_user_state(user_id, UserState.WAITING_COLUMN_MAPPING, data=user_data)

    # پرسیدن سوال بعدی
    await _ask_next_mapping_question(update, user_id, context)


async def mapping_cancel_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """انصراف کامل از ویزارد مپینگ و حذف فایل موقت"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_data = get_user_data(user_id)

    # حذف فایل موقت
    file_path = user_data.get("file_path")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            log.error(f"خطا در حذف فایل موقت هنگام لغو مپینگ: {e}")

    clear_user_state(user_id)

    await query.edit_message_text(
        "❌ عملیات خواندن فایل لغو شد.\n\n"
        "می‌توانید فایل جدیدی آپلود کنید یا نام ستون‌های فایل قبلی را اصلاح کنید."
    )


async def _finalize_and_process_file(update, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """ویزارد تمام شده، حالا فایل را با مپینگ کاربر می‌خوانیم"""
    user_data = get_user_data(user_id)
    source = user_data.get("source", "excel")
    file_path = user_data.get("file_path")
    custom_map = user_data.get("custom_map", {})
    ignored_fields = user_data.get("ignored_fields", [])

    query = update.callback_query
    await query.edit_message_text(
        "✅ ستون‌ها شناسایی شدند.\n در حال پردازش داده‌ها با تنظیمات شما..."
    )
    
    try:
        if source == "google_sheet":
            customer_id = user_data["customer_id"]
            
            from app.tasks.jobs.sheet_sync_job import sync_customer_sheet
            sync_result = await sync_customer_sheet(
                context.bot,  # ✅ استفاده صحیح از context.bot
                customer_id,
                edit_posts_now=True,
                is_manual=True,
                custom_maps=custom_map,
                ignored_fields=ignored_fields,
            )

            clear_user_state(user_id)
            if sync_result.get("error"):
                await query.edit_message_text(f"❌ خطا در همگام‌سازی: {sync_result['error']}")
            else:
                summary = (
                    f" <b>همگام‌سازی گوگل‌شیت با موفقیت انجام شد!</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"🆕 محصولات جدید: {sync_result.get('new_count', 0)}\n"
                    f"🔄 بروزرسانی شده: {sync_result.get('updated_count', 0)}\n"
                    f"━━━━━━━━━━━━━━━"
                )

                skipped_count = sync_result.get("skipped_count", 0)
                if skipped_count:
                    summary += (
                        f"\n\n⚠️ <b>{skipped_count} ردیف به‌خاطر اطلاعات ناقص/نامعتبر خونده نشدن.</b>\n"
                        f"لطفاً این ردیف‌ها رو توی شیت تکمیل کن، خودشون در sync بعدی اضافه می‌شن:\n"
                    )
                    for line in sync_result.get("skipped_rows", [])[:10]:
                        summary += f"• {line}\n"

                await query.edit_message_text(summary, parse_mode="HTML")
            return

        # پردازش اکسل عادی
        async with AsyncSessionLocal() as session:
            customer = await get_customer_by_telegram_id(session, user_id)
            if not customer:
                await query.edit_message_text("❌ مشتری پیدا نشد!")
                clear_user_state(user_id)
                return

            business_config = get_business_config_for_customer(customer)
            business = await get_business_for_customer(session, customer.id)
            subscription = await get_active_subscription(session, customer.id)

            if not business_config or not subscription:
                await query.edit_message_text("❌ اطلاعات کسب‌وکار یا اشتراک یافت نشد.")
                clear_user_state(user_id)
                return

            plan = get_plan(subscription.plan_key)
            business_id = business.id if business else None

            # خواندن با مپینگ سفارشی
            read_result = read_excel_file(
                file_path=file_path,
                business_config=business_config,
                custom_map=custom_map,
                ignored_fields=ignored_fields,
            )

            # ذخیره محصولات در دیتابیس
            save_result = await save_products_from_excel(
                session=session,
                customer_id=customer.id,
                business_id=business_id,
                products_data=read_result.all_products,
                max_products_limit=plan.max_products,
            )

        summary_text = (
            f"🎉 <b>پردازش فایل با موفقیت انجام شد!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🆕 محصولات جدید: {save_result.new_count}\n"
            f"🔄 آپدیت شده: {save_result.updated_count}\n"
            f"✅ بدون تغییر: {save_result.unchanged_count}\n"
            f" خطا: {save_result.error_count}\n"
            f"━━━━━━━━━━━━━━━"
        )

        await query.edit_message_text(summary_text, parse_mode="HTML")

    except Exception as e:
        log.error(f"خطا در پردازش نهایی فایل مپینگ: {e}", exc_info=True)
        await query.edit_message_text(f"❌ خطا در پردازش فایل: {str(e)[:200]}")

    finally:
        clear_user_state(user_id)
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass