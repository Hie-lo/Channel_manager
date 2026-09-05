"""
ساخت پرامپت‌های بهینه برای AI
هر کسب‌وکار فرمت خروجی خاص خودش را دارد
"""

from app.database.models import Product
from app.business.config import BusinessConfig, get_subcategory


# ═══════════════════════════════════════════════════════════════
# System Prompts - یک system prompt برای هر نوع کسب‌وکار
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT_COMPUTER_SHOP = """تو نویسنده پست فروش محصولات کامپیوتری هستی. متن خودمانی، صادقانه و قانع‌کننده بنویس.

قوانین:
- خروجی فقط در فرمت خواسته شده
- هیچ متن اضافه یا توضیح ننویس
- از ایموجی استفاده نکن (کد اضافه می‌کنه)"""

SYSTEM_PROMPT_GENERIC = """تو نویسنده پست فروش محصولات هستی. متن صادقانه و جذاب بنویس.

قوانین:
- خروجی فقط در فرمت خواسته شده
- هیچ متن اضافه ننویس
- از ایموجی استفاده نکن"""


def get_system_prompt(business_key: str) -> str:
    """انتخاب system prompt بر اساس نوع کسب‌وکار"""
    if business_key in ["computer_shop", "laptop_store"]:
        return SYSTEM_PROMPT_COMPUTER_SHOP
    else:
        return SYSTEM_PROMPT_GENERIC


# ═══════════════════════════════════════════════════════════════
# Generation Prompts - فرمت خروجی برای هر کسب‌وکار
# ═══════════════════════════════════════════════════════════════

def build_generation_prompt(
    product: Product,
    business_config: BusinessConfig,
) -> str:
    """ساخت پرامپت برای تولید توضیحات جدید"""
    business_key = business_config.key
    
    if business_key in ["computer_shop", "laptop_store"]:
        return _build_computer_prompt(product, business_config)
    else:
        return _build_generic_prompt(product, business_config)


def _build_computer_prompt(
    product: Product,
    business_config: BusinessConfig,
) -> str:
    """پرامپت ویژه برای کسب‌وکارهای کامپیوتری"""
    specs_str = _build_specs_string(product)

    prompt = f"""محصول: {product.product_name}
مشخصات: {specs_str}

قوانین خروجی:
D: یک جمله کوتاه و جذاب درباره محصول (مثل: لپ‌تاپ زیبا از برند محبوب ایسوس، سبک و خوش‌دست)
F1 تا F6: ۳ تا ۶ نقطه قوت خودمانی و قانع‌کننده؛ مشخصات خام را تکرار نکن، بگو این ویژگی چه فایده‌ای برای خریدار دارد؛ از کلمات مثل "خیلی خیلی"، "بسیار عالی"، "فوق‌العاده" استفاده کن (مثل: دارای SSD ۲۵۶ گیگ فوق‌العاده سریع، بسیار سبک مناسب حمل زیاد، یه گزینه اقتصادی برای کارهای سبک)
G: فقط نام ۳ بازی برتر روز متناسب با سخت‌افزار (بدون توضیح)
SW: فقط نام ۶-۷ برنامه کاربردی روز (حتماً Adobe شامل شود) متناسب با سخت‌افزار (بدون توضیح)
N1, N2: دو محدودیت واقعی کوتاه

خروجی:
D: [یک جمله جذاب]
F1: [مزیت اول]
F2: [مزیت دوم]
F3: [مزیت سوم]
F4: [مزیت چهارم]
F5: [مزیت پنجم]
F6: [مزیت ششم]
G: [نام ۳ بازی]
SW: [نام ۶-۷ برنامه]
N1: [محدودیت اول]
N2: [محدودیت دوم]"""

    return prompt


def _build_generic_prompt(
    product: Product,
    business_config: BusinessConfig,
) -> str:
    """پرامپت عمومی برای سایر کسب‌وکارها (5 ویژگی)"""
    subcategory = get_subcategory(business_config.key, product.sub_category_key)
    subcategory_name = subcategory.name_fa if subcategory else "محصول"

    specs_str = _build_specs_string(product)

    prompt = f"""محصول: {product.product_name}
دسته: {subcategory_name}
مشخصات: {specs_str}

وظیفه: توضیحات کامل و جذاب این محصول رو بنویس.

قوانین دقیق:
1. D: توضیح جامع و جذاب محصول (۲ تا ۳ جمله، ۲۵ تا ۴۰ کلمه)
2. P1 تا P5: پنج مزیت واقعی محصول (هر کدام ۳ تا ۶ کلمه)
3. N1, N2: دو محدودیت یا کاستی واقعی (هر کدام ۳ تا ۶ کلمه)

خروجی دقیقاً به این فرمت:
D: [توضیح جامع]
P1: [مزیت اول]
P2: [مزیت دوم]
P3: [مزیت سوم]
P4: [مزیت چهارم]
P5: [مزیت پنجم]
N1: [محدودیت اول]
N2: [محدودیت دوم]"""

    return prompt


