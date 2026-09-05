"""
Helper برای محاسبه hash عکس‌های محصول برای تشخیص تغییرات
"""
import hashlib
from app.database.models import Product, Platform


async def calculate_media_hash(product: Product, platform: Platform) -> str:
    """
    محاسبه hash از عکس‌های محصول برای تشخیص تغییر
    
    Returns:
        رشته hash (md5) یا رشته خالی اگر عکسی نباشد
    """
    from app.services.product_media_service import get_product_medias
    from app.database.connection import AsyncSessionLocal
    
    # برای پست سفارشی (CUSTOM)
    if product.sku == "CUSTOM" and product.specs and "custom_medias" in product.specs:
        custom_medias = product.specs["custom_medias"]
        if custom_medias:
            # ساخت رشته از file_id ها
            media_str = "|".join(m["file_id"] for m in custom_medias)
            return hashlib.md5(media_str.encode()).hexdigest()
        return ""
    
    # برای محصولات عادی
    async with AsyncSessionLocal() as session:
        medias = await get_product_medias(session, product.id, platform)
    
    if medias:
        # ساخت رشته از file_id ها
        media_str = "|".join(m.file_id for m in medias)
        return hashlib.md5(media_str.encode()).hexdigest()
    
    # اگه عکسی نداره ولی image_url داره
    if product.image_url and product.image_url.strip():
        return hashlib.md5(product.image_url.encode()).hexdigest()
    
    return ""
