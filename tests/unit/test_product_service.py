"""
تست سرویس محصولات
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.product_service import (
    _create_product,
    _update_product,
    ProductSaveResult,
)
from app.database.models import Product


def test_create_product_from_data():
    """ساخت محصول جدید از دیتا"""
    data = {
        "sku": "LP001",
        "product_name": "IdeaPad 5",
        "price": 42500000,
        "stock": 5,
        "description": "لپتاپ خوب",
        "image_url": "https://example.com/img.jpg",
        "specs": {"brand": "Lenovo", "cpu": "i7"},
    }

    product = _create_product(customer_id=1, business_id=1, data=data)

    assert product.sku == "LP001"
    assert product.product_name == "IdeaPad 5"
    assert product.price == 42500000
    assert product.stock_qty == 5
    assert product.is_available is True
    assert product.specs["brand"] == "Lenovo"


def test_create_product_zero_stock_unavailable():
    """محصول با موجودی صفر باید is_available=False باشه"""
    data = {
        "sku": "LP001",
        "product_name": "Test",
        "price": 1000,
        "stock": 0,
        "specs": {},
    }
    product = _create_product(customer_id=1, business_id=None, data=data)
    assert product.is_available is False


def test_update_product_price_change():
    """آپدیت قیمت محصول"""
    product = Product()
    product.product_name = "IdeaPad 5"
    product.price = 40000000
    product.stock_qty = 5
    product.is_available = True
    product.description_custom = "قدیم"
    product.image_url = None
    product.specs = {"brand": "Lenovo"}

    new_data = {
        "product_name": "IdeaPad 5",
        "price": 42000000,  # قیمت تغییر کرده
        "stock": 5,
        "specs": {"brand": "Lenovo"},
    }

    changed = _update_product(product, new_data)

    assert changed is True
    assert product.price == 42000000


def test_update_product_no_change():
    """اگر تغییری نبود، False برگرده"""
    product = Product()
    product.product_name = "IdeaPad"
    product.price = 40000000
    product.stock_qty = 5
    product.is_available = True
    product.description_custom = "test"
    product.image_url = None
    product.specs = {}

    new_data = {
        "product_name": "IdeaPad",
        "price": 40000000,
        "stock": 5,
        "specs": {},
    }

    changed = _update_product(product, new_data)
    assert changed is False


def test_update_product_stock_change():
    """آپدیت موجودی و is_available"""
    product = Product()
    product.product_name = "Test"
    product.price = 1000
    product.stock_qty = 5
    product.is_available = True
    product.description_custom = None
    product.image_url = None
    product.specs = {}

    # موجودی شد صفر
    new_data = {
        "product_name": "Test",
        "price": 1000,
        "stock": 0,
        "specs": {},
    }

    changed = _update_product(product, new_data)

    assert changed is True
    assert product.stock_qty == 0
    assert product.is_available is False


def test_product_save_result_defaults():
    """مقادیر پیش‌فرض ProductSaveResult"""
    result = ProductSaveResult()
    assert result.new_count == 0
    assert result.updated_count == 0
    assert result.unchanged_count == 0
    assert result.error_count == 0
    assert result.errors == []