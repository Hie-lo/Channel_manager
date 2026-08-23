"""
تعریف کسب‌وکارهای پشتیبانی شده
هر کسب‌وکار می‌تونه چند "دسته فرعی" (SubCategory) داشته باشه
"""

from dataclasses import dataclass, field
from pathlib import Path


BUSINESS_DIR = Path(__file__).resolve().parent


@dataclass
class BusinessField:
    """یک فیلد از فرم محصول"""
    key: str
    label_fa: str
    emoji: str
    excel_column: str
    required: bool = True
    aliases: list[str] = field(default_factory=list) # ← لیست مترادف‌ها

# لیست مترادف‌های استاندارد
PRICE_ALIASES = ["قیمت", "مبلغ", "بها", "قیمت نهایی", "ارزش", "قیمت (تومان)", "price", "amount"]
STOCK_ALIASES = ["موجودی", "تعداد", "تعداد موجود", "انبار", "موجودی انبار", "stock", "qty", "quantity"]
SKU_ALIASES = ["کد", "کد محصول", "کد کالا", "شناسه", "شناسه کالا", "sku", "code", "id"]
NAME_ALIASES = ["نام", "نام محصول", "نام کالا", "عنوان", "عنوان محصول", "product_name", "title", "name"]
BRAND_ALIASES = ["برند", "مارک", "سازنده", "شرکت سازنده", "brand", "make"]

@dataclass
class SubCategory:
    """
    یک زیردسته از یک کسب‌وکار
    مثلاً: laptop_store → لپتاپ / کیس آماده / مانیتور / ...
    """
    key: str                        # laptops, monitors, ...
    name_fa: str                    # لپتاپ، مانیتور، ...
    emoji: str
    worksheet_name: str             # نام sheet در فایل اکسل (باید انگلیسی باشه)
    fields: list[BusinessField]     # فیلدهای مخصوص این دسته
    post_template_file: str         # فایل قالب پست این دسته
    static_hashtags: list[str] = field(default_factory=list)


@dataclass
class BusinessConfig:
    """تنظیمات یک کسب‌وکار"""
    key: str
    name_fa: str
    emoji: str
    description: str

    # زیردسته‌ها
    sub_categories: list[SubCategory]

    # فایل نمونه اکسل (شامل همه sheet ها)
    excel_template_file: str

    # زمان‌بندی آپدیت قیمت (بدون default)
    price_check_interval_hours: int

    # لینک Make a Copy گوگل شیت (با default)
    google_sheet_template_url: str = "https://docs.google.com/spreadsheets/d/1WDHERQgp7WiHBMci8XSgPh0m76xzs_k-/copy"


# ═══════════════════════════════════════════════════════
# فیلدهای مشترک بین همه دسته‌ها
# ═══════════════════════════════════════════════════════

COMMON_FIELDS_START = [
    BusinessField(key="sku", label_fa="کد محصول", emoji="🔖", excel_column="کد محصول", required=True),
    BusinessField(key="product_name", label_fa="نام محصول", emoji="📦", excel_column="نام محصول", required=True),
    BusinessField(key="brand", label_fa="برند", emoji="🏭", excel_column="برند", required=True),
]

COMMON_FIELDS_END = [
    BusinessField(key="price", label_fa="قیمت", emoji="💰", excel_column="قیمت", required=True),
    BusinessField(key="stock", label_fa="موجودی", emoji="📦", excel_column="موجودی", required=True),
    BusinessField(key="description", label_fa="توضیحات", emoji="📝", excel_column="توضیحات", required=False),
    BusinessField(key="image_url", label_fa="لینک عکس", emoji="🖼", excel_column="لینک عکس", required=False),
]


# ═══════════════════════════════════════════════════════
# زیردسته‌های فروشگاه کامپیوتر
# ═══════════════════════════════════════════════════════

