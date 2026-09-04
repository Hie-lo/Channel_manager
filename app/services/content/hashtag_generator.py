# ===============================
# بخش جدید: سیستم امتیازدهی ماژولار
# ===============================

from typing import Callable
from dataclasses import dataclass
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

# ===============================
# کلاس‌های کمکی برای امتیازدهی
# ===============================

@dataclass
class HashtagRule:
    tag: str
    weight: int = 1
    condition: Callable[..., bool] | None = None
    # اگر condition None باشد، همیشه اعمال می‌شود

class HashtagScorer:
    def __init__(self, product: Product, subcategory_key: str, specs: dict):
        self.product = product
        self.subcategory_key = subcategory_key
        self.specs = specs
        self.price = self._get_price()
        self.all_text = self._build_all_text()
        self.scores: dict[str, int] = {}
        self.static_tags: list[str] = []

    def _get_price(self) -> int:
        try:
            p = getattr(self.product, 'price', 0) or 0
            return int(float(p))
        except (TypeError, ValueError):
            return 0

    def _build_all_text(self) -> str:
        parts = []
        if hasattr(self.product, 'product_name'):
            parts.append(str(self.product.product_name or ''))
        for v in self.specs.values():
            parts.append(str(v or ''))
        return " ".join(parts).lower()

    def _text(self, value) -> str:
        return str(value or "").strip().lower()

    def _has_any(self, values: tuple[str, ...]) -> bool:
        return any(v in self.all_text for v in values)

    def _is_yes(self, key: str) -> bool:
        v = self._text(self.specs.get(key, ''))
        return v in {"yes", "true", "1", "بله", "دارد", "داره"}

    def add_score(self, tag: str, points: int) -> None:
        if tag:
            self.scores[tag] = self.scores.get(tag, 0) + points

    def add_static(self, tag: str) -> None:
        if tag and tag not in self.static_tags:
            self.static_tags.append(tag)

    def apply_rules(self, rules: list[HashtagRule]) -> None:
        for rule in rules:
            if rule.condition is None:
                self.add_score(rule.tag, rule.weight)
            else:
                if rule.condition(self.product, self.specs, self.all_text, self.price):
                    self.add_score(rule.tag, rule.weight)

    def get_top_tags(self, max_tags: int, priority_order: tuple[str, ...] = ()) -> list[str]:
        result = self.static_tags.copy()

        # مرتب‌سازی هشتک‌های امتیازدار
        sorted_tags = sorted(self.scores.items(), key=lambda x: (-x[1], x[0]))
        for tag, _ in sorted_tags:
            if tag not in result:
                result.append(tag)

        # اعمال اولویت
        if priority_order:
            ordered = []
            for ptag in priority_order:
                if ptag in result:
                    ordered.append(ptag)
                    result.remove(ptag)
            ordered.extend(result)
            result = ordered

        return result[:max_tags]

# ===============================
# تعریف توابع شرطی (Conditions)
# ===============================

def has_discrete_gpu(product, specs, all_text, price):
    gpu = str(specs.get('gpu') or specs.get('graphics') or '').lower()
    if not gpu:
        return False
    if any(x in gpu for x in ('integrated', 'onboard', 'آن برد', 'ندارد', 'without', 'intel hd')):
        return False
    return True

def is_gaming(product, specs, all_text, price):
    return any(x in all_text for x in ('gaming', 'گیم', 'گیمنگ'))

def is_accounting(product, specs, all_text, price):
    return any(x in all_text for x in ('accounting', 'حسابداری'))

def is_light(product, specs, all_text, price):
    return any(x in all_text for x in ('light', 'سبک', 'ultrabook'))

def is_tablet_convertible(product, specs, all_text, price):
    return any(x in all_text for x in ('tablet', 'تبلت', '2-in-1', 'convertible'))

def is_render(product, specs, all_text, price):
    return any(x in all_text for x in ('render', 'رندر', 'workstation'))

def is_touch(product, specs, all_text, price):
    return str(specs.get('touch_screen', '')).lower() in ('yes', 'true', '1', 'بله', 'دارد', 'داره')

def is_pen(product, specs, all_text, price):
    return str(specs.get('pen_support', '')).lower() in ('yes', 'true', '1', 'بله', 'دارد', 'داره')

def is_x360(product, specs, all_text, price):
    return str(specs.get('x360', '')).lower() in ('yes', 'true', '1', 'بله', 'دارد', 'داره')

def has_lte(product, specs, all_text, price):
    return str(specs.get('lte', '')).lower() in ('yes', 'true', '1', 'بله', 'دارد', 'داره')

def is_chromebook(product, specs, all_text, price):
    return 'chromebook' in all_text or 'کروم_بوک' in all_text

def is_student(product, specs, all_text, price):
    return any(x in all_text for x in ('student', 'دانشجو', 'دانشجویی'))

def is_school(product, specs, all_text, price):
    return any(x in all_text for x in ('school', 'دانش_آموز', 'دانش‌آموز', 'دانش آموز'))

def is_seminary(product, specs, all_text, price):
    return any(x in all_text for x in ('seminary', 'طلبه', 'طلبگی'))

def is_office(product, specs, all_text, price):
    return any(x in all_text for x in ('office', 'اداری', 'business'))

def is_programming(product, specs, all_text, price):
    return any(x in all_text for x in ('programming', 'programmer', 'برنامه نویسی', 'برنامه‌نویسی', 'کدنویسی', 'developer'))

