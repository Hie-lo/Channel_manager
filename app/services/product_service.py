"""
سرویس مدیریت محصولات
"""

from dataclasses import dataclass, field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Product
from app.utils.logger import log
from app.utils.time import utc_now_naive


@dataclass
class ProductSaveResult:
    """نتیجه ذخیره محصولات"""
    new_count: int = 0
    updated_count: int = 0
    unchanged_count: int = 0
    error_count: int = 0
    errors: list[str] = field(default_factory=list)


async def get_product_by_sku(
    session: AsyncSession,
    customer_id: int,
    sku: str,
) -> Product | None:
    """پیدا کردن محصول با SKU"""
    result = await session.execute(
        select(Product).where(
            Product.customer_id == customer_id,
            Product.sku == sku,
        )
    )
    return result.scalar_one_or_none()


async def get_all_products_by_customer(
    session: AsyncSession,
    customer_id: int,
) -> list[Product]:
    """لیست همه محصولات یک مشتری"""
    result = await session.execute(
        select(Product).where(Product.customer_id == customer_id)
    )
    return list(result.scalars().all())


async def count_products_by_customer(
    session: AsyncSession,
    customer_id: int,
) -> int:
    """شمارش محصولات مشتری"""
    products = await get_all_products_by_customer(session, customer_id)
    return len(products)


async def save_products_from_excel(
    session: AsyncSession,
    customer_id: int,
    business_id: int | None,
    products_data: list[dict],
    max_products_limit: int,
) -> ProductSaveResult:
    """
    ذخیره یا آپدیت محصولات

    برای هر محصول:
    - اگر SKU جدید است → محصول جدید
    - اگر SKU وجود دارد → آپدیت
    """
    result = ProductSaveResult()

    # چک محدودیت تعداد محصولات
    existing_count = await count_products_by_customer(session, customer_id)
    existing_skus = {
        p.sku: p
        for p in await get_all_products_by_customer(session, customer_id)
    }

    for product_data in products_data:
        try:
            sku = product_data.get("sku")
            if not sku:
                result.error_count += 1
                continue

            existing_product = existing_skus.get(sku)

            if existing_product:
                # آپدیت
                changed = _update_product(existing_product, product_data)
                if changed:
                    result.updated_count += 1
                else:
                    result.unchanged_count += 1
            else:
                # چک محدودیت
                if existing_count + result.new_count >= max_products_limit:
                    result.errors.append(
                        f"محدودیت پلن شما ({max_products_limit} محصول) پر شده"
                    )
                    result.error_count += 1
                    continue

                # محصول جدید
                new_product = _create_product(customer_id, business_id, product_data)
                session.add(new_product)
                result.new_count += 1

        except Exception as e:
            log.error(f"خطا در ذخیره محصول {product_data.get('sku')}: {e}")
            result.errors.append(f"خطا در محصول {product_data.get('sku')}: {str(e)}")
            result.error_count += 1

    await session.commit()

    log.info(
        f"ذخیره محصولات: {result.new_count} جدید، "
        f"{result.updated_count} آپدیت، {result.unchanged_count} بدون تغییر، "
        f"{result.error_count} خطا"
    )

    return result


def _create_product(
    customer_id: int,
    business_id: int | None,
    data: dict,
) -> Product:
    """ساخت رکورد محصول جدید"""
    now = utc_now_naive()

    return Product(
        customer_id=customer_id,
        business_id=business_id,
        sub_category_key=data.get("sub_category_key"),  # ← جدید
        sku=data.get("sku"),
        product_name=data.get("product_name", ""),
        price=data.get("price", 0),
        stock_qty=data.get("stock", 0),
        is_available=(data.get("stock", 0) > 0),
        description_manual=data.get("description"),
        image_url=data.get("image_url"),
        specs=data.get("specs", {}),
        created_at=now,
        updated_at=now,
    )



@dataclass
class ProductChangeDetection:
    """تشخیص تغییرات محصول"""
    price_changed: bool = False
    stock_changed: bool = False
    name_changed: bool = False
    description_changed: bool = False
    image_changed: bool = False
    specs_changed: bool = False
    old_price: int = 0
    new_price: int = 0
    old_stock: int = 0
    new_stock: int = 0

    @property
    def has_any_change(self) -> bool:
        return any([
            self.price_changed,
            self.stock_changed,
            self.name_changed,
            self.description_changed,
            self.image_changed,
            self.specs_changed,
        ])

    @property
    def has_price_or_stock_change(self) -> bool:
        return self.price_changed or self.stock_changed