LAPTOP_SUBCATEGORY = SubCategory(
    key="laptop",
    name_fa="لپتاپ",
    emoji="💻",
    worksheet_name="laptops",
    fields=COMMON_FIELDS_START + [
        BusinessField(key="cpu", label_fa="پردازنده", emoji="⚡", excel_column="پردازنده", required=True),
        BusinessField(key="ram", label_fa="رم", emoji="🧠", excel_column="رم", required=True),
        BusinessField(key="storage", label_fa="حافظه", emoji="💾", excel_column="حافظه", required=True),
        BusinessField(key="gpu", label_fa="گرافیک", emoji="🎮", excel_column="گرافیک", required=False),
        BusinessField(key="screen", label_fa="صفحه نمایش", emoji="📐", excel_column="صفحه نمایش", required=False),
    ] + COMMON_FIELDS_END,
    post_template_file="post_templates/computer_shop/laptop.txt",
    static_hashtags=["#لپتاپ", "#کامپیوتر"],
)


PREBUILT_PC_SUBCATEGORY = SubCategory(
    key="prebuilt_pc",
    name_fa="کیس آماده",
    emoji="🖥",
    worksheet_name="prebuilt_pcs",
    fields=COMMON_FIELDS_START + [
        BusinessField(key="cpu", label_fa="پردازنده", emoji="⚡", excel_column="پردازنده", required=True),
        BusinessField(key="ram", label_fa="رم", emoji="🧠", excel_column="رم", required=True),
        BusinessField(key="storage", label_fa="حافظه", emoji="💾", excel_column="حافظه", required=True),
        BusinessField(key="gpu", label_fa="گرافیک", emoji="🎮", excel_column="گرافیک", required=True),
        BusinessField(key="psu", label_fa="منبع تغذیه", emoji="⚡", excel_column="منبع تغذیه", required=False),
        BusinessField(key="case_model", label_fa="مدل کیس", emoji="📦", excel_column="مدل کیس", required=False),
    ] + COMMON_FIELDS_END,
    post_template_file="post_templates/computer_shop/prebuilt_pc.txt",
    static_hashtags=["#کامپیوتر_آماده", "#کیس_گیمینگ"],
)


MONITOR_SUBCATEGORY = SubCategory(
    key="monitor",
    name_fa="مانیتور",
    emoji="🖥",
    worksheet_name="monitors",
    fields=COMMON_FIELDS_START + [
        BusinessField(key="screen_size", label_fa="سایز", emoji="📐", excel_column="سایز", required=True),
        BusinessField(key="resolution", label_fa="رزولوشن", emoji="🔍", excel_column="رزولوشن", required=True),
        BusinessField(key="refresh_rate", label_fa="نرخ رفرش", emoji="⚡", excel_column="نرخ رفرش", required=False),
        BusinessField(key="panel_type", label_fa="نوع پنل", emoji="🎨", excel_column="نوع پنل", required=False),
    ] + COMMON_FIELDS_END,
    post_template_file="post_templates/computer_shop/monitor.txt",
    static_hashtags=["#مانیتور", "#مانیتور_گیمینگ"],
)


COMPONENTS_SUBCATEGORY = SubCategory(
    key="component",
    name_fa="قطعات کامپیوتر",
    emoji="⚙️",
    worksheet_name="components",
    fields=COMMON_FIELDS_START + [
        BusinessField(key="component_type", label_fa="نوع قطعه", emoji="🔧", excel_column="نوع قطعه", required=True),
        BusinessField(key="specs", label_fa="مشخصات", emoji="📋", excel_column="مشخصات", required=True),
    ] + COMMON_FIELDS_END,
    post_template_file="post_templates/computer_shop/component.txt",
    static_hashtags=["#قطعات_کامپیوتر"],
)


ACCESSORIES_SUBCATEGORY = SubCategory(
    key="accessory",
    name_fa="لوازم جانبی",
    emoji="🖱",
    worksheet_name="accessories",
    fields=COMMON_FIELDS_START + [
        BusinessField(key="accessory_type", label_fa="نوع لوازم", emoji="🎧", excel_column="نوع لوازم", required=True),
        BusinessField(key="connection", label_fa="نوع اتصال", emoji="🔌", excel_column="نوع اتصال", required=False),
        BusinessField(key="features", label_fa="ویژگی‌ها", emoji="✨", excel_column="ویژگی‌ها", required=False),
    ] + COMMON_FIELDS_END,
    post_template_file="post_templates/computer_shop/accessory.txt",
    static_hashtags=["#لوازم_جانبی_کامپیوتر"],
)


