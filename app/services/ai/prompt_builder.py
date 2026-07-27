"""
ساخت پرامپت‌های بهینه برای AI
پرامپت‌ها کوتاه و ساختاریافته‌اند
"""

from app.database.models import Product
from app.business.config import BusinessConfig, get_subcategory


SYSTEM_PROMPT = """تو یک کپی‌رایتر فارسی برای پست فروشگاهی تلگرام هستی.
خروجی کوتاه، دقیق و فقط در فرمت خواسته‌شده باشد.
هرگز متن اضافی، توضیح یا مقدمه ننویس."""


def build_generation_prompt(
    product: Product,
    business_config: BusinessConfig,
) -> str:
    """
    ساخت پرامپت برای تولید توضیحات جدید
    """
    subcategory = get_subcategory(business_config.key, product.sub_category_key)
    subcategory_name = subcategory.name_fa if subcategory else "محصول"

    # ساخت spec string
    specs_str = _build_specs_string(product)

    prompt = f"""biz={business_config.key}
subcategory={subcategory_name}
mode=new
name={product.product_name}
specs={specs_str}
base=

قوانین:
- desc: یک جمله کوتاه جذاب (حداکثر ۱۲ کلمه)
- ۲ مزیت (هر کدام حداکثر ۵ کلمه)
- ۲ نکته (به جای معایب - حداکثر ۵ کلمه)
- بدون هیچ متن اضافی

خروجی دقیقاً به این فرمت (بدون تغییر):
D: [توضیح یک خطی]
P1: [مزیت اول]
P2: [مزیت دوم]
N1: [نکته اول]
N2: [نکته دوم]"""

    return prompt


def build_improve_prompt(
    product: Product,
    business_config: BusinessConfig,
    existing_description: str,
) -> str:
    """
    ساخت پرامپت برای بهبود متن موجود
    """
    subcategory = get_subcategory(business_config.key, product.sub_category_key)
    subcategory_name = subcategory.name_fa if subcategory else "محصول"

    specs_str = _build_specs_string(product)

    prompt = f"""biz={business_config.key}
subcategory={subcategory_name}
mode=improve
name={product.product_name}
specs={specs_str}
base={existing_description}

قوانین:
- معنای متن اصلی رو حفظ کن ولی جذاب‌تر بنویس
- desc: یک جمله کوتاه (حداکثر ۱۲ کلمه)
- ۲ مزیت واقعی بر اساس مشخصات (هر کدام حداکثر ۵ کلمه)
- ۲ نکته (نه معایب - حداکثر ۵ کلمه)
- بدون هیچ متن اضافی

خروجی دقیقاً به این فرمت (بدون تغییر):
D: [توضیح یک خطی]
P1: [مزیت اول]
P2: [مزیت دوم]
N1: [نکته اول]
N2: [نکته دوم]"""

    return prompt


def _build_specs_string(product: Product) -> str:
    """تبدیل specs به رشته کوتاه"""
    if not product.specs:
        return ""

    parts = []
    # ترتیب مهمه - مهم‌ترین‌ها اول
    priority_keys = ["brand", "cpu", "ram", "storage", "gpu", "screen",
                     "resolution", "component_type", "accessory_type"]

    for key in priority_keys:
        if key in product.specs:
            value = product.specs[key]
            if value:
                parts.append(f"{key}={value}")

    # بقیه فیلدها
    for key, value in product.specs.items():
        if key not in priority_keys and value:
            parts.append(f"{key}={value}")

    return "؛ ".join(parts)