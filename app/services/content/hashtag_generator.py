"""
تولید هشتگ هوشمند برای پست
هشتگ‌ها بر اساس داده محصول و تنظیمات کسب‌وکار تولید می‌شوند
تماماً rule-based (بدون AI)
"""

from app.business.config import BusinessConfig
from app.database.models import Product


def generate_hashtags(
    product: Product,
    business_config: BusinessConfig,
    max_hashtags: int = 7,
) -> list[str]:
    """
    تولید لیست هشتگ برای یک محصول

    ترکیب:
    - هشتگ‌های ثابت کسب‌وکار
    - هشتگ برند (از specs)
    - هشتگ رنج قیمت
    """
    hashtags = []

    # ۱) هشتگ‌های ثابت کسب‌وکار
    for tag in business_config.static_hashtags:
        if tag not in hashtags:
            hashtags.append(tag)

    # ۲) هشتگ برند
    brand = _get_brand_from_specs(product)
    if brand:
        brand_tag = _make_brand_hashtag(business_config.key, brand)
        if brand_tag and brand_tag not in hashtags:
            hashtags.append(brand_tag)

    # ۳) هشتگ رنج قیمت
    price_tag = _make_price_range_hashtag(business_config.key, int(product.price))
    if price_tag and price_tag not in hashtags:
        hashtags.append(price_tag)

    # محدود کردن به max_hashtags
    return hashtags[:max_hashtags]


def format_hashtags_for_post(hashtags: list[str]) -> str:
    """فرمت کردن هشتگ‌ها برای نمایش در پست"""
    if not hashtags:
        return ""
    return " ".join(hashtags)


def _get_brand_from_specs(product: Product) -> str | None:
    """استخراج برند از specs"""
    if not product.specs:
        return None

    brand = product.specs.get("brand")
    if brand:
        return str(brand).strip()
    return None


def _make_brand_hashtag(business_key: str, brand: str) -> str | None:
    """ساخت هشتگ برند"""
    # ترجمه برندهای معروف به فارسی
    brand_translations = {
        "lenovo": "لنوو",
        "asus": "ایسوس",
        "hp": "اچ_پی",
        "dell": "دل",
        "acer": "ایسر",
        "msi": "ام_اس_آی",
        "apple": "اپل",
        "macbook": "مک_بوک",
        "samsung": "سامسونگ",
        "huawei": "هواوی",
        "microsoft": "مایکروسافت",
        "razer": "ریزر",
    }

    brand_lower = brand.lower().strip()
    persian_brand = brand_translations.get(brand_lower)

    if not persian_brand:
        # اگه ترجمه نداشت، از خود اسم استفاده کن (بدون فاصله)
        persian_brand = brand.replace(" ", "_")

    # پیشوند بر اساس نوع کسب‌وکار
    prefix_map = {
        "laptop_store": "لپتاپ",
        "mobile_store": "موبایل",
        "clothing_store": "پوشاک",
    }

    prefix = prefix_map.get(business_key, "")
    if prefix:
        return f"#{prefix}_{persian_brand}"
    return f"#{persian_brand}"


def _make_price_range_hashtag(business_key: str, price: int) -> str | None:
    """ساخت هشتگ رنج قیمت"""
    if price <= 0:
        return None

    # تعریف رنج‌های قیمت برای هر کسب‌وکار
    price_ranges_map = {
        "laptop_store": [
            (0, 20_000_000, "زیر_۲۰_میلیون"),
            (20_000_000, 30_000_000, "زیر_۳۰_میلیون"),
            (30_000_000, 50_000_000, "زیر_۵۰_میلیون"),
            (50_000_000, 80_000_000, "زیر_۸۰_میلیون"),
            (80_000_000, 150_000_000, "زیر_۱۵۰_میلیون"),
            (150_000_000, float("inf"), "بالای_۱۵۰_میلیون"),
        ],
        "mobile_store": [
            (0, 5_000_000, "زیر_۵_میلیون"),
            (5_000_000, 10_000_000, "زیر_۱۰_میلیون"),
            (10_000_000, 20_000_000, "زیر_۲۰_میلیون"),
            (20_000_000, 40_000_000, "زیر_۴۰_میلیون"),
            (40_000_000, float("inf"), "بالای_۴۰_میلیون"),
        ],
    }

    ranges = price_ranges_map.get(business_key)
    if not ranges:
        return None

    for min_price, max_price, label in ranges:
        if min_price <= price < max_price:
            prefix_map = {
                "laptop_store": "لپتاپ",
                "mobile_store": "موبایل",
            }
            prefix = prefix_map.get(business_key, "")
            if prefix:
                return f"#{prefix}_{label}"

    return None