# ═══════════════════════════════════════════════════════
# تعریف کسب‌وکارها
# ═══════════════════════════════════════════════════════

COMPUTER_SHOP = BusinessConfig(
    key="computer_shop",
    name_fa="فروشگاه کامپیوتر و لوازم جانبی",
    emoji="🖥",
    description="مناسب فروشگاه‌های کامپیوتر، لپتاپ، قطعات و لوازم جانبی",
    sub_categories=[
        LAPTOP_SUBCATEGORY,
        PREBUILT_PC_SUBCATEGORY,
        MONITOR_SUBCATEGORY,
        COMPONENTS_SUBCATEGORY,
        ACCESSORIES_SUBCATEGORY,
    ],
    excel_template_file="templates/computer_shop.xlsx",
    price_check_interval_hours=24,
    google_sheet_template_url="https://docs.google.com/spreadsheets/d/1WDHERQgp7WiHBMci8XSgPh0m76xzs_k-/copy",

)

# ═══════════════════════════════════════════════════════
# کسب‌وکار موبایل و تبلت
# ═══════════════════════════════════════════════════════

MOBILE_SHOP = BusinessConfig(
    key="mobile_shop",
    name_fa="فروشگاه موبایل و تبلت",
    emoji="📱",
    description="مناسب فروشگاه‌های موبایل، تبلت، ساعت هوشمند و لوازم جانبی",
    sub_categories=[
        SubCategory(
            key="smartphone",
            name_fa="گوشی موبایل",
            emoji="📱",
            worksheet_name="smartphones",
            fields=COMMON_FIELDS_START + [
                BusinessField(key="ram", label_fa="حافظه رم", emoji="🧠", excel_column="حافظه رم", required=True),
                BusinessField(key="storage", label_fa="حافظه داخلی", emoji="💾", excel_column="حافظه داخلی", required=True),
                BusinessField(key="camera", label_fa="دوربین", emoji="📸", excel_column="دوربین", required=False),
                BusinessField(key="battery", label_fa="باتری", emoji="🔋", excel_column="باتری", required=False),
                BusinessField(key="color", label_fa="رنگ", emoji="🎨", excel_column="رنگ", required=False),
            ] + COMMON_FIELDS_END,
            post_template_file="post_templates/mobile_shop/smartphone.txt",
            static_hashtags=["#موبایل", "#گوشی_موبایل", "#خرید_گوشی"],
        )
    ],
    excel_template_file="templates/mobile_shop.xlsx",
    price_check_interval_hours=12,  # موبایل نوسان قیمت بالاتری دارد
    google_sheet_template_url="",
)

# ═══════════════════════════════════════════════════════
# کسب‌وکار پوشاک و کفش
# ═══════════════════════════════════════════════════════

CLOTHING_SHOP = BusinessConfig(
    key="clothing_shop",
    name_fa="فروشگاه پوشاک و کفش",
    emoji="👕",
    description="مناسب فروشگاه‌های لباس، کفش، کیف و اکسسوری",
    sub_categories=[
        SubCategory(
            key="clothing",
            name_fa="پوشاک",
            emoji="👗",
            worksheet_name="clothing",
            fields=COMMON_FIELDS_START + [
                BusinessField(key="size", label_fa="سایزبندی", emoji="📏", excel_column="سایزبندی", required=True),
                BusinessField(key="color", label_fa="رنگ‌بندی", emoji="🎨", excel_column="رنگ‌بندی", required=False),
                BusinessField(key="material", label_fa="جنس پارچه", emoji="🧶", excel_column="جنس", required=False),
            ] + COMMON_FIELDS_END,
            post_template_file="post_templates/clothing_shop/clothing.txt",
            static_hashtags=["#پوشاک", "#لباس", "#مد"],
        )
    ],
    excel_template_file="templates/clothing_shop.xlsx",
    price_check_interval_hours=48,  # قیمت پوشاک نوسان کمتری دارد
    google_sheet_template_url="",
)
# ═══════════════════════════════════════════════════════
# رجیستری کسب‌وکارها
# ═══════════════════════════════════════════════════════