# ═══════════════════════════════════════════════════════════════
# Improve Prompts
# ═══════════════════════════════════════════════════════════════

def build_improve_prompt(
    product: Product,
    business_config: BusinessConfig,
    existing_description: str,
) -> str:
    """ساخت پرامپت برای بهبود متن موجود"""
    business_key = business_config.key
    
    if business_key in ["computer_shop", "laptop_store"]:
        return _build_computer_improve_prompt(product, business_config, existing_description)
    else:
        return _build_generic_improve_prompt(product, business_config, existing_description)


def _build_computer_improve_prompt(
    product: Product,
    business_config: BusinessConfig,
    existing_description: str,
) -> str:
    """بهبود متن برای کسب‌وکارهای کامپیوتری"""
    specs_str = _build_specs_string(product)

    prompt = f"""محصول: {product.product_name}
مشخصات: {specs_str}
متن فروشنده: {existing_description}

قوانین خروجی:
D: بازنویسی متن فروشنده به یک جمله کوتاه و جذاب
F1 تا F6: ۳ تا ۶ نقطه قوت خودمانی؛ مشخصات خام تکرار نکن، فایده واقعی برای خریدار بگو؛ از کلمات مثل "خیلی خیلی"، "بسیار عالی"، "فوق‌العاده" استفاده کن
G: فقط نام ۳ بازی برتر روز متناسب با سخت‌افزار
SW: فقط نام ۶-۷ برنامه کاربردی روز (حتماً Adobe شامل شود) متناسب با سخت‌افزار
N1, N2: دو محدودیت واقعی کوتاه

خروجی:
D: [یک جمله جذاب]
F1: [مزیت اول]
F2: [مزیت دوم]
F3: [مزیت سوم]
F4: [مزیت چهارم]
F5: [مزیت پنجم]
F6: [مزیت ششم]
G: [نام ۳ بازی]
SW: [نام ۶-۷ برنامه]
N1: [محدودیت اول]
N2: [محدودیت دوم]"""

    return prompt


def _build_generic_improve_prompt(
    product: Product,
    business_config: BusinessConfig,
    existing_description: str,
) -> str:
    """بهبود متن برای کسب‌وکارهای عمومی"""
    subcategory = get_subcategory(business_config.key, product.sub_category_key)
    subcategory_name = subcategory.name_fa if subcategory else "محصول"

    specs_str = _build_specs_string(product)

    prompt = f"""محصول: {product.product_name}
دسته: {subcategory_name}
مشخصات: {specs_str}
متن اولیه فروشنده: {existing_description}

وظیفه: متن فروشنده رو بهبود بده و مزایا و محدودیت‌های واقعی اضافه کن.

قوانین دقیق:
1. D: بازنویسی جامع‌تر متن فروشنده (۲ تا ۳ جمله)
2. P1 تا P5: پنج مزیت واقعی (هر کدام ۳ تا ۶ کلمه)
3. N1, N2: دو محدودیت واقعی (هر کدام ۳ تا ۶ کلمه)

خروجی دقیقاً به این فرمت:
D: [توضیح جامع]
P1: [مزیت اول]
P2: [مزیت دوم]
P3: [مزیت سوم]
P4: [مزیت چهارم]
P5: [مزیت پنجم]
N1: [محدودیت اول]
N2: [محدودیت دوم]"""

    return prompt


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _build_specs_string(product: Product) -> str:
    """تبدیل specs به رشته کوتاه"""
    if not product.specs:
        return ""

    parts = []
    priority_keys = ["brand", "cpu", "ram", "storage", "gpu", "screen",
                     "resolution", "component_type", "accessory_type"]

    for key in priority_keys:
        if key in product.specs:
            value = product.specs[key]
            if value:
                parts.append(f"{key}={value}")

    for key, value in product.specs.items():
        if key not in priority_keys and value:
            parts.append(f"{key}={value}")

    return "؛ ".join(parts)
