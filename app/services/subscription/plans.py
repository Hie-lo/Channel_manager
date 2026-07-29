"""
تعریف پلن‌های اشتراک
تمام مشخصات پلن‌ها اینجا متمرکز شده
"""

from dataclasses import dataclass


@dataclass
class PlanFeatures:
    """امکانات یک پلن"""
    key: str                    # کلید یکتا (BRONZE/SILVER/GOLD)
    name_fa: str                # نام فارسی
    emoji: str                  # ایموجی
    max_channels: int           # حداکثر تعداد کانال
    max_products: int           # حداکثر تعداد محصول
    monthly_ai_tokens: int      # توکن AI رایگان ماهانه
    can_customize_template: bool  # امکان شخصی‌سازی قالب
    can_use_ai: bool           # امکان استفاده از AI
    realtime_reports: bool     # گزارش لحظه‌ای
    price_monthly: int         # قیمت ماهانه (تومان)
    price_quarterly: int       # قیمت ۳ ماهه (تومان)
    price_half_yearly: int     # قیمت ۶ ماهه (تومان)


# ─── پلن‌های موجود ───
PLANS: dict[str, PlanFeatures] = {
    "BRONZE": PlanFeatures(
        key="BRONZE",
        name_fa="برنزی",
        emoji="🥉",
        max_channels=1,
        max_products=50,
        monthly_ai_tokens=10,
        can_customize_template=False,
        can_use_ai=True,
        realtime_reports=False,
        price_monthly=500_000,
        price_quarterly=1_350_000,
        price_half_yearly=2_750_000,
    ),
    "SILVER": PlanFeatures(
        key="SILVER",
        name_fa="نقره‌ای",
        emoji="🥈",
        max_channels=3,
        max_products=300,
        monthly_ai_tokens=50,
        can_customize_template=False,
        can_use_ai= True,
        realtime_reports=False,
        price_monthly=1_700_000,
        price_quarterly=3_950_000,
        price_half_yearly=8_000_000,
    ),
    "GOLD": PlanFeatures(
        key="GOLD",
        name_fa="طلایی",
        emoji="🥇",
        max_channels=9,
        max_products=9999,
        monthly_ai_tokens=100,
        can_customize_template=True,
        can_use_ai=True,
        realtime_reports=True,
        price_monthly=3_000_000,
        price_quarterly=7_800_000,
        price_half_yearly=15_000_000,
    ),
}


def get_plan(plan_key: str) -> PlanFeatures | None:
    """دریافت اطلاعات یک پلن"""
    return PLANS.get(plan_key.upper())


def get_all_plans() -> list[PlanFeatures]:
    """لیست همه پلن‌ها"""
    return list(PLANS.values())


def format_price(price: int) -> str:
    """قیمت رو با کاما فرمت میکنه: 300000 -> 300,000"""
    return f"{price:,}"


def get_duration_price(plan: PlanFeatures, duration_key: str) -> int:
    """قیمت پلن بر اساس مدت اشتراک"""
    if duration_key == "monthly":
        return plan.price_monthly
    elif duration_key == "quarterly":
        return plan.price_quarterly
    elif duration_key == "half_yearly":
        return plan.price_half_yearly
    return 0


def get_duration_days(duration_key: str) -> int:
    """تعداد روزهای هر مدت"""
    if duration_key == "monthly":
        return 30
    elif duration_key == "quarterly":
        return 90
    elif duration_key == "half_yearly":
        return 180
    return 0


def get_duration_name(duration_key: str) -> str:
    """نام فارسی مدت اشتراک"""
    names = {
        "monthly": "۱ ماهه",
        "quarterly": "۳ ماهه",
        "half_yearly": "۶ ماهه",
    }
    return names.get(duration_key, "")