BUSINESSES: dict[str, BusinessConfig] = {
    "computer_shop": COMPUTER_SHOP,
    "mobile_shop": MOBILE_SHOP,        # ← اضافه شد
    "clothing_shop": CLOTHING_SHOP,    # ← اضافه شد
    # "other": OTHER_STORE,
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


def get_subcategory(business_key: str, subcategory_key: str) -> SubCategory | None:
    """پیدا کردن یک زیردسته"""
    business = get_business(business_key)
    if not business:
        return None
    for sc in business.sub_categories:
        if sc.key == subcategory_key:
            return sc
    return None


def get_subcategory_by_worksheet(business_key: str, worksheet_name: str) -> SubCategory | None:
    """پیدا کردن زیردسته بر اساس نام worksheet"""
    business = get_business(business_key)
    if not business:
        return None
    for sc in business.sub_categories:
        if sc.worksheet_name.lower() == worksheet_name.lower():
            return sc
    return None


def get_subcategory_template_path(business_key: str, subcategory_key: str) -> Path | None:
    """مسیر قالب پست یک زیردسته"""
    subcategory = get_subcategory(business_key, subcategory_key)
    if not subcategory:
        return None
    return BUSINESS_DIR / subcategory.post_template_file

def get_google_sheet_template_url(business_key: str) -> str | None:
    """گرفتن لینک Google Sheet نمونه"""
    business = get_business(business_key)
    if not business or not business.google_sheet_template_url:
        return None
    return business.google_sheet_template_url


# ═══════════════════════════════════════════════════════
# کسب‌وکار سایر (کاملاً انعطاف‌پذیر و داینامیک)
# ═══════════════════════════════════════════════════════

OTHER_STORE = BusinessConfig(
    key="other",
    name_fa="سایر / فروشگاه عمومی",
    emoji="📦",
    description="مناسب برای تمامی فروشگاه‌ها (گل، کتاب، مواد غذایی، لوازم خانگی و...)",
    sub_categories=[
        SubCategory(
            key="general_item",
            name_fa="محصولات عمومی",
            emoji="📦",
            worksheet_name="products",
            fields=[
                BusinessField(key="sku", label_fa="کد محصول", emoji="🔖", excel_column="کد محصول", required=True, aliases=SKU_ALIASES),
                BusinessField(key="product_name", label_fa="نام محصول", emoji="📦", excel_column="نام محصول", required=True, aliases=NAME_ALIASES),
                BusinessField(key="brand", label_fa="برند / سازنده", emoji="🏭", excel_column="برند", required=False, aliases=BRAND_ALIASES),
                BusinessField(key="price", label_fa="قیمت", emoji="💰", excel_column="قیمت", required=True, aliases=PRICE_ALIASES),
                BusinessField(key="stock", label_fa="موجودی", emoji="📦", excel_column="موجودی", required=True, aliases=STOCK_ALIASES),
                BusinessField(key="description", label_fa="توضیحات", emoji="📝", excel_column="توضیحات", required=False, aliases=["توضیحات", "شرح", "desc", "description"]),
                BusinessField(key="image_url", label_fa="لینک عکس", emoji="🖼", excel_column="لینک عکس", required=False, aliases=["لینک عکس", "عکس", "تصویر", "image", "photo"]),
            ],
            post_template_file="post_templates/other/general.txt",
            static_hashtags=["#فروشگاه", "#خرید_آنلاین"],
        )
    ],
    excel_template_file="templates/other.xlsx",
    price_check_interval_hours=24,
)

# اضافه کردن به دیکشنری BUSINESSES
BUSINESSES["other"] = OTHER_STORE