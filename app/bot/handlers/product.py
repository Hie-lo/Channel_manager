"""
هندلرهای مدیریت محصولات
شامل: نمایش لیست، پیش‌نمایش پست، ارسال دستی به کانال
"""
from datetime import datetime
from requests import session
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
from app.services.product_media_service import (
        get_product_medias,
        count_all_product_medias,
        get_all_product_medias,
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
    get_product_medias,
    get_photo_sources_for_platform,
    count_product_medias,
)
from app.utils.security import is_rate_limited
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

 # 💡 مرتب‌سازی هوشمند مطابق با صف انتشار ربات:
    # ۱. ابتدا محصولات PENDING دقیقاً به ترتیبی که قرار است پست شوند (قدیمی‌ترها اول - FIFO)
    # ۲. سپس محصولات PUBLISHED در انتهای لیست
    products.sort(key=lambda p: (
        p.publish_status == ProductPublishStatus.PUBLISHED,  # False (0) قبل از True (1) می‌آید
        p.created_at or datetime.min                         # صعودی بر اساس زمان ساخت
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
        all_medias = await get_all_product_medias(session, product_id)
        media_count = len(all_medias)

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

    if product.description_custom:
        text += f"\n📝 توضیحات:\n{product.description_custom}\n"
    
    # نمایش توضیحات AI اگر وجود داشته باشد
    if product.ai_description or product.ai_pros or product.ai_cons:
        text += f"\n🤖 توضیحات AI ذخیره شده ✅\n"

    keyboard = [
        [InlineKeyboardButton("👁 پیش‌نمایش پست", callback_data=f"prod_preview_{product.id}")],
        [InlineKeyboardButton("📤 ارسال به کانال", callback_data=f"prod_publish_{product.id}")],
    ]

    if can_use_ai:
        keyboard.append([
            InlineKeyboardButton("🤖 تولید توضیحات با AI", callback_data=f"ai_start_{product.id}")
        ])
    
    # دکمه ویرایش توضیحات AI (اگر قبلاً ذخیره شده باشد)
    if product.ai_description or product.ai_pros or product.ai_cons:
        keyboard.append([
            InlineKeyboardButton("✏️ ویرایش توضیحات AI", callback_data=f"ai_edit_saved_{product.id}")
        ])

    # دکمه‌های عکس
    if media_count > 0:
        keyboard.append([
            InlineKeyboardButton(
                f"🖼 مدیریت عکس‌ها ({media_count})",
                callback_data=f"prod_upload_image_{product.id}"
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
    """پیش‌نمایش پست به همراه عکس‌ها (آلبوم یا تک عکس)"""
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
        
        # گرفتن عکس‌ها بر اساس پلتفرم فعلی کاربر
        from app.utils.admin_check import detect_platform_from_context
        from app.services.product_media_service import get_product_medias, get_photo_sources_for_platform
        current_platform_str = detect_platform_from_context(context)
        media_platform = Platform.BALE if current_platform_str == "BALE" else Platform.TELEGRAM
        
        medias = await get_product_medias(session, product.id, media_platform)
        photo_sources = get_photo_sources_for_platform(product, medias)

        from app.services.post_preset_service import get_selected_preset
        selected_preset = await get_selected_preset(session, customer.id)

    preset_text = selected_preset.template_text if selected_preset else None
    caption = build_post_caption(product, business_config, business, preset_template_text=preset_text)

    # کوتاه کردن کپشن برای پیش‌نمایش اگر خیلی طولانی بود
    max_cap_len = 1024 if photo_sources else 4000
    if len(caption) > max_cap_len:
        caption = caption[:max_cap_len-3] + "..."

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 ارسال به کانال", callback_data=f"prod_publish_{product.id}")],
        [InlineKeyboardButton("🔙 بازگشت به محصول", callback_data=f"prod_view_{product.id}")],
    ])

    try:
        # حذف پیام فعلی برای ارسال یک پیام عکس‌دار تمیز
        await query.message.delete()
    except Exception:
        pass

    try:
        if not photo_sources:
            # حالت متنی
            await context.bot.send_message(
                chat_id=user.id,
                text=f"👁 <b>پیش‌نمایش پست:</b>\n━━━━━━━━━━━━━━━\n\n{caption}",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        elif len(photo_sources) == 1:
            # حالت تک عکس
            await context.bot.send_photo(
                chat_id=user.id,
                photo=photo_sources[0],
                caption=caption,
                reply_markup=keyboard
            )
        else:
            # حالت آلبوم (چند عکس)
            from telegram import InputMediaPhoto
            media_group = []
            for i, source in enumerate(photo_sources[:10]):
                if i == 0:
                    media_group.append(InputMediaPhoto(media=source, caption=caption))
                else:
                    media_group.append(InputMediaPhoto(media=source))
            
            # ارسال آلبوم
            await context.bot.send_media_group(chat_id=user.id, media=media_group)
            
            # چون روی آلبوم نمیشه کیبورد شیشه‌ای گذاشت، یه پیام متنی جدا می‌فرستیم
            await context.bot.send_message(
                chat_id=user.id,
                text="👆 <b>پیش‌نمایش آلبوم شما</b>\nجهت تایید یا انصراف از دکمه‌های زیر استفاده کنید:",
                parse_mode="HTML",
                reply_markup=keyboard
            )
    except Exception as e:
        log.error(f"خطا در پیش‌نمایش عکس: {e}", exc_info=True)
        # Fallback به حالت متنی در صورت خرابی عکس
        await context.bot.send_message(
            chat_id=user.id,
            text=f"⚠️ عکس‌ها برای پیش‌نمایش بارگیری نشدند.\n\n👁 <b>پیش‌نمایش متن:</b>\n━━━━━━━━━━━━━━━\n\n{caption}",
            parse_mode="HTML",
            reply_markup=keyboard
        )


async def prod_publish_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ارسال دستی پست به کانال"""

    query = update.callback_query
    await query.answer()

    product_id = int(query.data.replace("prod_publish_", ""))
    user = query.from_user
    if is_rate_limited(user.id, "publish_post", max_requests=5, time_window_seconds=60):
        await query.answer("⚠️ لطفاً آرام‌تر! برای جلوگیری از بلاک شدن کانال، ۱ دقیقه صبر کنید.", show_alert=True)
        return
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

        from app.services.post_preset_service import get_selected_preset
        selected_preset = await get_selected_preset(session, customer.id)

    # نمایش پیام "در حال ارسال"
    await query.edit_message_text("⏳ در حال ارسال به کانال‌ها...")

    # ساخت کپشن
    preset_text = selected_preset.template_text if selected_preset else None
    caption = build_post_caption(product, business_config, business, preset_template_text=preset_text)

    # 🚀 ارسال موازی به تمامی کانال‌ها
    import asyncio
    
    # 1. ساخت تسک‌ها برای هر کانال (برای پشتیبانی از ادیت یا پست جدید)
    tasks = []
    for channel in channels:
        task = _publish_or_edit(
            bot=context.bot,
            product=product,
            channel=channel,
            caption=caption,
        )
        tasks.append(task)
        
    # 2. اجرای همزمان تمامی تسک‌ها
    parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 3. تطبیق نتایج با کانال‌ها
    results = []
    for idx, res in enumerate(parallel_results):
        channel = channels[idx]
        if isinstance(res, Exception):
            from app.services.publisher.telegram_publisher import PublishResult
            log.error(f"❌ خطا در تسک موازی برای کانال {channel.channel_identifier}: {res}")
            results.append((channel, PublishResult(success=False, error_message="خطای بحرانی سیستمی")))
        else:
            results.append((channel, res))

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
    # ارسال منوی محصول به صورت پیام جدید برای دسترسی راحت‌تر
    if success_count > 0:
        try:
            from app.bot.handlers.product_image import _send_product_menu_message
            await _send_product_menu_message(context, user.id, product_id)
        except Exception as e:
            log.warning(f"خطا در ارسال منوی محصول: {e}")

async def _publish_or_edit(bot, product, channel, caption):
    """
    اگه محصول قبلاً در این کانال پست شده → ویرایش
    اگه نه → ارسال جدید

    پشتیبانی از تلگرام، بله و ایتا
    """
    from app.services.publisher.publisher_manager import (
        publish_to_channel,
        edit_channel_post,
    )
    from app.database.models import Platform

    # ─── گرفتن داده‌های قبلی ───
    async with AsyncSessionLocal() as session:
        # چک قبلاً پست شده
        existing = await get_posted_message(session, product.id, channel.id)
        
        # کپی کردن مقادیر مهم (برای جلوگیری از مشکل detached object)
        if existing:
            existing_data = {
                "id": existing.id,
                "telegram_message_id": existing.telegram_message_id,
                "telegram_message_ids": list(existing.telegram_message_ids or []),
                "last_caption": existing.last_caption,
                "last_price": existing.last_price,
                "last_stock_qty": existing.last_stock_qty,
                "last_media_hash": existing.last_media_hash or "",
            }
        else:
            existing_data = None

        # گرفتن توکن ایتا (اگه کانال ایتاست)
        eitaa_token = None
        if channel.platform == Platform.EITAA:
            from app.services.customer_service import get_customer_eitaa_token
            from app.database.models import Customer
            customer_result = await session.execute(
                select(Customer).where(Customer.id == channel.customer_id)
            )
            customer = customer_result.scalar_one_or_none()

            if customer:
                eitaa_token = await get_customer_eitaa_token(session, customer.id)

    # ─── حالت ویرایش ───
    if existing_data and existing_data["telegram_message_id"]:
        # محاسبه hash عکس فعلی
        from app.services.media_hash import calculate_media_hash
        current_media_hash = await calculate_media_hash(product, channel.platform)
        
        # بررسی تغییرات (از existing_data استفاده می‌کنیم)
        current_price = int(product.price) if product.price else 0
        current_stock_qty = product.stock_qty or 0
        
        caption_changed = existing_data["last_caption"] != caption
        price_changed = int(existing_data["last_price"] or 0) != current_price
        stock_changed = (existing_data["last_stock_qty"] or 0) != current_stock_qty
        media_changed = existing_data["last_media_hash"] != current_media_hash
        
        # 🔍 DEBUG LOG
        log.info(
            f"[Publish Debug] محصول {product.id} در کانال {channel.channel_identifier} ({channel.platform.value}):\n"
            f"  caption_changed={caption_changed}\n"
            f"  price_changed={price_changed}\n"
            f"  stock_changed={stock_changed}\n"
            f"  media_changed={media_changed}\n"
            f"  telegram_message_id={existing_data['telegram_message_id']}"
        )
        
        # اگه هیچ تغییری نکرده، هیچ کاری نکن
        if not any([caption_changed, price_changed, stock_changed, media_changed]):
            from app.services.publisher.telegram_publisher import PublishResult
            log.info(
                f"[Publish] محصول {product.id} در {channel.channel_identifier} "
                "بدون تغییر است؛ عملیات ارسال/ادیت انجام نشد"
            )
            return PublishResult(
                success=True,
                message_id=existing_data["telegram_message_id"],
            )
        
        # تصمیم‌گیری: delete+repost یا edit؟
        # - ایتا: همیشه delete+repost (API edit نداره)
        # - بله/تلگرام: اگه media تغییر کرد → delete+repost | وگرنه → edit
        needs_repost = (
            (channel.platform == Platform.EITAA) or  # ایتا همیشه repost
            media_changed  # هر پلتفرمی که media تغییر کرده
        )
        
        if needs_repost:
            log.info(
                f"[Publish] محصول {product.id} نیاز به repost دارد؛ "
                f"(media_changed={media_changed}, platform={channel.platform.value}) "
                f"حذف و ارسال مجدد در {channel.channel_identifier}"
            )
            
            # حذف پست قبلی
            try:
                if channel.platform == Platform.BALE:
                    from app.config import settings
                    from telegram import Bot
                    
                    bale_bot = Bot(
                        token=settings.BALE_BOT_TOKEN,
                        base_url=settings.BALE_API_BASE,
                        base_file_url=settings.BALE_FILE_API_BASE,
                    )
                    await bale_bot.initialize()
                    
                    try:
                        # حذف پست(های) قبلی
                        if existing_data["telegram_message_ids"] and len(existing_data["telegram_message_ids"]) > 1:
                            # آلبوم - حذف همه پیام‌ها
                            for msg_id in existing_data["telegram_message_ids"]:
                                try:
                                    await bale_bot.delete_message(
                                        chat_id=channel.channel_identifier,
                                        message_id=msg_id
                                    )
                                except Exception as e:
                                    log.warning(f"خطا در حذف پیام {msg_id}: {e}")
                        else:
                            # تک عکس
                            await bale_bot.delete_message(
                                chat_id=channel.channel_identifier,
                                message_id=existing_data["telegram_message_id"]
                            )
                    finally:
                        await bale_bot.shutdown()
                        
                elif channel.platform == Platform.EITAA:
                    # برای ایتا از همان روش موجود استفاده می‌کنیم
                    pass
                    
            except Exception as e:
                log.warning(f"[Publish] خطا در حذف پست قبلی: {e}")
            
            # حذف رکورد قدیمی
            async with AsyncSessionLocal() as session:
                existing_to_delete = await get_posted_message(session, product.id, channel.id)
                if existing_to_delete:
                    await session.delete(existing_to_delete)
                    await session.commit()
            
            # ارسال جدید
            repost_result = await publish_to_channel(
                bot=bot,
                channel=channel,
                product=product,
                caption=caption,
                eitaa_token=eitaa_token,
            )
            
            # ذخیره پست جدید
            if repost_result.success and repost_result.message_id:
                async with AsyncSessionLocal() as session:
                    await create_posted_message(
                        session=session,
                        product_id=product.id,
                        channel_id=channel.id,
                        telegram_message_id=repost_result.message_id,
                        caption=caption,
                        price=int(product.price),
                        stock_qty=product.stock_qty,
                        media_hash=current_media_hash,
                    )
                    
                    # ذخیره message_ids آلبوم
                    if repost_result.message_ids and len(repost_result.message_ids) > 1:
                        posted = await get_posted_message(session, product.id, channel.id)
                        if posted:
                            posted.telegram_message_ids = repost_result.message_ids
                            await session.commit()
            
            from app.services.publisher.telegram_publisher import PublishResult
            return PublishResult(
                success=repost_result.success,
                message_id=repost_result.message_id,
                error_message=repost_result.error_message,
            )
        
        # اگه فقط caption تغییر کرده، ویرایش کن
        result = await edit_channel_post(
            bot=bot,
            channel=channel,
            product=product,
            new_caption=caption,
            old_message_id=existing_data["telegram_message_id"],
            eitaa_token=eitaa_token,
        )

        # اگه ویرایش موفق بود
        if result.success:
            # برای ایتا: message_id عوض میشه (delete + repost)
            # برای تلگرام/بله: message_id همون قبلی می‌مونه
            new_msg_id = result.message_id if result.message_id else existing_data["telegram_message_id"]

            async with AsyncSessionLocal() as session:
                posted_fresh = await get_posted_message(session, product.id, channel.id)
                if posted_fresh:
                    # محاسبه hash عکس جدید (اگه عکس عوض نشده همون قبلی میمونه)
                    new_media_hash = await calculate_media_hash(product, channel.platform) if media_changed else posted_fresh.last_media_hash
                    
                    # آپدیت message_id (برای ایتا حتماً عوض شده)
                    posted_fresh.telegram_message_id = new_msg_id
                    await update_posted_message(
                        session=session,
                        posted_message=posted_fresh,
                        new_caption=caption,
                        new_price=int(product.price),
                        new_stock_qty=product.stock_qty,
                        new_media_hash=new_media_hash,
                    )

        # تبدیل UnifiedPublishResult به فرمت سازگار
        from app.services.publisher.telegram_publisher import PublishResult
        return PublishResult(
            success=result.success,
            message_id=result.message_id,
            error_message=result.error_message,
            used_fallback=result.used_fallback,
        )

    # ─── حالت ارسال جدید ───
    result = await publish_to_channel(
        bot=bot,
        channel=channel,
        product=product,
        caption=caption,
        eitaa_token=eitaa_token,
    )

    # ذخیره در دیتابیس
    if result.success and result.message_id:
        async with AsyncSessionLocal() as session:
            posted = await create_posted_message(
                session=session,
                product_id=product.id,
                channel_id=channel.id,
                telegram_message_id=result.message_id,
                caption=caption,
                price=int(product.price),
                stock_qty=product.stock_qty,
            )

            # ذخیره message_ids آلبوم
            all_ids = getattr(result, 'message_ids', [])
            if all_ids and len(all_ids) > 1 and posted:
                posted.telegram_message_ids = all_ids
                await session.commit()

    # تبدیل UnifiedPublishResult به PublishResult سازگار
    from app.services.publisher.telegram_publisher import PublishResult
    return PublishResult(
        success=result.success,
        message_id=result.message_id,
        error_message=result.error_message,
        used_fallback=result.used_fallback,
    )
