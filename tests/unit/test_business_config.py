"""
تست تنظیمات کسب‌وکار
"""

from app.business.config import (
    get_business,
    get_all_businesses,
    get_business_excel_path,
    LAPTOP_STORE,
    BUSINESSES,
)


def test_laptop_business_exists():
    """کسب‌وکار لپتاپ باید وجود داشته باشه"""
    business = get_business("laptop_store")
    assert business is not None
    assert business.key == "laptop_store"
    assert business.name_fa == "فروش لپتاپ و کامپیوتر"


def test_get_all_businesses_returns_list():
    """لیست کسب‌وکارها نباید خالی باشه"""
    businesses = get_all_businesses()
    assert len(businesses) > 0
    assert LAPTOP_STORE in businesses


def test_laptop_has_required_fields():
    """لپتاپ باید فیلدهای اجباری داشته باشه"""
    business = get_business("laptop_store")
    field_keys = [f.key for f in business.fields]

    assert "sku" in field_keys
    assert "product_name" in field_keys
    assert "brand" in field_keys
    assert "price" in field_keys
    assert "stock" in field_keys


def test_laptop_price_check_interval():
    """بازه چک قیمت لپتاپ روزانه (۲۴ ساعت)"""
    business = get_business("laptop_store")
    assert business.price_check_interval_hours == 24


def test_get_business_invalid_returns_none():
    """کسب‌وکار غیرموجود باید None برگرده"""
    assert get_business("nonexistent") is None


def test_laptop_has_static_hashtags():
    """لپتاپ باید هشتگ ثابت داشته باشه"""
    business = get_business("laptop_store")
    assert len(business.static_hashtags) > 0
    assert "#لپتاپ" in business.static_hashtags


def test_required_fields_marked():
    """فیلدهای اجباری باید required=True داشته باشن"""
    business = get_business("laptop_store")
    required_fields = [f for f in business.fields if f.required]
    assert len(required_fields) >= 5  # حداقل ۵ فیلد اجباری