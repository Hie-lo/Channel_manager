"""
تعریف کسب‌وکارهای پشتیبانی شده
هر کسب‌وکار یه dict داره با تنظیمات کامل
"""

from dataclasses import dataclass, field
from pathlib import Path


BUSINESS_DIR = Path(__file__).resolve().parent


@dataclass
class BusinessField:
    """یک فیلد از فرم محصول"""
    key: str              # کلید فنی (مثلاً "cpu")
    label_fa: str         # نام فارسی (مثلاً "پردازنده")
    emoji: str            # ایموجی (مثلاً "⚡")
    excel_column: str     # اسم ستون در اکسل (مثلاً "پردازنده")
    required: bool = True # اجباری هست یا نه


@dataclass
class BusinessConfig:
    """تنظیمات یک کسب‌وکار"""
    key: str                           # کلید یکتا
    name_fa: str                       # نام فارسی
    emoji: str                         # ایموجی
    description: str                   # توضیح کوتاه

    # فیلدهای محصول
    fields: list[BusinessField]

    # فایل نمونه
    excel_template_file: str           # مسیر فایل نمونه
    post_template_file: str            # مسیر قالب پست

    # زمان‌بندی آپدیت قیمت
    price_check_interval_hours: int    # چند ساعت یکبار

    # هشتگ‌های ثابت
    static_hashtags: list[str] = field(default_factory=list)


# ─── تعریف کسب‌وکار لپتاپ ───
LAPTOP_STORE = BusinessConfig(
    key="laptop_store",
    name_fa="فروش لپتاپ و کامپیوتر",
    emoji="💻",
    description="مناسب فروشگاه‌های لپتاپ، کامپیوتر، آل‌این‌وان",

    fields=[
        BusinessField(
            key="sku",
            label_fa="کد محصول",
            emoji="🔖",
            excel_column="کد محصول",
            required=True,
        ),
        BusinessField(
            key="product_name",
            label_fa="نام محصول",
            emoji="🖥",
            excel_column="نام محصول",
            required=True,
        ),
        BusinessField(
            key="brand",
            label_fa="برند",
            emoji="🏭",
            excel_column="برند",
            required=True,
        ),
        BusinessField(
            key="cpu",
            label_fa="پردازنده",
            emoji="⚡",
            excel_column="پردازنده",
            required=True,
        ),
        BusinessField(
            key="ram",
            label_fa="رم",
            emoji="🧠",
            excel_column="رم",
            required=True,
        ),
        BusinessField(
            key="storage",
            label_fa="حافظه",
            emoji="💾",
            excel_column="حافظه",
            required=True,
        ),
        BusinessField(
            key="gpu",
            label_fa="گرافیک",
            emoji="🎮",
            excel_column="گرافیک",
            required=False,
        ),
        BusinessField(
            key="screen",
            label_fa="صفحه نمایش",
            emoji="📐",
            excel_column="صفحه نمایش",
            required=False,
        ),
        BusinessField(
            key="price",
            label_fa="قیمت (تومان)",
            emoji="💰",
            excel_column="قیمت",
            required=True,
        ),
        BusinessField(
            key="stock",
            label_fa="موجودی",
            emoji="📦",
            excel_column="موجودی",
            required=True,
        ),
        BusinessField(
            key="description",
            label_fa="توضیحات",
            emoji="📝",
            excel_column="توضیحات",
            required=False,
        ),
        BusinessField(
            key="image_url",
            label_fa="لینک عکس",
            emoji="🖼",
            excel_column="لینک عکس",
            required=False,
        ),
    ],

    excel_template_file="templates/laptop_store.xlsx",
    post_template_file="post_templates/laptop_store.txt",

    price_check_interval_hours=24,  # روزانه

    static_hashtags=["#لپتاپ", "#کامپیوتر", "#خرید_لپتاپ"],
)


# ─── تمام کسب‌وکارها ───
BUSINESSES: dict[str, BusinessConfig] = {
    "laptop_store": LAPTOP_STORE,
    # در آینده اضافه می‌کنیم:
    # "mobile_store": MOBILE_STORE,
    # "clothing_store": CLOTHING_STORE,
}


def get_business(key: str) -> BusinessConfig | None:
    """دریافت تنظیمات یک کسب‌وکار"""
    return BUSINESSES.get(key)


def get_all_businesses() -> list[BusinessConfig]:
    """لیست همه کسب‌وکارها"""
    return list(BUSINESSES.values())


def get_business_excel_path(key: str) -> Path | None:
    """مسیر کامل فایل نمونه اکسل"""
    business = get_business(key)
    if not business:
        return None
    return BUSINESS_DIR / business.excel_template_file


def get_business_template_path(key: str) -> Path | None:
    """مسیر کامل قالب پست"""
    business = get_business(key)
    if not business:
        return None
    return BUSINESS_DIR / business.post_template_file