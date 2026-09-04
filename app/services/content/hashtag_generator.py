import re
from typing import Callable, Any
from dataclasses import dataclass
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

# ==================================================
#  توابع کمکی عمومی
# ==================================================

def _text(value: Any) -> str:
    return str(value or "").strip().lower()

def _has_any(text: str, words: tuple[str, ...]) -> bool:
    return any(w in text for w in words)

def _is_yes(value: Any) -> bool:
    return _text(value) in {"yes", "true", "1", "بله", "دارد", "داره"}

def _get_price(product: Product) -> int:
    try:
        p = getattr(product, "price", 0) or 0
        return int(float(p))
    except (TypeError, ValueError):
        return 0

# ==================================================
#  توابع شرط (همگی با امضای (specs, all_text, price))
# ==================================================

def has_discrete_gpu(specs: dict, all_text: str, price: int) -> bool:
    gpu = _text(specs.get("gpu") or specs.get("graphics"))
    if not gpu:
        return False
    # رد کردن موارد onboard / integrated
    if _has_any(gpu, ("integrated", "onboard", "آن برد", "ندارد", "without", "intel hd", "intel hd graphics")):
        return False
    # تشخیص نام‌های معروف کارت‌های مجزا
    if _has_any(gpu, ("nvidia", "amd", "geforce", "radeon", "rtx", "gtx", "rx")):
        return True
    # اگر در all_text به discrete یا مجزا اشاره شده باشد
    if "discrete" in all_text or "مجزا" in all_text:
        return True
    return False

def is_gaming(specs: dict, all_text: str, price: int) -> bool:
    return _has_any(all_text, ("gaming", "گیم", "گیمنگ"))

def is_light(specs: dict, all_text: str, price: int) -> bool:
    return _has_any(all_text, ("light", "سبک", "ultrabook"))

def is_tablet_convertible(specs: dict, all_text: str, price: int) -> bool:
    return _has_any(all_text, ("tablet", "تبلت", "2-in-1", "convertible"))

def is_render_workstation(specs: dict, all_text: str, price: int) -> bool:
    return _has_any(all_text, ("render", "رندر", "workstation", "ایستگاه کاری"))

def is_touch(specs: dict, all_text: str, price: int) -> bool:
    return _is_yes(specs.get("touch_screen"))

def is_pen(specs: dict, all_text: str, price: int) -> bool:
    return _is_yes(specs.get("pen_support"))

def is_x360(specs: dict, all_text: str, price: int) -> bool:
    return _is_yes(specs.get("x360"))

def has_lte(specs: dict, all_text: str, price: int) -> bool:
    return _is_yes(specs.get("lte"))

def is_chromebook(specs: dict, all_text: str, price: int) -> bool:
    return "chromebook" in all_text or "کروم_بوک" in all_text

def is_student(specs: dict, all_text: str, price: int) -> bool:
    return _has_any(all_text, ("student", "دانشجو", "دانشجویی"))

def is_school(specs: dict, all_text: str, price: int) -> bool:
    return _has_any(all_text, ("school", "دانش_آموز", "دانش‌آموز", "دانش آموز"))

def is_seminary(specs: dict, all_text: str, price: int) -> bool:
    return _has_any(all_text, ("seminary", "طلبه", "طلبگی"))

def is_office(specs: dict, all_text: str, price: int) -> bool:
    return _has_any(all_text, ("office", "اداری", "business"))

def is_programming(specs: dict, all_text: str, price: int) -> bool:
    return _has_any(all_text, ("programming", "programmer", "برنامه نویسی", "برنامه‌نویسی", "کدنویسی", "developer"))

def is_design(specs: dict, all_text: str, price: int) -> bool:
    return _has_any(all_text, ("photoshop", "فتوشاپ", "illustrator", "ایلاستریتور", "graphic design", "طراحی"))

def is_editing(specs: dict, all_text: str, price: int) -> bool:
    return _has_any(all_text, ("editing", "تدوین", "premiere", "پریمیر", "video"))

