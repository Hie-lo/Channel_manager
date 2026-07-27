"""
هندلرهای مدیریت محصولات
فعلاً فقط نمایش لیست
"""

from telegram import Update
from telegram.ext import ContextTypes

from app.database.connection import AsyncSessionLocal
from app.database.models import CustomerStatus
from app.services.customer_service import get_customer_by_telegram_id
from app.services.product_service import get_all_products_by_customer
from app.services.business_service import get_business_config_for_customer


async def product_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش لیست محصولات"""

    user = update.effective_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)

        if not customer or customer.customer_status != CustomerStatus.ACTIVE:
            await update.message.reply_text("❌ حساب شما فعال نیست.")
            return

        products = await get_all_products_by_customer(session, customer.id)
        business_config = get_business_config_for_customer(customer)

    if not products:
        await update.message.reply_text(
            "📦 مدیریت محصولات\n"
            "━━━━━━━━━━━━━━━\n\n"
            "❌ هنوز محصولی ندارید.\n\n"
            "از منوی '📤 آپلود محصولات' فایل اکسل را ارسال کنید."
        )
        return

    available = sum(1 for p in products if p.is_available)
    unavailable = len(products) - available

    text = (
        f"📦 مدیریت محصولات\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🏢 کسب‌وکار: {business_config.emoji} {business_config.name_fa}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📊 آمار:\n"
        f"├── کل محصولات: {len(products)}\n"
        f"├── ✅ موجود: {available}\n"
        f"└── ❌ ناموجود: {unavailable}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"🆕 آخرین ۵ محصول:\n\n"
    )

    # نمایش ۵ محصول آخر
    recent_products = sorted(products, key=lambda p: p.updated_at, reverse=True)[:5]
    for product in recent_products:
        status = "✅" if product.is_available else "❌"
        price_formatted = f"{int(product.price):,}"
        text += (
            f"{status} {product.product_name}\n"
            f"   💰 {price_formatted} تومان | "
            f"📦 {product.stock_qty} عدد | "
            f"🔖 {product.sku}\n\n"
        )

    await update.message.reply_text(text)