"""
هندلرهای ویزارد مپینگ ستون‌ها (روش B)
وقتی هوش مصنوعی نتواند ستون‌ها را پیدا کند، این ویزارد اجرا می‌شود.
"""
from telegram import Update
from telegram.ext import ContextTypes
import os

from app.bot.states.user_state import UserState, get_user_state, set_user_state, get_user_data, clear_user_state
from app.bot.keyboards.mapping import get_column_mapping_keyboard
from app.services.data_input.excel_reader import read_excel_file
from app.services.product_service import save_products_from_excel
from app.database.connection import AsyncSessionLocal
from app.services.customer_service import get_customer_by_telegram_id
from app.utils.logger import log


async def start_mapping_wizard(update, user_id: int, file_path: str, business_config, headers: list, missing_fields: list):
    """استارت ویزارد سوالات"""
    
    # ذخیره داده‌های ویزارد در حافظه
    set_user_state(
        user_id, 
        UserState.WAITING_COLUMN_MAPPING,
        data={
            "file_path": file_path,
            "headers": headers,
            "missing_fields": missing_fields,  # لیست فیلدهای پیدا نشده (صف)
            "custom_map": {},                  # مپینگی که کاربر میسازه
            "ignored_fields": [],              # ستون‌هایی که کاربر زد "ندارد"
        }
    )
    
    await _ask_next_mapping_question(update, user_id)


async def _ask_next_mapping_question(update, user_id: int):
    """پرسیدن سوال بعدی از صف"""
    user_data = get_user_data(user_id)
    missing_fields = user_data.get("missing_fields", [])
    headers = user_data.get("headers", [])
    
    if not missing_fields:
        # سوالات تمام شد! اجرای پردازش نهایی
        await _finalize_and_process_file(update, user_id)
        return
        
    # گرفتن فیلد بعدی برای سوال
    next_field = missing_fields[0]
    
    text = (
        f"⚠️ <b>برخی از ستون‌ها به طور خودکار پیدا نشدند.</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"لطفاً به من کمک کنید:\n"
        f"در فایل شما، ستون مربوط به <b>«{next_field.label_fa}»</b> کدام است؟\n\n"
        f"💡 <i>اگر این اطلاعات را در فایل ندارید، دکمه 'ندارد' را در پایین بزنید.</i>"
    )
    
    keyboard = get_column_mapping_keyboard(headers)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


async def process_mapping_answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کاربر یک ستون را انتخاب کرده یا دکمه ندارد را زده است"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = get_user_data(user_id)
    
    if get_user_state(user_id) != UserState.WAITING_COLUMN_MAPPING:
        return
        
    data = query.data # "map_col_2" یا "map_col_ignore"
    
    missing_fields = user_data.get("missing_fields", [])
    current_field = missing_fields.pop(0) # برداشتن از صف
    
    if data == "map_col_ignore":
        user_data["ignored_fields"].append(current_field.key)
    else:
        col_index = int(data.replace("map_col_", ""))
        user_data["custom_map"][current_field.key] = col_index
        
    # بروزرسانی state
    set_user_state(user_id, UserState.WAITING_COLUMN_MAPPING, data=user_data)
    
    # پرسیدن سوال بعدی
    await _ask_next_mapping_question(update, user_id)


async def _finalize_and_process_file(update, user_id: int):
    """ویزارد تمام شده، حالا فایل را با مپینگ کاربر می‌خوانیم"""
    user_data = get_user_data(user_id)
    
    file_path = user_data["file_path"]
    custom_map = user_data["custom_map"]
    ignored_fields = user_data["ignored_fields"]
    
    msg = update.callback_query.message
    await msg.edit_text("✅ ستون‌ها شناسایی شدند.\n🔄 در حال پردازش فایل با تنظیمات شما...")
    
    # در اینجا دقیقاً همان لاجیک ذخیره فایل در مرحله آپلود (upload.py) را صدا می‌زنیم
    # ولی متغیرهای custom_map و ignored_fields را به read_excel_file پاس می‌دهیم.
    
    # ... (کد پردازش نهایی، پاک کردن State و حذف فایل موقت) ...
    clear_user_state(user_id)