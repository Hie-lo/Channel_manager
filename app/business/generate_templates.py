"""
تولید فایل‌های نمونه اکسل برای هر کسب‌وکار
این اسکریپت رو دستی اجرا می‌کنیم:
python -m app.business.generate_templates
"""

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from app.business.config import get_all_businesses, BUSINESS_DIR


# ─── استایل‌ها ───
HEADER_FONT = Font(name="Tahoma", size=11, bold=True, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="2E86DE", end_color="2E86DE", fill_type="solid")
DATA_FONT = Font(name="Tahoma", size=10)
CENTER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)


def create_laptop_template():
    """ساخت فایل نمونه اکسل برای فروش لپتاپ"""

    wb = Workbook()
    ws = wb.active
    ws.title = "محصولات"
    ws.sheet_view.rightToLeft = True  # فارسی راست به چپ

    # ستون‌ها
    headers = [
        "کد محصول", "نام محصول", "برند", "پردازنده", "رم",
        "حافظه", "گرافیک", "صفحه نمایش", "قیمت", "موجودی",
        "توضیحات", "لینک عکس",
    ]

    # نوشتن هدر
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER_ALIGN
        cell.border = BORDER

    # داده‌های نمونه
    sample_data = [
        [
            "LP001", "IdeaPad 5 Pro", "Lenovo", "Core i7-12700H", "16GB",
            "512GB SSD", "RTX 3050 4GB", "16 اینچ 2.5K", 42500000, 5,
            "لپتاپی قدرتمند برای کار و بازی حرفه‌ای", "https://example.com/img1.jpg",
        ],
        [
            "LP002", "ROG Strix G16", "ASUS", "Core i9-13900H", "32GB",
            "1TB SSD", "RTX 4060 8GB", "16 اینچ FHD 165Hz", 65000000, 3,
            "لپتاپ گیمینگ فوق‌العاده", "https://example.com/img2.jpg",
        ],
        [
            "LP003", "Pavilion 15", "HP", "Ryzen 5-7530U", "8GB",
            "256GB SSD", "Vega 7", "15.6 اینچ FHD", 28000000, 0,
            "", "",
        ],
    ]

    for row_num, row_data in enumerate(sample_data, 2):
        for col_num, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col_num, value=value)
            cell.font = DATA_FONT
            cell.alignment = CENTER_ALIGN
            cell.border = BORDER

    # تنظیم عرض ستون‌ها
    column_widths = {
        1: 12,   # کد محصول
        2: 22,   # نام محصول
        3: 12,   # برند
        4: 18,   # پردازنده
        5: 10,   # رم
        6: 15,   # حافظه
        7: 15,   # گرافیک
        8: 20,   # صفحه نمایش
        9: 15,   # قیمت
        10: 10,  # موجودی
        11: 40,  # توضیحات
        12: 30,  # لینک عکس
    }
    for col_num, width in column_widths.items():
        ws.column_dimensions[get_column_letter(col_num)].width = width

    # ارتفاع هدر
    ws.row_dimensions[1].height = 35

    # مسیر فایل
    template_dir = BUSINESS_DIR / "templates"
    template_dir.mkdir(exist_ok=True)

    file_path = template_dir / "laptop_store.xlsx"
    wb.save(file_path)
    print(f"✅ فایل ساخته شد: {file_path}")


def create_laptop_post_template():
    """ساخت قالب پست پیش‌فرض برای لپتاپ"""

    template_text = """🖥 {product_name}

🏭 برند: {brand}
⚡ پردازنده: {cpu}
🧠 رم: {ram}
💾 حافظه: {storage}
🎮 گرافیک: {gpu}
📐 صفحه: {screen}
─────────────────
💰 قیمت: {price} تومان
📦 {stock_status}
─────────────────
{description_block}

{hashtags}

📞 {contact}
🔄 {update_date}"""

    template_dir = BUSINESS_DIR / "post_templates"
    template_dir.mkdir(exist_ok=True)

    file_path = template_dir / "laptop_store.txt"
    file_path.write_text(template_text, encoding="utf-8")
    print(f"✅ قالب پست ساخته شد: {file_path}")


def main():
    """تولید همه فایل‌ها"""
    print("🔨 در حال تولید فایل‌های نمونه...")
    print()

    create_laptop_template()
    create_laptop_post_template()

    print()
    print("✅ همه فایل‌ها ساخته شدند!")


if __name__ == "__main__":
    main()