def is_design(product, specs, all_text, price):
    return any(x in all_text for x in ('photoshop', 'فتوشاپ', 'illustrator', 'ایلاستریتور', 'graphic design', 'طراحی'))

def is_editing(product, specs, all_text, price):
    return any(x in all_text for x in ('editing', 'تدوین', 'premiere', 'پریمیر', 'video'))

# ===============================
# قوانین (Rules) برای زیردسته‌ها
# ===============================

def rule(tag: str, weight: int = 1, condition=None):
    return HashtagRule(tag, weight, condition)

LAPTOP_RULES = [
    rule("#گرافیک", weight=5, condition=has_discrete_gpu),
    rule("#گیمینگ", weight=10, condition=is_gaming),
    rule("#حسابداری", weight=10, condition=is_accounting),
    rule("#سبک", weight=5, condition=is_light),
    rule("#تبلت_شو", weight=5, condition=is_tablet_convertible),
    rule("#رندرینگ", weight=10, condition=is_render),
    rule("#رندر", weight=8, condition=is_render),
    rule("#لمسی", weight=5, condition=is_touch),
    rule("#چرخشی_لمسی", weight=5, condition=lambda p,s,t,pr: is_touch(p,s,t,pr) and is_x360(p,s,t,pr)),
    rule("#Pen", weight=3, condition=is_pen),
    rule("#LTE", weight=3, condition=has_lte),
    rule("#CHROMEBOOK", weight=5, condition=is_chromebook),
    rule("#دانشجویی", weight=10, condition=is_student),
    rule("#دانش_آموزی", weight=10, condition=is_school),
    rule("#طلبگی", weight=10, condition=is_seminary),
    rule("#اداری", weight=10, condition=is_office),
    rule("#برنامه_نویسی", weight=10, condition=is_programming),
    rule("#طراحی_فتوشاپ", weight=10, condition=is_design),
    rule("#تدوین", weight=10, condition=is_editing),
]

COMMON_RULES = []  # می‌توان قوانین عمومی اضافه کرد

# ===============================
# توابع اصلی (بازنویسی‌شده)
# ===============================

def generate_hashtags(
    product: Product,
    business_config: BusinessConfig | None = None,
    max_hashtags: int = 9,
) -> list[str]:
    specs = getattr(product, "specs", None) or {}
    subcategory_key = getattr(product, "sub_category_key", None) or ""
    if business_config and not subcategory_key and business_config.sub_categories:
        subcategory_key = business_config.sub_categories[0].key

    scorer = HashtagScorer(product, subcategory_key, specs)

    # هشتک‌های ثابت از زیردسته
    if business_config and subcategory_key:
        subcategory = get_subcategory(business_config.key, subcategory_key)
        if subcategory:
            for tag in subcategory.static_hashtags:
                scorer.add_static(tag)

    # هشتک‌های دسته‌بندی
    category_tags = {
        "laptop": ("#لپتاپ",),
        "prebuilt_pc": ("#کیس_آماده", "#کامپیوتر"),
        "monitor": ("#مانیتور",),
        "component": ("#قطعات_کامپیوتر",),
        "accessory": ("#لوازم_جانبی",),
    }
    for tag in category_tags.get(subcategory_key, ()):
        scorer.add_static(tag)

    # برند
    brand = specs.get("brand")
    if brand:
        brand_text = str(brand).strip().lower()
        brand_hashtag = BRAND_TAGS.get(brand_text)
        if brand_hashtag:
            scorer.add_static(brand_hashtag)
        else:
            clean = re.sub(r"[^\w]+", "_", brand_text).strip("_")
            if clean:
                scorer.add_static(f"#{clean}")

    # هشتگ قیمت
    price_tag = generate_price_range_hashtag(product)
    if price_tag:
        scorer.add_static(price_tag)

    # انتخاب قوانین بر اساس زیردسته
    rules = []
    if subcategory_key == "laptop":
        rules = LAPTOP_RULES
    # می‌توان برای prebuilt_pc، monitor و ... قوانین جداگانه تعریف کرد
    rules.extend(COMMON_RULES)
    scorer.apply_rules(rules)

    # اولویت‌بندی نهایی
    priority_order = (
        "#دانشجویی", "#طلبگی", "#دانش_آموزی", "#برنامه_نویسی",
        "#طراحی_فتوشاپ", "#حسابداری", "#رندرینگ", "#رندر",
        "#گیمینگ", "#اداری", "#کاربری_روزانه", "#وبگردی", "#تدوین",
        "#سبک", "#لمسی", "#چرخشی_لمسی", "#گرافیک"
    )
    tags = scorer.get_top_tags(max_hashtags, priority_order)

    # اضافه کردن نسل و مدل CPU (اگر وجود داشته باشد)
    cpu = str(specs.get('cpu') or specs.get('processor') or '').lower()
    all_text = scorer.all_text
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


def generate_price_range_hashtag(product: Product) -> str:
    try:
        price = int(float(getattr(product, "price", 0) or 0))
    except (TypeError, ValueError):
        return ""
    if price <= 0:
        return ""
    for minimum, maximum, label in PRICE_RANGES:
        if minimum <= price < maximum:
            return f"#{label}"
    return ""


def format_hashtags_for_post(hashtags: list[str]) -> str:
    return " ".join(hashtags) if hashtags else ""