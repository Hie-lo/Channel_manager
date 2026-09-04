"""تولید هشتگ‌های مرتبط با محصول."""

import re
from app.business.config import BusinessConfig, get_subcategory
from app.database.models import Product

BRAND_TAGS = {
    "hp": "#HP", "hewlett packard": "#HP", "dell": "#Dell",
    "toshiba": "#Toshiba", "fujitsu": "#Fujitsu", "lenovo": "#Lenovo",
    "samsung": "#Samsung", "sony": "#Sony", "vaio": "#VAIO",
    "asus": "#ASUS", "acer": "#Acer", "msi": "#MSI", "microsoft": "#Microsoft",
    "apple": "#Apple", "alienware": "#Alienware", "panasonic": "#Panasonic",
    "nec": "#NEC", "stone": "#Stone", "razer": "#RAZER",
}

PRICE_RANGES = (
    (10_000_000, 20_000_000, "10تا20تومان"),
    (20_000_000, 30_000_000, "20تا30تومان"),
    (30_000_000, 40_000_000, "30تا40تومان"),
    (40_000_000, 50_000_000, "40تا50تومان"),
    (50_000_000, 60_000_000, "50تا60تومان"),
    (60_000_000, 80_000_000, "60تا80تومان"),
    (80_000_000, 100_000_000, "80تا100تومان"),
    (100_000_000, 150_000_000, "100تا150تومان"),
    (150_000_000, 200_000_000, "150تا200تومان"),
    (200_000_000, 250_000_000, "200تا250تومان"),
    (250_000_000, 300_000_000, "250تا300تومان"),
    (300_000_000, 400_000_000, "300تا400تومان"),
    (400_000_000, 500_000_000, "400تا500تومان"),
    (500_000_000, 600_000_000, "500تا600تومان"),
)


def _specs(product: Product) -> dict:
    return getattr(product, "specs", None) or {}


def _text(value) -> str:
    return str(value or "").strip().lower()


def _has_any(text: str, values: tuple[str, ...]) -> bool:
    return any(value in text for value in values)


def _is_yes(value) -> bool:
    return _text(value) in {"yes", "true", "1", "بله", "دارد", "داره"}


