"""
هندلرهای مدیریت محصولات
شامل: نمایش لیست، پیش‌نمایش پست، ارسال دستی به کانال
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from app.services.subscription.service import get_active_subscription
from app.services.subscription.plans import get_plan
from app.database.connection import AsyncSessionLocal
from app.database.models import CustomerStatus, ProductPublishStatus
from app.services.customer_service import get_customer_by_telegram_id
from app.services.product_service import (
    get_all_products_by_customer,
    get_product_by_sku,
)
from app.services.business_service import (
    get_business_config_for_customer,
    get_business_for_customer,
)
from app.services.channel_service import get_customer_channels
from app.services.content.post_builder import build_post_caption
from app.services.publisher.telegram_publisher import (
    publish_post_to_telegram,
    edit_post_in_telegram,
)
from app.services.publisher.posted_message_service import (
    get_posted_message,
    create_posted_message,
    update_posted_message,
)
from app.utils.logger import log
from sqlalchemy import select


PRODUCTS_PER_PAGE = 5


async def product_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش منوی مدیریت محصولات"""

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
    published = sum(1 for p in products if p.publish_status == ProductPublishStatus.PUBLISHED)
    pending = len(products) - published

    text = (
        f"📦 مدیریت محصولات\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🏢 کسب‌وکار: {business_config.emoji} {business_config.name_fa}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📊 آمار:\n"
        f"├── کل: {len(products)}\n"
        f"├── ✅ موجود: {available}\n"
        f"├── ❌ ناموجود: {unavailable}\n"
        f"├── 📤 منتشر شده: {published}\n"
        f"└── ⏳ منتشر نشده: {pending}\n"
        f"━━━━━━━━━━━━━━━"
    )

    keyboard = [
        [InlineKeyboardButton("📋 لیست محصولات", callback_data="prod_list_0")],
    ]

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def prod_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش لیست محصولات با صفحه‌بندی"""

    query = update.callback_query
    await query.answer()

    user = query.from_user

    # استخراج شماره صفحه از callback_data (prod_list_0, prod_list_1, ...)
    try:
        page = int(query.data.replace("prod_list_", ""))
    except ValueError:
        page = 0

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            await query.edit_message_text("❌ خطا!")
            return

        products = await get_all_products_by_customer(session, customer.id)

    if not products:
        await query.edit_message_text("❌ محصولی وجود ندارد.")
        return

    # مرتب‌سازی: منتشر نشده‌ها اول
    products.sort(key=lambda p: (
        p.publish_status == ProductPublishStatus.PUBLISHED,
        p.product_name,
    ))

    # صفحه‌بندی
    total_pages = (len(products) + PRODUCTS_PER_PAGE - 1) // PRODUCTS_PER_PAGE
    start = page * PRODUCTS_PER_PAGE
    end = start + PRODUCTS_PER_PAGE
    page_products = products[start:end]

    text = f"📋 لیست محصولات ({page + 1}/{total_pages})\n━━━━━━━━━━━━━━━\n\n"

    for i, product in enumerate(page_products, start=start + 1):
        status_emoji = "✅" if product.is_available else "❌"
        published_emoji = "📤" if product.publish_status == ProductPublishStatus.PUBLISHED else "⏳"
        price = f"{int(product.price):,}"

        text += (
            f"{i}. {status_emoji} {published_emoji} {product.product_name}\n"
            f"    💰 {price} ت | 📦 {product.stock_qty} | 🔖 {product.sku}\n\n"
        )

    # دکمه‌های هر محصول
    keyboard = []
    for product in page_products:
        keyboard.append([
            InlineKeyboardButton(
                f"👁 {product.product_name[:30]}",
                callback_data=f"prod_view_{product.id}",
            )
        ])

    # دکمه‌های صفحه‌بندی
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"prod_list_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"prod_list_{page + 1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def prod_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """نمایش جزئیات یک محصول با دکمه‌های عملیات"""

    query = update.callback_query
    await query.answer()

    product_id = int(query.data.replace("prod_view_", ""))
    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            return

        from app.database.models import Product
        result = await session.execute(
            select(Product).where(
                Product.id == product_id,
                Product.customer_id == customer.id,
            )
        )
        product = result.scalar_one_or_none()

        if not product:
            await query.edit_message_text("❌ محصول پیدا نشد!")
            return

    status = "✅ موجود" if product.is_available else "❌ ناموجود"
    published = "📤 منتشر شده" if product.publish_status == ProductPublishStatus.PUBLISHED else "⏳ منتشر نشده"

    text = (
        f"📦 جزئیات محصول\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🖥 نام: {product.product_name}\n"
        f"🔖 کد: {product.sku}\n"
        f"💰 قیمت: {int(product.price):,} تومان\n"
        f"📦 موجودی: {product.stock_qty} عدد\n"
        f"🚦 وضعیت: {status}\n"
        f"📡 انتشار: {published}\n"
    )

    if product.specs:
        text += f"\n📋 مشخصات:\n"
        for key, value in product.specs.items():
            text += f"├── {key}: {value}\n"

    if product.description_manual:
        text += f"\n📝 توضیحات:\n{product.description_manual}\n"

    # چک کن آیا مشتری امکان AI داره
    async with AsyncSessionLocal() as session:
        subscription = await get_active_subscription(session, customer.id)
        can_use_ai = False
        if subscription:
            plan_obj = get_plan(subscription.plan_key)
            # AI برای همه پلن‌ها فعاله (اگه توکن داشته باشن)
            can_use_ai = True

    keyboard = [
        [InlineKeyboardButton("👁 پیش‌نمایش پست", callback_data=f"prod_preview_{product.id}")],
        [InlineKeyboardButton("📤 ارسال به کانال", callback_data=f"prod_publish_{product.id}")],
    ]

    if can_use_ai:
        keyboard.append([
            InlineKeyboardButton("🤖 تولید توضیحات با AI", callback_data=f"ai_start_{product.id}")
        ])

    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="prod_list_0")
    ])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def prod_preview_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پیش‌نمایش پست"""

    query = update.callback_query
    await query.answer()

    product_id = int(query.data.replace("prod_preview_", ""))
    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            return

        from app.database.models import Product
        result = await session.execute(
            select(Product).where(
                Product.id == product_id,
                Product.customer_id == customer.id,
            )
        )
        product = result.scalar_one_or_none()

        if not product:
            await query.edit_message_text("❌ محصول پیدا نشد!")
            return

        business_config = get_business_config_for_customer(customer)
        business = await get_business_for_customer(session, customer.id)

    caption = build_post_caption(product, business_config, business)

    preview_text = (
        f"👁 پیش‌نمایش پست\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"{caption}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📏 طول: {len(caption)} کاراکتر\n"
        f"(حداکثر مجاز: 1024)"
    )

    keyboard = [
        [InlineKeyboardButton("📤 ارسال به کانال", callback_data=f"prod_publish_{product.id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"prod_view_{product.id}")],
    ]

    await query.edit_message_text(preview_text, reply_markup=InlineKeyboardMarkup(keyboard))


async def prod_publish_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ارسال دستی پست به کانال"""

    query = update.callback_query
    await query.answer()

    product_id = int(query.data.replace("prod_publish_", ""))
    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            return

        # گرفتن کانال‌ها
        channels = await get_customer_channels(session, customer.id, only_active=True)

        if not channels:
            await query.edit_message_text(
                "❌ کانالی متصل نکرده‌اید!\n\n"
                "از منوی '📢 مدیریت کانال' یک کانال اضافه کنید."
            )
            return

        # گرفتن محصول
        from app.database.models import Product
        result = await session.execute(
            select(Product).where(
                Product.id == product_id,
                Product.customer_id == customer.id,
            )
        )
        product = result.scalar_one_or_none()

        if not product:
            await query.edit_message_text("❌ محصول پیدا نشد!")
            return

        business_config = get_business_config_for_customer(customer)
        business = await get_business_for_customer(session, customer.id)

    # نمایش پیام "در حال ارسال"
    await query.edit_message_text("⏳ در حال ارسال به کانال‌ها...")

    # ساخت کپشن
    caption = build_post_caption(product, business_config, business)

    # ارسال به هر کانال
    results = []
    for channel in channels:
        publish_result = await _publish_or_edit(
            bot=context.bot,
            product=product,
            channel=channel,
            caption=caption,
        )
        results.append((channel, publish_result))

    # ساخت متن نتیجه
    text = "📤 نتیجه ارسال\n━━━━━━━━━━━━━━━\n\n"
    success_count = 0
    fallback_count = 0

    for channel, res in results:
        if res.success:
            if res.used_fallback:
                text += (
                    f"⚠️ {channel.channel_identifier}\n"
                    f"   ارسال شد (بدون عکس - لینک عکس نامعتبر)\n\n"
                )
                fallback_count += 1
            else:
                text += f"✅ {channel.channel_identifier}\n   ارسال شد\n\n"
            success_count += 1
        else:
            text += f"❌ {channel.channel_identifier}\n   {res.error_message}\n\n"

    text += f"━━━━━━━━━━━━━━━\n"
    text += f"موفق: {success_count}/{len(results)}"

    if fallback_count > 0:
        text += (
            f"\n\n⚠️ توجه: {fallback_count} پست بدون عکس ارسال شد.\n"
            f"لطفاً لینک عکس محصولات را چک کنید."
        )

    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"prod_view_{product.id}")],
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # آپدیت وضعیت publish محصول اگه حداقل یک ارسال موفق بود
    if success_count > 0:
        async with AsyncSessionLocal() as session:
            from app.database.models import Product
            result = await session.execute(
                select(Product).where(Product.id == product_id)
            )
            p = result.scalar_one_or_none()
            if p:
                p.publish_status = ProductPublishStatus.PUBLISHED
                await session.commit()


async def _publish_or_edit(bot, product, channel, caption):
    """
    اگه محصول قبلاً در این کانال پست شده → ویرایش
    اگه نه → ارسال جدید
    """
    async with AsyncSessionLocal() as session:
        # چک کن قبلاً پست شده یا نه
        existing = await get_posted_message(session, product.id, channel.id)

        if existing and existing.telegram_message_id:
            # ویرایش
            has_photo = bool(product.image_url)
            result = await edit_post_in_telegram(
                bot=bot,
                channel_identifier=channel.channel_identifier,
                message_id=existing.telegram_message_id,
                new_caption=caption,
                has_photo=has_photo,
            )

            if result.success:
                await update_posted_message(
                    session=session,
                    posted_message=existing,
                    new_caption=caption,
                    new_price=int(product.price),
                    new_stock_qty=product.stock_qty,
                )
            return result
        else:
            # ارسال جدید
            result = await publish_post_to_telegram(
                bot=bot,
                channel_identifier=channel.channel_identifier,
                caption=caption,
                photo_url=product.image_url,
            )

            if result.success and result.message_id:
                await create_posted_message(
                    session=session,
                    product_id=product.id,
                    channel_id=channel.id,
                    telegram_message_id=result.message_id,
                    caption=caption,
                    price=int(product.price),
                    stock_qty=product.stock_qty,
                )
            return result