def detect_product_changes(product: Product, data: dict) -> ProductChangeDetection:
    """تشخیص تغییرات یک محصول"""
    detection = ProductChangeDetection()

    new_name = data.get("product_name", "")
    if new_name and product.product_name != new_name:
        detection.name_changed = True

    new_price = int(data.get("price", 0))
    if int(product.price) != new_price:
        detection.price_changed = True
        detection.old_price = int(product.price)
        detection.new_price = new_price

    new_stock = int(data.get("stock", 0))
    if product.stock_qty != new_stock:
        detection.stock_changed = True
        detection.old_stock = product.stock_qty
        detection.new_stock = new_stock

    new_desc = data.get("description")
    if new_desc and product.description_manual != new_desc:
        detection.description_changed = True

    new_image = data.get("image_url")
    if new_image and product.image_url != new_image:
        detection.image_changed = True

    # مدیریت امن specs (jsonb)
    new_specs = data.get("specs", {})
    if new_specs:
        try:
            # اطمینان از dict بودن
            if not isinstance(new_specs, dict):
                new_specs = {}

            # مقایسه با specs فعلی
            current_specs = product.specs if isinstance(product.specs, dict) else {}

            # merge specs (نه replace) - برای اینکه ستون‌های قدیمی حذف نشن
            merged_specs = {**current_specs, **new_specs}

            if merged_specs != current_specs:
                product.specs = merged_specs
                changed = True
        except Exception as e:
            log.error(f"خطا در آپدیت specs محصول {product.sku}: {e}")
            # ادامه بده - فقط specs آپدیت نشد

    return detection


def _update_product(product: Product, data: dict) -> bool:
    """
    آپدیت محصول موجود
    Returns: True اگر تغییری بوده
    """
    detection = detect_product_changes(product, data)

    if not detection.has_any_change:
        return False

    # اعمال تغییرات
    if detection.name_changed:
        product.product_name = data.get("product_name", "")

    if detection.price_changed:
        product.price = detection.new_price

    if detection.stock_changed:
        product.stock_qty = detection.new_stock
        product.is_available = (detection.new_stock > 0)

    if detection.description_changed:
        product.description_manual = data.get("description")

    if detection.image_changed:
        product.image_url = data.get("image_url")

    if detection.specs_changed:
        product.specs = data.get("specs", {})

    product.updated_at = utc_now_naive()

    return True


async def delete_all_products(
    session: AsyncSession,
    customer_id: int,
) -> int:
    """حذف همه محصولات یک مشتری (برای reset)"""
    products = await get_all_products_by_customer(session, customer_id)
    count = len(products)

    for product in products:
        await session.delete(product)

    await session.commit()
    log.info(f"همه محصولات مشتری {customer_id} حذف شدند: {count} محصول")
    return count

async def get_pending_products_for_customer(
    session: AsyncSession,
    customer_id: int,
    limit: int = 100,
) -> list[Product]:
    """
    گرفتن محصولات منتشر نشده مشتری (که موجود هستن)
    مرتب شده بر اساس تاریخ ایجاد (قدیمی‌ها اول)
    """
    from app.database.models import ProductPublishStatus

    result = await session.execute(
        select(Product)
        .where(
            Product.customer_id == customer_id,
            Product.publish_status == ProductPublishStatus.PENDING,
            Product.is_available == True,
        )
        .order_by(Product.created_at.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_next_pending_product(
    session: AsyncSession,
    customer_id: int,
) -> Product | None:
    """گرفتن محصول بعدی که باید پست بشه"""
    products = await get_pending_products_for_customer(session, customer_id, limit=1)
    return products[0] if products else None


async def mark_product_as_published(
    session: AsyncSession,
    product_id: int,
) -> None:
    """علامت‌گذاری محصول به عنوان منتشر شده"""
    from app.database.models import ProductPublishStatus

    result = await session.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if product:
        product.publish_status = ProductPublishStatus.PUBLISHED
        product.updated_at = utc_now_naive()
        await session.commit()


async def mark_product_as_failed(
    session: AsyncSession,
    product_id: int,
) -> None:
    """علامت‌گذاری محصول به عنوان ارسال ناموفق"""
    from app.database.models import ProductPublishStatus

    result = await session.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if product:
        product.publish_status = ProductPublishStatus.FAILED
        product.updated_at = utc_now_naive()
        await session.commit()