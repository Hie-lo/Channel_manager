"""
تست پلن‌های اشتراک
"""

from app.services.subscription.plans import (
    get_plan,
    get_all_plans,
    get_duration_price,
    get_duration_days,
    get_duration_name,
    format_price,
    PLANS,
)


def test_all_three_plans_exist():
    """۳ پلن باید موجود باشه"""
    plans = get_all_plans()
    assert len(plans) == 3
    keys = [p.key for p in plans]
    assert "BRONZE" in keys
    assert "SILVER" in keys
    assert "GOLD" in keys


def test_get_plan_returns_correct_plan():
    plan = get_plan("GOLD")
    assert plan is not None
    assert plan.key == "GOLD"
    assert plan.can_use_ai is True
    assert plan.monthly_ai_tokens == 100


def test_get_plan_case_insensitive():
    assert get_plan("gold") is not None
    assert get_plan("Gold") is not None


def test_get_plan_invalid_returns_none():
    assert get_plan("PLATINUM") is None


def test_bronze_plan_limits():
    plan = get_plan("BRONZE")
    assert plan.max_channels == 1
    assert plan.max_products == 50
    assert plan.can_use_ai is False


def test_silver_plan_limits():
    plan = get_plan("SILVER")
    assert plan.max_channels == 3
    assert plan.max_products == 200


def test_gold_plan_features():
    plan = get_plan("GOLD")
    assert plan.can_customize_template is True
    assert plan.realtime_reports is True


def test_duration_prices():
    plan = get_plan("SILVER")
    assert get_duration_price(plan, "monthly") == 300_000
    assert get_duration_price(plan, "quarterly") == 800_000
    assert get_duration_price(plan, "half_yearly") == 1_500_000


def test_duration_days():
    assert get_duration_days("monthly") == 30
    assert get_duration_days("quarterly") == 90
    assert get_duration_days("half_yearly") == 180


def test_duration_names():
    assert get_duration_name("monthly") == "۱ ماهه"
    assert get_duration_name("quarterly") == "۳ ماهه"
    assert get_duration_name("half_yearly") == "۶ ماهه"


def test_format_price():
    assert format_price(1000) == "1,000"
    assert format_price(150000) == "150,000"
    assert format_price(0) == "0"