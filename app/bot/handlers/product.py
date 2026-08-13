"""
هندلرهای مدیریت محصولات
شامل: نمایش لیست، پیش‌نمایش پست، ارسال دستی به کانال
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from app.services.subscription.service import get_active_subscription
from app.services.subscription.plans import get_plan
from app.database.connection import AsyncSessionLocal
from app.database.models import CustomerStatus, Product, ProductPublishStatus, Platform
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
from app.services.product_media_service import (
    get_customer_uploaded_media,
    get_photo_source_for_platform,
)

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

    # گرفتن business_config برای پیدا کردن اسم دسته‌ها
    business_config = None
    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if customer:
            business_config = get_business_config_for_customer(customer)

    # ساخت map از sub_category_key به نام فارسی
    subcategory_names = {}
    if business_config:
        for sc in business_config.sub_categories:
            subcategory_names[sc.key] = f"{sc.emoji} {sc.name_fa}"

    text = f"📋 لیست محصولات ({page + 1}/{total_pages})\n━━━━━━━━━━━━━━━\n\n"

    for i, product in enumerate(page_products, start=start + 1):
        status_emoji = "✅" if product.is_available else "❌"
        published_emoji = "📤" if product.publish_status == ProductPublishStatus.PUBLISHED else "⏳"
        price = f"{int(product.price):,}"

        # نوع محصول
        category_display = subcategory_names.get(
            product.sub_category_key,
            "نامشخص"
        )

        text += (
            f"{i}. {status_emoji} {published_emoji} {product.product_name}\n"
            f"    📁 {category_display}\n"
            f"    💰 {price} ت | 📦 {product.stock_qty} | 🔖 {product.sku}\n\n"
        )

    # دکمه‌های هر محصول - با نوع محصول
    keyboard = []
    for product in page_products:
        category = subcategory_names.get(product.sub_category_key, "")

        # ساخت متن دکمه بدون قطع کردن اجباری
        if category:
            button_text = f"{category} - {product.product_name}"
        else:
            button_text = f"👁 {product.product_name}"

        # فقط اگه واقعاً طولانی بود، محدود کن (تلگرام حداکثر ~۶۴ کاراکتر)
        if len(button_text) > 64:
            button_text = button_text[:61] + "..."

        keyboard.append([
            InlineKeyboardButton(
                button_text,
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

    await _show_product_detail(query, product_id, user.id)


async def _show_product_detail(query, product_id: int, telegram_user_id: int) -> None:
    """نمایش جزئیات محصول (helper - برای reuse)"""

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, telegram_user_id)
        if not customer:
            return

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

        # چک عکس‌های آپلود شده
        from app.services.product_media_service import get_product_medias, count_product_medias
        uploaded_medias = await get_product_medias(session, product_id, Platform.TELEGRAM)
        media_count = len(uploaded_medias)

        # چک اشتراک
        subscription = await get_active_subscription(session, customer.id)
        can_use_ai = subscription is not None

    status = "✅ موجود" if product.is_available else "❌ ناموجود"
    published = "📤 منتشر شده" if product.publish_status == ProductPublishStatus.PUBLISHED else "⏳ منتشر نشده"

    # وضعیت عکس
    if media_count > 0:
        image_status = f"🖼 {media_count} عکس آپلود شده ✅"
    elif product.image_url and product.image_url.strip():
        image_status = "🔗 عکس از لینک ✅"
    else:
        image_status = "❌ بدون عکس"

    text = (
        f"📦 جزئیات محصول\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🖥 نام: {product.product_name}\n"
        f"🔖 کد: {product.sku}\n"
        f"💰 قیمت: {int(product.price):,} تومان\n"
        f"📦 موجودی: {product.stock_qty} عدد\n"
        f"🚦 وضعیت: {status}\n"
        f"📡 انتشار: {published}\n"
        f"🖼 عکس: {image_status}\n"
    )

    if product.specs:
        text += f"\n📋 مشخصات:\n"
        for key, value in product.specs.items():
            text += f"├── {key}: {value}\n"

    if product.description_manual:
        text += f"\n📝 توضیحات:\n{product.description_manual}\n"

    keyboard = [
        [InlineKeyboardButton("👁 پیش‌نمایش پست", callback_data=f"prod_preview_{product.id}")],
        [InlineKeyboardButton("📤 ارسال به کانال", callback_data=f"prod_publish_{product.id}")],
    ]

    if can_use_ai:
        keyboard.append([
            InlineKeyboardButton("🤖 تولید توضیحات با AI", callback_data=f"ai_start_{product.id}")
        ])

    # دکمه‌های عکس
    if media_count > 0:
        keyboard.append([
            InlineKeyboardButton(
                "🖼 تغییر عکس آپلود شده",
                callback_data=f"prod_upload_image_{product.id}"
            )
        ])
        keyboard.append([
            InlineKeyboardButton(
                "❌ حذف عکس آپلود شده",
                callback_data=f"prod_remove_image_{product.id}"
            )
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(
                "🖼 آپلود عکس محصول",
                callback_data=f"prod_upload_image_{product.id}"
            )
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
            result = await session.execute(
                select(Product).where(Product.id == product_id)
            )
            p = result.scalar_one_or_none()
            if p:
                p.publish_status = ProductPublishStatus.PUBLISHED
                await session.commit()


async def _publish_or_edit(bot, product, channel, caption):
    """
    اگه محصول قبلاً در این کانال پست شده → ویرایش کپشن
    اگه نه → ارسال جدید (تک عکس یا آلبوم)

    از عکس‌های آپلود شده (اگه هست) استفاده می‌کنه، وگرنه از image_url
    """
    from app.services.product_media_service import (
        get_product_medias,
        get_photo_sources_for_platform,
    )
    from app.services.publisher.telegram_publisher import (
        publish_media_group_to_telegram,
    )

    async with AsyncSessionLocal() as session:
        # چک قبلاً پست شده
        existing = await get_posted_message(session, product.id, channel.id)

        # گرفتن عکس‌ها (اولویت با آپلود شده)
        uploaded_medias = await get_product_medias(session, product.id, Platform.TELEGRAM)
        photo_sources = get_photo_sources_for_platform(product, uploaded_medias)

    # ═══════════════════════════════════════════
    # حالت ۱: قبلاً پست شده → ویرایش کپشن
    # ═══════════════════════════════════════════
    if existing and existing.telegram_message_id:
        has_photo = bool(photo_sources)
        result = await edit_post_in_telegram(
            bot=bot,
            channel_identifier=channel.channel_identifier,
            message_id=existing.telegram_message_id,
            new_caption=caption,
            has_photo=has_photo,
        )

        if result.success:
            async with AsyncSessionLocal() as session:
                posted_fresh = await get_posted_message(session, product.id, channel.id)
                if posted_fresh:
                    await update_posted_message(
                        session=session,
                        posted_message=posted_fresh,
                        new_caption=caption,
                        new_price=int(product.price),
                        new_stock_qty=product.stock_qty,
                    )
        return result

    # ═══════════════════════════════════════════
    # حالت ۲: پست جدید
    # ═══════════════════════════════════════════

    # اگه چند عکس هست → آلبوم
    if len(photo_sources) > 1:
        result = await publish_media_group_to_telegram(
            bot=bot,
            channel_identifier=channel.channel_identifier,
            caption=caption,
            photo_sources=photo_sources,
        )
    # اگه یه عکس یا بدون عکس
    else:
        photo_url = photo_sources[0] if photo_sources else None
        result = await publish_post_to_telegram(
            bot=bot,
            channel_identifier=channel.channel_identifier,
            caption=caption,
            photo_url=photo_url,
        )

    # ذخیره در دیتابیس (برای هر دو حالت)
    if result.success and result.message_id:
        async with AsyncSessionLocal() as session:
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