def is_budget_laptop(specs: dict, all_text: str, price: int) -> bool:
    cpu = _text(specs.get("cpu") or specs.get("processor"))
    if price <= 30_000_000 and not has_discrete_gpu(specs, all_text, price):
        if _has_any(cpu, ("atom", "celeron", "pentium", "i3")):
            return True
    return False

# ==================================================
#  کلاس امتیازدهنده
# ==================================================

@dataclass
class Rule:
    tag: str
    weight: int = 1
    condition: Callable[[dict, str, int], bool] | None = None   # (specs, all_text, price)

class Scorer:
    def __init__(self, specs: dict, all_text: str, price: int):
        self.specs = specs
        self.all_text = all_text
        self.price = price
        self.scores: dict[str, int] = {}
        self.static_tags: list[str] = []

    def add_score(self, tag: str, points: int) -> None:
        if tag:
            self.scores[tag] = self.scores.get(tag, 0) + points

    def add_static(self, tag: str) -> None:
        if tag and tag not in self.static_tags:
            self.static_tags.append(tag)

    def apply_rules(self, rules: list[Rule]) -> None:
        for rule in rules:
            if rule.condition is None or rule.condition(self.specs, self.all_text, self.price):
                self.add_score(rule.tag, rule.weight)

    def get_top_tags(self, max_tags: int, priority_order: tuple[str, ...] = ()) -> list[str]:
        result = self.static_tags.copy()
        sorted_scores = sorted(self.scores.items(), key=lambda x: (-x[1], x[0]))
        for tag, _ in sorted_scores:
            if tag not in result:
                result.append(tag)
        if priority_order:
            ordered = []
            for ptag in priority_order:
                if ptag in result:
                    ordered.append(ptag)
                    result.remove(ptag)
            ordered.extend(result)
            result = ordered
        return result[:max_tags]

# ==================================================
#  قوانین لپ‌تاپ (با استفاده از توابع شرط اصلاح‌شده)
# ==================================================

LAPTOP_RULES = [
    Rule("#گرافیک", weight=8, condition=has_discrete_gpu),
    Rule("#گیمینگ", weight=10, condition=is_gaming),
    Rule("#رندرینگ", weight=10, condition=is_render_workstation),
    Rule("#رندر", weight=7, condition=is_render_workstation),
    Rule("#سبک", weight=6, condition=is_light),
    Rule("#تبلت_شو", weight=6, condition=is_tablet_convertible),
    Rule("#لمسی", weight=5, condition=is_touch),
    Rule("#چرخشی_لمسی", weight=5, condition=lambda s, t, p: is_touch(s, t, p) and is_x360(s, t, p)),
    Rule("#Pen", weight=3, condition=is_pen),
    Rule("#LTE", weight=3, condition=has_lte),
    Rule("#CHROMEBOOK", weight=5, condition=is_chromebook),
    Rule("#دانشجویی", weight=10, condition=is_student),
    Rule("#دانش_آموزی", weight=10, condition=is_school),
    Rule("#طلبگی", weight=10, condition=is_seminary),
    Rule("#اداری", weight=10, condition=is_office),
    Rule("#برنامه_نویسی", weight=10, condition=is_programming),
    Rule("#طراحی_فتوشاپ", weight=10, condition=is_design),
    Rule("#تدوین", weight=10, condition=is_editing),
    Rule("#کاربری_روزانه", weight=5, condition=is_budget_laptop),
    Rule("#وبگردی", weight=4, condition=is_budget_laptop),
]

# ==================================================
#  تابع اصلی تولید هشتگ (بدون قیمت)
# ==================================================

