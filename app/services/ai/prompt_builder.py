"""
ساخت پرامپت‌های بهینه برای AI
هر کسب‌وکار فرمت خروجی خاص خودش را دارد
"""

from app.database.models import Product
from app.business.config import BusinessConfig, get_subcategory


# ═══════════════════════════════════════════════════════════════
# System Prompts - یک system prompt برای هر نوع کسب‌وکار
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT_COMPUTER_SHOP = """تو یک نویسنده صمیمی برای پست فروش محصولات کامپیوتری هستی.
متن را خودمانی، روان، کوتاه و قابل‌فهم برای مشتری بنویس؛ خشک و اداری ننویس.

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

وظیفه: یک متن کوتاه و جذاب برای فروش این محصول بنویس.

قانون داده: گزینه‌های Yes شیت را قابلیت واقعی در نظر بگیر؛ گزینه‌های No یا خالی را هرگز به‌عنوان قابلیت محصول ذکر نکن.

قوانین دقیق:
1. D: توضیح جامع و جذاب محصول (1 تا 2 جمله، 10 تا 15 کلمه)
   - کاربرد اصلی محصول
   - برای چه کسانی مناسبه
   - ویژگی برجسته

2. U1 تا U5: کاربردهای واقعی مانند دانشجویی، اداری، حسابداری، وبگردی یا برنامه‌نویسی؛ فقط کاربردهایی را بنویس که با مشخصات سازگارند.
3. G: فقط نام ۳ تا ۶ بازی واقعی و متناسب با سخت‌افزار را با ویرگول بنویس؛ هیچ توضیحی درباره تنظیمات یا سطح اجرا ننویس.
4. SW: نام نرم‌افزارهای واقعی و مناسب را کوتاه بنویس. اگر سخت‌افزار توان دارد حتماً Adobe Photoshop و Adobe Illustrator را ذکر کن.
   
5. F1 تا F6: فقط ۳ تا ۶ نقطه قوت کوتاه، خودمانی و قانع‌کننده بنویس. مشخصات خامی که در پست چاپ می‌شوند را تکرار نکن؛ توضیح بده این ویژگی چه سودی برای خریدار دارد و چرا نخریدن این محصول ممکن است باعث از دست دادن یک مزیت عالی شود. از واژه‌های طبیعی مثل عالی، فوق‌العاده، خفن و ارزشمند استفاده کن، اما اغراق دروغین نکن. هر بار با جمله‌بندی و زاویه‌ای متفاوت بنویس تا تولید مجدد تکراری نباشد؛ مثل «با این SSD، منتظر بالا آمدن ویندوز نمی‌مانی» یا «این ترکیب برای چندکارگی روزمره واقعاً جواب می‌دهد».
   
6. N1, N2: دو محدودیت یا کاستی واقعی این نوع محصول (هر کدام ۳ تا ۶ کلمه)

مثال درست برای F (نقاط قوت تحلیلی):
- "پردازنده برای کارهای اداری و چندوظیفگی روان‌تر از مدل‌های دو هسته‌ای قدیمی است"
- "SSD زمان روشن‌شدن ویندوز و اجرای نرم‌افزارها را به شکل محسوسی کم می‌کند"
- "گرافیک مجزا برای کارهای گرافیکی و CAD نسبت به گرافیک مجتمع مناسب‌تر است"
- "ترکیب حافظه SSD و HDD هم سرعت اجرای برنامه‌ها و هم فضای آرشیو را فراهم می‌کند"
- "نمایشگر مات بازتاب نور را کم می‌کند و برای مطالعه طولانی مناسب‌تر است"
- "بدنه مقاوم و طراحی صنعتی برای استفاده کاری مداوم اطمینان بیشتری می‌دهد"

خروجی دقیقاً به این فرمت (فقط این خطوط، بدون ایموجی، بدون توضیح):
D: [توضیح جامع ۲-۳ جمله‌ای]
C: [توضیح CPU برای کاربر]
U1: [کاربرد اول]
U2: [کاربرد دوم]
U3: [کاربرد سوم]
G: [بازی‌های مناسب یا محدودیت بازی]
SW: [نرم‌افزارهای مناسب]
F1: [مزیت تحلیلی اول]
F2: [مزیت تحلیلی دوم]
F3: [مزیت تحلیلی سوم]
F4: [مزیت تحلیلی چهارم]
F5: [مزیت تحلیلی پنجم]
F6: [مزیت تحلیلی ششم]
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
1. D: توضیح جامع و جذاب محصول (1 تا 2 جمله، 10 تا 15 کلمه)
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
1. D: بازنویسی جامع‌تر متن فروشنده (1 تا 2 جمله)
2. U1 تا U5: کاربردهای واقعی محصول و فقط موارد سازگار با مشخصات
3. G: نام بازی‌های واقعی و متناسب با سخت‌افزار
4. SW: نام نرم‌افزارهای واقعی؛ در صورت توان سخت‌افزار حتماً Photoshop و Illustrator را بررسی و ذکر کن
5. F1 تا F6: فقط ۳ تا ۶ نقطه قوت کوتاه، خودمانی و قانع‌کننده بنویس. مشخصات خام و آپشن‌های چاپ‌شده را تکرار نکن؛ فایده واقعی برای خریدار را بگو. لحن طبیعی و کمی هیجان‌دار باشد و هر بار جمله‌بندی متفاوتی داشته باشد، بدون اغراق دروغین.
6. N1, N2: دو محدودیت واقعی (هر کدام ۳ تا ۶ کلمه)

خروجی دقیقاً به این فرمت:
D: [توضیح جامع]
U1: [کاربرد اول]
U2: [کاربرد دوم]
U3: [کاربرد سوم]
G: [بازی‌های مناسب یا محدودیت بازی]
SW: [نرم‌افزارهای مناسب]
F1: [مزیت تحلیلی اول]
F2: [مزیت تحلیلی دوم]
F3: [مزیت تحلیلی سوم]
F4: [مزیت تحلیلی چهارم]
F5: [مزیت تحلیلی پنجم]
F6: [مزیت تحلیلی ششم]
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
1. D: بازنویسی جامع‌تر متن فروشنده (۲1 تا 2 جمله)
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