def generate_hashtags(
    product: Product,
    business_config: BusinessConfig | None = None,
    max_hashtags: int = 9,
) -> list[str]:
    """تولید هشتگ‌های واقعی و مرتبط از اطلاعات محصول."""
    tags: list[str] = []

    def add(tag: str | None) -> None:
        if tag and tag not in tags:
            tags.append(tag)

    subcategory_key = getattr(product, "sub_category_key", None) or ""
    if business_config and not subcategory_key and business_config.sub_categories:
        subcategory_key = business_config.sub_categories[0].key
    if business_config and subcategory_key:
        subcategory = get_subcategory(business_config.key, subcategory_key)
        if subcategory:
            for tag in subcategory.static_hashtags:
                add(tag)
    category_tags = {
        "laptop": ("#لپتاپ", "#کامپیوتر"),
        "prebuilt_pc": ("#کیس_آماده", "#کامپیوتر"),
        "monitor": ("#مانیتور",),
        "component": ("#قطعات_کامپیوتر",),
        "accessory": ("#لوازم_جانبی",),
    }
    for tag in category_tags.get(subcategory_key, ()):
        add(tag)

    specs = _specs(product)
    brand_value = specs.get("brand")
    brand = _text(brand_value)
    add(BRAND_TAGS.get(brand))
    if brand and brand not in BRAND_TAGS:
        add("#" + re.sub(r"[^\w]+", "_", str(brand_value).strip()).strip("_"))

    try:
        price = int(float(getattr(product, "price", 0) or 0))
    except (TypeError, ValueError):
        price = 0
    if price > 0:
        for minimum, maximum, label in PRICE_RANGES:
            if minimum <= price < maximum:
                add(f"#{label}")
                break

    all_values = " ".join(_text(value) for value in specs.values())
    all_text = f"{_text(getattr(product, 'product_name', ''))} {all_values}"
    gpu = _text(specs.get("gpu") or specs.get("graphics"))
    cpu = _text(specs.get("cpu") or specs.get("processor"))
    is_laptop = subcategory_key == "laptop"
    is_gaming = _has_any(all_text, ("gaming", "گیم", "گیمنگ"))

    if gpu and not _has_any(gpu, ("integrated", "onboard", "آن برد", "ندارد", "without", "intel hd")):
        add("#گرافیک")
    if is_gaming:
        add("#گیمینگ")
    if _has_any(all_text, ("accounting", "حسابداری")):
        add("#حسابداری")
    if _has_any(all_text, ("light", "سبک", "ultrabook")):
        add("#سبک")
    if _has_any(all_text, ("tablet", "تبلت", "2-in-1", "convertible")):
        add("#تبلت_شو")
    if _has_any(all_text, ("render", "رندر", "workstation")):
        add("#رندرینگ")
        add("#رندر")
    touch_enabled = _is_yes(specs.get("touch_screen"))
    pen_enabled = _is_yes(specs.get("pen_support"))
    x360_enabled = _is_yes(specs.get("x360"))
    if touch_enabled:
        add("#لمسی")
    if touch_enabled and x360_enabled:
        add("#چرخشی_لمسی")
    if pen_enabled:
        add("#Pen")
    if _has_any(all_text, ("chromebook", "کروم_بوک")):
        add("#CHROMEBOOK")
    if _is_yes(specs.get("lte")):
        add("#LTE")
    if _has_any(all_text, ("new", "نو", "آکبند", "استوک نو")):
        add("#Brand_New")
    if "vaio" in all_text:
        add("#VAIO")

    # برچسب‌های کاربردی فقط با نشانه‌های واقعی محصول اضافه می‌شوند.
    if is_laptop and not is_gaming:
        if _has_any(all_text, ("student", "دانشجو", "دانشجویی")) or "i3" in cpu or "i5" in cpu:
            add("#دانشجویی")
        if _has_any(all_text, ("office", "اداری", "حسابداری", "business")) or "i3" in cpu or "i5" in cpu:
            add("#اداری")
        if _has_any(all_text, ("home", "خانگی", "منزل")) or (price > 0 and price <= 30_000_000 and not gpu):
            add("#کاربری_روزانه")
            add("#وبگردی")
    if _has_any(all_text, ("programming", "programmer", "برنامه نویسی", "برنامه‌نویسی", "کدنویسی", "developer")):
        add("#برنامه_نویسی")
    if is_laptop and not is_gaming and _has_any(all_text, ("student", "دانشجو", "دانشجویی")):
        add("#دانشجویی")
    if is_laptop and not is_gaming and _has_any(all_text, ("school", "دانش_آموز", "دانش‌آموز", "دانش آموز")):
        add("#دانش_آموزی")
    if is_laptop and not is_gaming and _has_any(all_text, ("seminary", "طلبه", "طلبگی")):
        add("#طلبگی")
    if _has_any(all_text, ("photoshop", "فتوشاپ", "illustrator", "ایلاستریتور", "graphic design", "طراحی")):
        add("#طراحی_فتوشاپ")
    if _has_any(all_text, ("editing", "تدوین", "premiere", "پریمیر", "video")):
        add("#تدوین")

    for generation in range(1, 15):
        if f"نسل{generation}" in all_text or re.search(rf"\b{generation}(?:th|st|nd|rd)\b", all_text):
            add(f"#نسل{generation}")
            break

    for cpu_tag in ("i3", "i5", "i7", "i9", "xeon"):
        if re.search(rf"\b{cpu_tag}\b", cpu):
            add(f"#{cpu_tag}")
    if "amd" in cpu:
        add("#AMD")
    if "ryzen" in cpu:
        add("#Ryzen")

    return tags[:max_hashtags]


def format_hashtags_for_post(hashtags: list[str]) -> str:
    return " ".join(hashtags) if hashtags else ""


def _get_brand_from_specs(product: Product) -> str | None:
    value = _specs(product).get("brand")
    return str(value).strip() if value else None


def _make_brand_hashtag(sub_category_key: str, brand: str) -> str | None:
    if sub_category_key == "laptop_store":
        sub_category_key = "laptop"
    prefix = {"laptop": "لپتاپ", "prebuilt_pc": "کیس", "monitor": "مانیتور"}.get(sub_category_key)
    known = {"lenovo": "لنوو", "asus": "ایسوس", "hp": "اچ_پی", "dell": "دل", "acer": "ایسر", "msi": "ام_اس_آی"}
    name = known.get(brand.lower().strip(), brand.strip().replace(" ", "_"))
    return f"#{prefix}_{name}" if prefix else f"#{name}"


def _make_price_range_hashtag(sub_category_key: str, price: int) -> str | None:
    if price <= 0:
        return None
    for minimum, maximum, label in PRICE_RANGES:
        if minimum <= price < maximum:
            return f"#{label}"
    return None
