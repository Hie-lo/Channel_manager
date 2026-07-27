"""
تولید هشتگ هوشمند
هشتگ‌ها بر اساس زیردسته و برند تولید می‌شوند
"""

from app.business.config import BusinessConfig, get_subcategory
from app.database.models import Product


def generate_hashtags(
    product: Product,
    business_config: BusinessConfig,
    max_hashtags: int = 7,
) -> list[str]:
    """تولید لیست هشتگ برای یک محصول"""
    hashtags = []

    # ۱) هشتگ‌های ثابت زیردسته
    if product.sub_category_key:
        subcategory = get_subcategory(business_config.key, product.sub_category_key)
        if subcategory:
            for tag in subcategory.static_hashtags:
                if tag not in hashtags:
                    hashtags.append(tag)

    # ۲) هشتگ برند
    brand = _get_brand_from_specs(product)
    if brand:
        brand_tag = _make_brand_hashtag(product.sub_category_key, brand)
        if brand_tag and brand_tag not in hashtags:
            hashtags.append(brand_tag)

    # ۳) هشتگ رنج قیمت
    price_tag = _make_price_range_hashtag(product.sub_category_key, int(product.price))
    if price_tag and price_tag not in hashtags:
        hashtags.append(price_tag)

    return hashtags[:max_hashtags]


def format_hashtags_for_post(hashtags: list[str]) -> str:
    if not hashtags:
        return ""
    return " ".join(hashtags)


def _get_brand_from_specs(product: Product) -> str | None:
    """استخراج برند"""
    if not product.specs:
        return None

    brand = product.specs.get("brand")
    if brand:
        return str(brand).strip()
    return None


def _make_brand_hashtag(sub_category_key: str, brand: str) -> str | None:
    """ساخت هشتگ برند"""
    brand_translations = {
        "lenovo": "لنوو",
        "asus": "ایسوس",
        "hp": "اچ_پی",
        "dell": "دل",
        "acer": "ایسر",
        "msi": "ام_اس_آی",
        "apple": "اپل",
        "samsung": "سامسونگ",
        "logitech": "لاجیتک",
        "corsair": "کورسیر",
        "kingston": "کینگستون",
        "amd": "ای_ام_دی",
        "intel": "اینتل",
        "nvidia": "انویدیا",
        "sennheiser": "سنهایزر",
    }

    brand_lower = brand.lower().strip()
    persian_brand = brand_translations.get(brand_lower)

    if not persian_brand:
        persian_brand = brand.replace(" ", "_")

    # پیشوند بر اساس زیردسته
    prefix_map = {
        "laptop": "لپتاپ",
        "prebuilt_pc": "کیس",
        "monitor": "مانیتور",
        "component": "قطعه",
        "accessory": "لوازم_جانبی",
    }

    prefix = prefix_map.get(sub_category_key or "", "")
    if prefix:
        return f"#{prefix}_{persian_brand}"
    return f"#{persian_brand}"


def _make_price_range_hashtag(sub_category_key: str, price: int) -> str | None:
    """هشتگ رنج قیمت"""
    if price <= 0:
        return None

    # رنج‌های قیمت برای هر زیردسته
    price_ranges_map = {
        "laptop": [
            (0, 20_000_000, "زیر_۲۰_میلیون"),
            (20_000_000, 30_000_000, "زیر_۳۰_میلیون"),
            (30_000_000, 50_000_000, "زیر_۵۰_میلیون"),
            (50_000_000, 80_000_000, "زیر_۸۰_میلیون"),
            (80_000_000, float("inf"), "بالای_۸۰_میلیون"),
        ],
        "prebuilt_pc": [
            (0, 20_000_000, "زیر_۲۰_میلیون"),
            (20_000_000, 40_000_000, "زیر_۴۰_میلیون"),
            (40_000_000, 70_000_000, "زیر_۷۰_میلیون"),
            (70_000_000, float("inf"), "بالای_۷۰_میلیون"),
        ],
        "monitor": [
            (0, 10_000_000, "زیر_۱۰_میلیون"),
            (10_000_000, 20_000_000, "زیر_۲۰_میلیون"),
            (20_000_000, float("inf"), "بالای_۲۰_میلیون"),
        ],
    }

    ranges = price_ranges_map.get(sub_category_key or "")
    if not ranges:
        return None

    prefix_map = {
        "laptop": "لپتاپ",
        "prebuilt_pc": "کیس",
        "monitor": "مانیتور",
    }

    prefix = prefix_map.get(sub_category_key or "", "")
    if not prefix:
        return None

    for min_price, max_price, label in ranges:
        if min_price <= price < max_price:
            return f"#{prefix}_{label}"

    return None