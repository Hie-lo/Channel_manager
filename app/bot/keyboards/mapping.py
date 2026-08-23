"""
کیبوردهای مربوط به ویزارد مپینگ ستون‌ها
"""
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

def get_column_mapping_keyboard(headers: list[str]) -> InlineKeyboardMarkup:
    """ساخت دکمه‌های شیشه‌ای بر اساس هدرهای فایل اکسل/شیت"""
    keyboard = []
    
    # دکمه‌های ستون‌ها (دو تا در هر ردیف)
    row = []
    for idx, header in enumerate(headers):
        # تلگرام محدودیت حجم دیتا داره، نام هدر رو کوتاه می‌کنیم
        btn_text = str(header)[:25] if header else f"ستون {idx+1} (بدون نام)"
        row.append(InlineKeyboardButton(btn_text, callback_data=f"map_col_{idx}"))
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
            
    if row:
        keyboard.append(row)
        
    # دکمه "ندارد" و "لغو" در پایین
    keyboard.append([InlineKeyboardButton("❌ در فایل من وجود ندارد (نادیده بگیر)", callback_data="map_col_ignore")])
    keyboard.append([InlineKeyboardButton("🚫 لغو کامل عملیات", callback_data="map_cancel")])
    
    return InlineKeyboardMarkup(keyboard)