"""
تست تولید هشتگ
"""

from app.services.content.hashtag_generator import (
    generate_hashtags,
    format_hashtags_for_post,
    _make_brand_hashtag,
    _make_price_range_hashtag,
)
from app.business.config import get_business
from app.database.models import Product


def make_test_product(brand="Lenovo", price=42500000) -> Product:
    """ساخت محصول تست"""
    product = Product()
    product.product_name = "IdeaPad 5"
    product.price = price
    product.stock_qty = 5
    product.is_available = True
    product.specs = {"brand": brand, "cpu": "i7"}
    return product


def test_generate_hashtags_includes_static():
    """هشتگ‌های ثابت باید موجود باشن"""
    business = get_business("laptop_store")
    product = make_test_product()
    tags = generate_hashtags(product, business)

    assert "#لپتاپ" in tags
    assert "#کامپیوتر" in tags


def test_generate_hashtags_includes_brand():
    """هشتگ برند باید موجود باشه"""
    business = get_business("laptop_store")
    product = make_test_product(brand="Lenovo")
    tags = generate_hashtags(product, business)

    assert any("لنوو" in t for t in tags)


def test_generate_hashtags_includes_price_range():
    """هشتگ رنج قیمت باید موجود باشه"""
    business = get_business("laptop_store")
    product = make_test_product(price=42500000)  # زیر ۵۰
    tags = generate_hashtags(product, business)

    assert any("۵۰_میلیون" in t for t in tags)


def test_brand_hashtag_known():
    """هشتگ برند معروف"""
    result = _make_brand_hashtag("laptop_store", "Lenovo")
    assert result == "#لپتاپ_لنوو"


def test_brand_hashtag_unknown():
    """برند ناشناخته باید همون اسم استفاده بشه"""
    result = _make_brand_hashtag("laptop_store", "Xiaomi")
    assert result == "#لپتاپ_Xiaomi"


def test_price_range_low():
    """رنج قیمت زیر ۲۰ میلیون"""
    result = _make_price_range_hashtag("laptop_store", 15_000_000)
    assert "۲۰" in result


def test_price_range_high():
    """رنج قیمت بالای ۱۵۰ میلیون"""
    result = _make_price_range_hashtag("laptop_store", 200_000_000)
    assert "بالای" in result


def test_price_range_zero():
    """قیمت صفر → None"""
    result = _make_price_range_hashtag("laptop_store", 0)
    assert result is None


def test_format_hashtags_empty():
    """لیست خالی → رشته خالی"""
    assert format_hashtags_for_post([]) == ""


def test_format_hashtags_multiple():
    """چند هشتگ با فاصله"""
    tags = ["#لپتاپ", "#لنوو", "#گیمینگ"]
    result = format_hashtags_for_post(tags)
    assert result == "#لپتاپ #لنوو #گیمینگ"


def test_max_hashtags_limit():
    """محدودیت تعداد"""
    business = get_business("laptop_store")
    product = make_test_product()
    tags = generate_hashtags(product, business, max_hashtags=3)
    assert len(tags) <= 3