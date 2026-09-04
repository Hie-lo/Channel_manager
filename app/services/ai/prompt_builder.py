"""
ساخت پرامپت‌های بهینه برای AI
هر کسب‌وکار فرمت خروجی خاص خودش را دارد
"""

from app.database.models import Product
from app.business.config import BusinessConfig, get_subcategory


# ═══════════════════════════════════════════════════════════════
# System Prompts - یک system prompt برای هر نوع کسب‌وکار
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT_COMPUTER_SHOP = """تو یک کپی‌رایتر حرفه‌ای برای پست‌های فروشگاهی محصولات کامپیوتری هستی.
وظیفه‌ات: نوشتن توضیحات صادقانه، متعادل و جذاب برای لپتاپ‌ها، قطعات کامپیوتر، و لوازم جانبی.

قوانین سختگیرانه:
- خروجی فقط در فرمت خواسته شده باشد
- هیچ متن اضافه، مقدمه، توضیح یا پرانتز اضافی ننویس
- در بخش ویژگی‌ها فقط نقاط قوت و مشخصات برجسته
- در بخش محدودیت‌ها فقط نکات منفی یا کاستی‌های واقعی
- هرگز محدودیت‌های مثبت ننویس (مثل 'طراحی زیبا' اشتباه است)
- از ایموجی در ابتدای خطوط استفاده نکن (کد خودمون اضافه می‌کنه)"""

SYSTEM_PROMPT_GENERIC = """تو یک کپی‌رایتر حرفه‌ای برای پست‌های فروشگاهی تلگرام هستی.
وظیفه‌ات: نوشتن توضیحات صادقانه، متعادل و جذاب برای محصولات.

قوانین سختگیرانه:
- خروجی فقط در فرمت خواسته شده باشد
- هیچ متن اضافه، مقدمه، توضیح یا پرانتز اضافی ننویس
- در بخش مزایا فقط نقاط قوت واقعی
- در بخش محدودیت‌ها فقط نکات منفی یا کاستی‌های واقعی
- از ایموجی در ابتدای خطوط استفاده نکن"""


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
    """پرامپت ویژه برای کسب‌وکارهای کامپیوتری (10-12 ویژگی)"""
    subcategory = get_subcategory(business_config.key, product.sub_category_key)
    subcategory_name = subcategory.name_fa if subcategory else "محصول"

    specs_str = _build_specs_string(product)

    prompt = f"""محصول: {product.product_name}
دسته: {subcategory_name}
مشخصات: {specs_str}

وظیفه: توضیحات کامل و جذاب این محصول رو بنویس با تمرکز روی ویژگی‌های فنی.

قانون داده: گزینه‌های Yes شیت را قابلیت واقعی در نظر بگیر؛ گزینه‌های No یا خالی را هرگز به‌عنوان قابلیت محصول ذکر نکن.

قوانین دقیق:
1. D: توضیح جامع و جذاب محصول (۲ تا ۳ جمله، ۲۵ تا ۴۰ کلمه)
   - کاربرد اصلی محصول
   - برای چه کسانی مناسبه
   - ویژگی برجسته

2. C: فقط عبارت فنی داخل پرانتز CPU را تولید کن، بدون جمله و توضیح اضافی، دقیقاً با این ساختار: 3MB Cache | 3.2 GHz | 8 Cores | Gen4. اگر داده‌ای در مشخصات نیست، آن بخش را نساز.
3. U1 تا U5: کاربردهای واقعی مانند دانشجویی، اداری، حسابداری، وبگردی یا برنامه‌نویسی
4. G: نام ۳ تا ۶ بازی مشخص و شناخته‌شده که با CPU/GPU/RAM این محصول منطقی است؛ سطح تقریبی اجرا را هم کوتاه بنویس. فقط نام بازی واقعی بنویس، نه عبارت کلی مثل «بازی‌های سبک». اگر سخت‌افزار برای بازی مناسب نیست، نام بازی‌های سبک واقعی مثل CS 1.6، League of Legends یا Minecraft را با توضیح محدودیت بیاور و هرگز بازی سنگین را ادعا نکن.
5. SW: نرم‌افزارهای مناسب یا محدودیت واقعی اجرای آن‌ها
   
6. F1 تا F12: ده تا دوازده ویژگی خاص و برجسته محصول (هر کدام ۴ تا ۸ کلمه)
   - مشخصات فنی مهم
   - قابلیت‌های کلیدی
   - نقاط قوت سخت‌افزاری
   - ویژگی‌های منحصربه‌فرد
   
7. N1, N2: دو محدودیت یا کاستی واقعی این نوع محصول (هر کدام ۳ تا ۶ کلمه)

مثال درست برای D:
"لپتاپی قدرتمند برای گیمرها و طراحان حرفه‌ای که ترکیبی از عملکرد بالا و طراحی شیک ارائه می‌ده. مناسب کارهای سنگین مثل رندرینگ و بازی‌های AAA."

مثال درست برای F (ویژگی‌ها):
- "لپ‌تاپ حرفه‌ای و صنعتی از سری EliteBook"
- "نمایشگر ۱۴ اینچی مناسب کاربری روزمره و اداری"
- "گرافیک مجتمع Intel HD Graphics 5500"
- "عملکرد گرافیکی در محدوده GeForce 820M"
- "رم ۸GB مناسب کاربری روزمره و اداری"
- "حافظه پرسرعت ۲۵۶GB SSD"
- "بدنه و شاسی مقاوم و باکیفیت"
- "کیبورد باکیفیت مناسب استفاده طولانی"
- "مناسب امور اداری، حسابداری و تحصیلی"
- "وزن سبک و قابل حمل برای کار روزانه"

مثال درست برای N (محدودیت):
- "باتری متوسط زیر بار سنگین"
- "گرافیک مجتمع برای بازی‌های سنگین محدود"
- "قیمت بالا نسبت به مدل‌های مشابه"

خروجی دقیقاً به این فرمت (فقط این خطوط، بدون ایموجی، بدون توضیح):
D: [توضیح جامع ۲-۳ جمله‌ای]
C: [توضیح CPU برای کاربر]
U1: [کاربرد اول]
U2: [کاربرد دوم]
U3: [کاربرد سوم]
G: [بازی‌های مناسب یا محدودیت بازی]
SW: [نرم‌افزارهای مناسب]
F1: [ویژگی اول]
F2: [ویژگی دوم]
F3: [ویژگی سوم]
F4: [ویژگی چهارم]
F5: [ویژگی پنجم]
F6: [ویژگی ششم]
F7: [ویژگی هفتم]
F8: [ویژگی هشتم]
F9: [ویژگی نهم]
F10: [ویژگی دهم]
F11: [ویژگی یازدهم]
F12: [ویژگی دوازدهم]
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
    subcategory = get_subcategory(business_config.key, product.sub_category_key)
    subcategory_name = subcategory.name_fa if subcategory else "محصول"

    specs_str = _build_specs_string(product)

    prompt = f"""محصول: {product.product_name}