def generate_hashtags(
    product: Product,
    business_config: BusinessConfig | None = None,
    max_hashtags: int = 9,
) -> list[str]:
    specs = getattr(product, "specs", None) or {}
    subcategory_key = getattr(product, "sub_category_key", None) or ""
    if business_config and not subcategory_key and business_config.sub_categories:
        subcategory_key = business_config.sub_categories[0].key

    # ساخت all_text از نام محصول و تمام مقدارهای specs
    all_text_parts = []
    if hasattr(product, "product_name"):
        all_text_parts.append(_text(product.product_name))
    for v in specs.values():
        all_text_parts.append(_text(v))
    all_text = " ".join(all_text_parts).lower()

    price = _get_price(product)
    scorer = Scorer(specs, all_text, price)

    # هشتک‌های ثابت از زیردسته
    if business_config and subcategory_key:
        subcategory = get_subcategory(business_config.key, subcategory_key)
        if subcategory:
            for tag in subcategory.static_hashtags:
                scorer.add_static(tag)

    # هشتک‌های دسته‌بندی اصلی (حداقل یکی)
    category_tags = {
        "laptop": ("#لپتاپ",),
        "prebuilt_pc": ("#کیس_آماده", "#کامپیوتر"),
        "monitor": ("#مانیتور",),
        "component": ("#قطعات_کامپیوتر",),
        "accessory": ("#لوازم_جانبی",),
    }
    for tag in category_tags.get(subcategory_key, ()):
        scorer.add_static(tag)

    # هشتک برند
    brand_value = specs.get("brand")
    if brand_value:
        brand = _text(brand_value)
        if brand in BRAND_TAGS:
            scorer.add_static(BRAND_TAGS[brand])
        else:
            clean = re.sub(r"[^\w]+", "_", brand).strip("_")
            if clean:
                scorer.add_static(f"#{clean}")

    # اعمال قوانین مخصوص لپ‌تاپ (در آینده برای سایر زیردسته‌ها می‌توان توسعه داد)
    rules = []
    if subcategory_key == "laptop":
        rules = LAPTOP_RULES
    scorer.apply_rules(rules)

    # اولویت‌بندی هشتگ‌های کاربردی (حداقل دو مورد باید در خروجی باشند)
    priority_order = (
        "#دانشجویی", "#طلبگی", "#دانش_آموزی", "#برنامه_نویسی",
        "#طراحی_فتوشاپ", "#حسابداری", "#رندرینگ", "#رندر",
        "#گیمینگ", "#اداری", "#کاربری_روزانه", "#وبگردی", "#تدوین",
        "#سبک", "#لمسی", "#چرخشی_لمسی", "#گرافیک"
    )

    tags = scorer.get_top_tags(max_hashtags, priority_order)

    # اطمینان از وجود حداقل دو هشتگ کاربردی
    usage_tags = [t for t in tags if t in priority_order]
    if len(usage_tags) < 2:
        # هشتگ‌های پیش‌فرض را در صورت وجود فضا اضافه کن
        fallbacks = ["#کاربری_روزانه", "#وبگردی"]
        for fb in fallbacks:
            if fb not in tags and len(tags) < max_hashtags:
                tags.append(fb)
            if len([t for t in tags if t in priority_order]) >= 2:
                break

    # اضافه کردن نسل پردازنده و مدل CPU (در صورت وجود)
    cpu = _text(specs.get("cpu") or specs.get("processor"))
    for gen in range(1, 15):
        if f"نسل{gen}" in all_text or re.search(rf"\b{gen}(?:th|st|nd|rd)\b", all_text):
            if f"#نسل{gen}" not in tags:
                tags.append(f"#نسل{gen}")
            break
    for cpu_tag in ("i3", "i5", "i7", "i9", "xeon"):
        if re.search(rf"\b{cpu_tag}\b", cpu):
            if f"#{cpu_tag}" not in tags:
                tags.append(f"#{cpu_tag}")
    if "amd" in cpu and "#AMD" not in tags:
        tags.append("#AMD")
    if "ryzen" in cpu and "#Ryzen" not in tags:
        tags.append("#Ryzen")

    return tags[:max_hashtags]

# ==================================================
#  توابع مربوط به هشتگ قیمت (جدا از بقیه)
# ==================================================

def generate_price_range_hashtag(product: Product) -> str:
    price = _get_price(product)
    if price <= 0:
        return ""
    for min_, max_, label in PRICE_RANGES:
        if min_ <= price < max_:
            return f"#{label}"
    return ""

def format_hashtags_for_post(hashtags: list[str]) -> str:
    return " ".join(hashtags) if hashtags else ""