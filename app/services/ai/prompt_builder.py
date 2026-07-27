"""
ساخت پرامپت‌های بهینه برای AI
"""

from app.database.models import Product
from app.business.config import BusinessConfig, get_subcategory


SYSTEM_PROMPT = """تو یک کپی‌رایتر حرفه‌ای برای پست‌های فروشگاهی تلگرام هستی.
وظیفه‌ات: نوشتن توضیحات صادقانه، متعادل و جذاب برای محصولات.

قوانین سختگیرانه:
- خروجی فقط در فرمت خواسته شده باشد
- هیچ متن اضافه، مقدمه، توضیح یا پرانتز اضافی ننویس
- در بخش مزایا فقط نقاط قوت واقعی
- در بخش محدودیت‌ها فقط نکات منفی یا کاستی‌های واقعی
- هرگز محدودیت‌های مثبت ننویس (مثل 'طراحی زیبا' اشتباه است)
- از ایموجی در ابتدای خطوط استفاده نکن (کد خودمون اضافه می‌کنه)"""


def build_generation_prompt(
    product: Product,
    business_config: BusinessConfig,
) -> str:
    """ساخت پرامپت برای تولید توضیحات جدید"""
    subcategory = get_subcategory(business_config.key, product.sub_category_key)
    subcategory_name = subcategory.name_fa if subcategory else "محصول"

    specs_str = _build_specs_string(product)

    prompt = f"""محصول: {product.product_name}
دسته: {subcategory_name}
مشخصات: {specs_str}

وظیفه: توضیحات کامل و جذاب این محصول رو بنویس.

قوانین دقیق:
1. D: توضیح جامع و جذاب محصول (۲ تا ۳ جمله، ۲۵ تا ۴۰ کلمه)
   - کاربرد اصلی محصول
   - برای چه کسانی مناسبه
   - ویژگی برجسته
2. P1 تا P5: پنج مزیت واقعی محصول (نقاط قوت - هر کدام ۳ تا ۶ کلمه)
3. N1, N2: دو محدودیت یا کاستی واقعی این نوع محصول (نقاط ضعف - هر کدام ۳ تا ۶ کلمه)

مثال درست برای D:
"لپتاپی قدرتمند برای گیمرها و طراحان حرفه‌ای که ترکیبی از عملکرد بالا و طراحی شیک ارائه می‌ده. مناسب کارهای سنگین مثل رندرینگ و بازی‌های AAA."

مثال درست برای P (مزایا):
- "پردازنده نسل ۱۲ اینتل با قدرت بالا"
- "نمایشگر 2.5K با رنگ‌های دقیق"
- "کیبورد بک‌لایت با کیفیت لمس عالی"

مثال درست برای N (محدودیت):
- "باتری متوسط زیر بار سنگین"
- "وزن نسبتاً بالا برای حمل روزانه"
- "فن پرصدا در بازی‌های سنگین"
- "قیمت بالا برای کاربر معمولی"
- "نبود درگاه Thunderbolt 4"

مثال اشتباه برای N (اینا مزیتن نه محدودیت):
- "طراحی زیبا" ❌
- "سرعت بالا" ❌
- "کیفیت ساخت عالی" ❌

خروجی دقیقاً به این فرمت (فقط این خطوط، بدون ایموجی، بدون توضیح):
D: [توضیح جامع ۲-۳ جمله‌ای]
P1: [مزیت اول]
P2: [مزیت دوم]
P3: [مزیت سوم]
P4: [مزیت چهارم]
P5: [مزیت پنجم]
N1: [محدودیت اول]
N2: [محدودیت دوم]"""

    return prompt


def build_improve_prompt(
    product: Product,
    business_config: BusinessConfig,
    existing_description: str,
) -> str:
    """ساخت پرامپت برای بهبود متن موجود"""
    subcategory = get_subcategory(business_config.key, product.sub_category_key)
    subcategory_name = subcategory.name_fa if subcategory else "محصول"

    specs_str = _build_specs_string(product)

    prompt = f"""محصول: {product.product_name}
دسته: {subcategory_name}
مشخصات: {specs_str}
متن اولیه فروشنده: {existing_description}

وظیفه: متن فروشنده رو بهبود بده، جامع‌تر کن و مزایا و محدودیت‌های واقعی محصول رو اضافه کن.

قوانین دقیق:
1. D: بازنویسی جامع‌تر متن فروشنده (۲ تا ۳ جمله، ۲۵ تا ۴۰ کلمه)
   - معنی اصلی حفظ شود
   - جذاب‌تر و کامل‌تر
2. P1 تا P5: پنج مزیت واقعی بر اساس مشخصات (هر کدام ۳ تا ۶ کلمه)
3. N1, N2: دو محدودیت یا کاستی واقعی (هر کدام ۳ تا ۶ کلمه)

مثال درست برای N (محدودیت):
- "باتری متوسط زیر بار سنگین"
- "وزن نسبتاً سنگین"
- "قیمت بالا برای کاربر معمولی"

مثال اشتباه برای N:
- "طراحی زیبا" ❌ (این مزیته)
- "سرعت بالا" ❌ (این مزیته)

خروجی دقیقاً به این فرمت (بدون ایموجی، بدون توضیح):
D: [توضیح جامع ۲-۳ جمله‌ای]
P1: [مزیت اول]
P2: [مزیت دوم]
P3: [مزیت سوم]
P4: [مزیت چهارم]
P5: [مزیت پنجم]
N1: [محدودیت اول]
N2: [محدودیت دوم]"""

    return prompt


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