"""
تست ساخت پست
"""

from app.services.content.post_builder import (
    build_post_caption,
    _format_price,
    _get_stock_status,
    _clean_empty_lines,
    _build_description_block,
)
from app.business.config import get_business
from app.database.models import Product


def make_test_product(**kwargs) -> Product:
    product = Product()
    product.product_name = kwargs.get("name", "IdeaPad 5 Pro")
    product.sku = kwargs.get("sku", "LP001")
    product.price = kwargs.get("price", 42500000)
    product.stock_qty = kwargs.get("stock", 5)
    product.is_available = kwargs.get("stock", 5) > 0
    product.description_manual = kwargs.get("description")
    product.image_url = kwargs.get("image_url")
    product.specs = kwargs.get("specs", {
        "brand": "Lenovo",
        "cpu": "i7-12700H",
        "ram": "16GB",
        "storage": "512GB SSD",
    })
    from datetime import datetime
    product.updated_at = datetime.now()
    return product


def test_format_price_normal():
    assert _format_price(42500000) == "42,500,000"


def test_format_price_zero():
    assert _format_price(0) == "-"


def test_stock_status_available():
    product = make_test_product(stock=5)
    assert "موجود" in _get_stock_status(product)


def test_stock_status_unavailable():
    product = make_test_product(stock=0)
    assert "ناموجود" in _get_stock_status(product)


def test_description_block_with_text():
    product = make_test_product(description="لپتاپ خوب")
    result = _build_description_block(product)
    assert "📝" in result
    assert "لپتاپ خوب" in result


def test_description_block_empty():
    product = make_test_product(description=None)
    result = _build_description_block(product)
    assert result == ""


def test_clean_empty_lines():
    text = "line1\n\n\n\nline2\n\n\nline3"
    result = _clean_empty_lines(text)
    lines = result.split("\n")
    # نباید بیش از یک خط خالی متوالی باشه
    for i in range(len(lines) - 1):
        if lines[i] == "" and lines[i + 1] == "":
            assert False, "خطوط خالی متوالی وجود دارد"


def test_build_post_caption_basic():
    """تست ساخت پست کامل"""
    business = get_business("laptop_store")
    product = make_test_product()

    caption = build_post_caption(product, business, business=None)

    # چک محتوای اصلی
    assert "IdeaPad 5 Pro" in caption
    assert "42,500,000" in caption
    assert "موجود" in caption
    assert "Lenovo" in caption or "لنوو" in caption


def test_build_post_out_of_stock():
    """پست محصول ناموجود"""
    business = get_business("laptop_store")
    product = make_test_product(stock=0)

    caption = build_post_caption(product, business, business=None)
    assert "ناموجود" in caption


def test_build_post_with_description():
    """پست با توضیحات"""
    business = get_business("laptop_store")
    product = make_test_product(description="بهترین انتخاب برای گیم")

    caption = build_post_caption(product, business, business=None)
    assert "بهترین انتخاب" in caption