دسته: {subcategory_name}
مشخصات: {specs_str}
متن اولیه فروشنده: {existing_description}

وظیفه: متن فروشنده رو بهبود بده و اطلاعات کاربردی CPU، کاربردها، بازی و نرم‌افزار را نیز اضافه کن.

قانون داده: گزینه‌های Yes شیت را قابلیت واقعی در نظر بگیر؛ گزینه‌های No یا خالی را هرگز به‌عنوان قابلیت محصول ذکر نکن.

قوانین دقیق:
1. D: بازنویسی جامع‌تر متن فروشنده (۲ تا ۳ جمله)
2. C: توضیح کوتاه CPU برای کاربر
3. U1 تا U5: کاربردهای واقعی محصول
4. G: بازی‌های منطقی قابل اجرا یا محدودیت بازی
5. SW: نرم‌افزارهای مناسب یا محدودیت واقعی
6. F1 تا F12: ده تا دوازده ویژگی خاص بر اساس مشخصات (هر کدام ۴ تا ۸ کلمه)
7. N1, N2: دو محدودیت واقعی (هر کدام ۳ تا ۶ کلمه)

خروجی دقیقاً به این فرمت:
D: [توضیح جامع]
C: [توضیح CPU برای کاربر]
U1: [کاربرد اول]
U2: [کاربرد دوم]
U3: [کاربرد سوم]
G: [بازی‌های مناسب یا محدودیت بازی]
SW: [نرم‌افزارهای مناسب]
F1: [ویژگی اول]
F2: [ویژگی دوم]
...
F12: [ویژگی دوازدهم]
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
