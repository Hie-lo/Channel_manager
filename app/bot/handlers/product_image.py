"""
هندلرهای آپلود و مدیریت عکس محصول (چند عکس)
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from sqlalchemy import select

from app.database.connection import AsyncSessionLocal
from app.database.models import Product, Platform, CustomerStatus, ProductPublishStatus
from app.services.customer_service import get_customer_by_telegram_id
from app.services.product_media_service import (
    add_product_media,
    remove_all_product_media,
    get_product_medias,
    count_product_medias,
    MAX_PHOTOS_PER_PRODUCT,
)
from app.bot.states.user_state import (
    UserState,
    set_user_state,
    get_user_state,
    get_user_data,
    clear_user_state,
)
from app.utils.logger import log


async def prod_upload_image_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    شروع فرآیند مدیریت عکس محصول
    اگه عکس داره: دو گزینه (جایگزین یا اضافه)
    اگه نداره: مستقیم آپلود
    """
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.replace("prod_upload_image_", ""))
    user = query.from_user

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer or customer.customer_status != CustomerStatus.ACTIVE:
            await query.answer("❌ حساب شما فعال نیست", show_alert=True)
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

        # شمارش عکس‌های فعلی
        current_count = await count_product_medias(session, product_id)

    # اگه عکسی نداره → مستقیم آپلود
    if current_count == 0:
        await _start_upload_mode(query, user.id, product_id, "add")
        return

    # اگه عکس داره → پرسیدن حالت
    text = (
        f"🖼 مدیریت عکس محصول\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📦 محصول: {product.product_name}\n"
        f"📷 عکس‌های فعلی: {current_count}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"چطور می‌خوای عکس‌ها رو مدیریت کنی؟\n\n"
        f"🔄 <b>جایگزین کردن</b>\n"
        f"همه عکس‌های قبلی پاک میشن و عکس‌های جدید جاشون میان\n\n"
        f"➕ <b>اضافه کردن</b>\n"
        f"عکس‌های جدید به آلبوم فعلی اضافه میشن"
    )

    keyboard = [
        [InlineKeyboardButton(
            "🔄 جایگزین همه عکس‌ها",
            callback_data=f"prod_img_replace_{product_id}"
        )],
        [InlineKeyboardButton(
            "➕ اضافه به عکس‌های موجود",
            callback_data=f"prod_img_add_{product_id}"
        )],
        [InlineKeyboardButton(
            "❌ انصراف",
            callback_data=f"prod_view_{product_id}"
        )],
    ]

    await query.edit_message_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def prod_img_replace_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """کاربر جایگزین کردن رو انتخاب کرد"""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.replace("prod_img_replace_", ""))
    user = query.from_user

    # پاک کردن عکس‌های قبلی
    async with AsyncSessionLocal() as session:
        count = await remove_all_product_media(session, product_id)

    log.info(f"🗑 [Replace Mode] {count} عکس محصول {product_id} پاک شد")

    await query.edit_message_text(
        f"🗑 {count} عکس قبلی حذف شد.\n\n"
        f"حالا عکس‌های جدید رو ارسال کنید..."
    )

    # کمی صبر که پیام نشون داده بشه
    import asyncio
    await asyncio.sleep(1)

    # حالا رفتن به حالت آپلود
    await _start_upload_mode(query, user.id, product_id, "replace")


async def prod_img_add_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """کاربر اضافه کردن رو انتخاب کرد"""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.replace("prod_img_add_", ""))
    user = query.from_user

    await _start_upload_mode(query, user.id, product_id, "add")


async def _start_upload_mode(query, telegram_user_id: int, product_id: int, mode: str) -> None:
    """
    شروع حالت آپلود عکس
    mode: "add" یا "replace"
    """
    async with AsyncSessionLocal() as session:
        current_count = await count_product_medias(session, product_id)

        # گرفتن نام محصول
        result = await session.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()

    remaining = MAX_PHOTOS_PER_PRODUCT - current_count

    if remaining <= 0:
        await query.edit_message_text(
            f"⚠️ به حداکثر تعداد عکس رسیدید ({MAX_PHOTOS_PER_PRODUCT})!\n"
            f"برای اضافه کردن عکس جدید، اول باید همه رو حذف کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data=f"prod_view_{product_id}")]
            ]),
        )
        return

    # تنظیم state با mode
    set_user_state(
        telegram_user_id,
        UserState.WAITING_PRODUCT_IMAGE,
        data={
            "product_id": product_id,
            "uploaded_count": 0,
            "mode": mode,  # "add" یا "replace"
        },
    )

    mode_text = "🔄 جایگزینی" if mode == "replace" else "➕ اضافه کردن"

    text = (
        f"🖼 آپلود عکس - {mode_text}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📦 محصول: {product.product_name if product else '?'}\n"
        f"📷 عکس‌های فعلی: {current_count}\n"
        f"➕ می‌تونی {remaining} عکس اضافه کنی\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"لطفاً عکس‌های محصول رو ارسال کنید.\n\n"
        f"💡 نکات:\n"
        f"• هر عکس رو جداگانه بفرستید\n"
        f"• عکس‌ها به ترتیب ارسال ذخیره میشن\n"
        f"• برای پایان، دکمه '✅ اتمام' رو بزنید"
    )

    keyboard = [
        [InlineKeyboardButton("✅ اتمام آپلود", callback_data=f"prod_finish_upload_{product_id}")],
        [InlineKeyboardButton("❌ انصراف", callback_data=f"prod_view_{product_id}")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def prod_finish_upload_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """پایان آپلود عکس‌ها + پرسیدن برای repost"""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.replace("prod_finish_upload_", ""))
    user = query.from_user

    user_data = get_user_data(user.id)
    uploaded_count = user_data.get("uploaded_count", 0)

    clear_user_state(user.id)

    async with AsyncSessionLocal() as session:
        total_count = await count_product_medias(session, product_id)

        result = await session.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()

        if not product:
            await query.edit_message_text("❌ محصول پیدا نشد!")
            return

        is_published = product.publish_status == ProductPublishStatus.PUBLISHED

    text = (
        f"✅ آپلود عکس تمام شد!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📷 عکس‌های اضافه شده: {uploaded_count}\n"
        f"📊 مجموع عکس‌ها: {total_count}\n"
        f"━━━━━━━━━━━━━━━\n\n"
    )

    if uploaded_count == 0:
        text += "هیچ عکسی اضافه نشد."
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت به محصول", callback_data=f"prod_view_{product_id}")]
            ]),
        )
        return

    if is_published:
        text += (
            f"⚠️ <b>این محصول قبلاً در کانال‌ها منتشر شده.</b>\n\n"
            f"می‌خوای پست‌های موجود رو با عکس‌های جدید دوباره بفرستم؟\n\n"
            f"⚠️ <b>نکته:</b>\n"
            f"• پست‌های قبلی از کانال حذف میشن\n"
            f"• پست‌های جدید ارسال میشن\n"
            f"• بازدید پست‌های قبلی از دست میره"
        )

        keyboard = [
            [InlineKeyboardButton(
                "✅ آره، دوباره بفرست",
                callback_data=f"prod_repost_{product_id}"
            )],
            [InlineKeyboardButton(
                "⏰ نه، فقط دیتابیس",
                callback_data=f"prod_view_{product_id}"
            )],
        ]

        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    else:
        text += (
            f"💡 این محصول هنوز در کانال منتشر نشده.\n"
            f"می‌تونی الان بفرستیش."
        )

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "📤 ارسال به کانال الان",
                    callback_data=f"prod_publish_{product_id}"
                )],
                [InlineKeyboardButton(
                    "👁 پیش‌نمایش پست",
                    callback_data=f"prod_preview_{product_id}"
                )],
                [InlineKeyboardButton(
                    "🔙 بازگشت به محصول",
                    callback_data=f"prod_view_{product_id}"
                )],
            ]),
        )


async def prod_remove_image_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """حذف همه عکس‌های آپلود شده"""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.replace("prod_remove_image_", ""))
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

        count = await remove_all_product_media(session, product_id)

    await query.answer(f"✅ {count} عکس حذف شد", show_alert=True)

    from app.bot.handlers.product import _show_product_detail
    await _show_product_detail(query, product_id, user.id)


async def product_image_received_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    دریافت عکس از مشتری برای محصول (چند عکس)
    """
    user = update.effective_user

    if get_user_state(user.id) != UserState.WAITING_PRODUCT_IMAGE:
        return

    user_data = get_user_data(user.id)
    product_id = user_data.get("product_id")

    if not product_id:
        await update.message.reply_text("❌ خطا! لطفاً از اول شروع کنید.")
        clear_user_state(user.id)
        return

    if not update.message.photo:
        await update.message.reply_text("⚠️ لطفاً عکس بفرستید.")
        return

    # گرفتن بزرگترین سایز
    photo = update.message.photo[-1]
    file_id = photo.file_id

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            await update.message.reply_text("❌ خطا!")
            clear_user_state(user.id)
            return

        result = await session.execute(
            select(Product).where(
                Product.id == product_id,
                Product.customer_id == customer.id,
            )
        )
        product = result.scalar_one_or_none()

        if not product:
            await update.message.reply_text("❌ محصول پیدا نشد!")
            clear_user_state(user.id)
            return

        # اضافه کردن عکس
        media = await add_product_media(
            session=session,
            product_id=product_id,
            file_id=file_id,
            platform=Platform.TELEGRAM,
            uploaded_by_customer=True,
        )

        if not media:
            await update.message.reply_text(
                f"⚠️ به حداکثر تعداد عکس ({MAX_PHOTOS_PER_PRODUCT}) رسیدید!\n"
                f"دکمه '✅ اتمام آپلود' رو بزنید."
            )
            return

        total_count = await count_product_medias(session, product_id)

    # آپدیت شمارش در state
    uploaded_count = user_data.get("uploaded_count", 0) + 1
    set_user_state(
        user.id,
        UserState.WAITING_PRODUCT_IMAGE,
        data={"product_id": product_id, "uploaded_count": uploaded_count},
    )

    remaining = MAX_PHOTOS_PER_PRODUCT - total_count

    if remaining > 0:
        response = (
            f"✅ عکس {uploaded_count} ذخیره شد!\n"
            f"📊 مجموع عکس‌ها: {total_count}/{MAX_PHOTOS_PER_PRODUCT}\n"
            f"➕ می‌تونید {remaining} عکس دیگه اضافه کنید.\n\n"
            f"عکس بعدی رو بفرستید یا دکمه '✅ اتمام آپلود' رو بزنید."
        )
    else:
        response = (
            f"✅ عکس {uploaded_count} ذخیره شد!\n"
            f"📊 به حداکثر تعداد رسیدید ({MAX_PHOTOS_PER_PRODUCT}).\n\n"
            f"دکمه '✅ اتمام آپلود' رو بزنید."
        )

    await update.message.reply_text(response)


async def prod_repost_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    دوباره ارسال پست با عکس‌های جدید
    ۱. حذف پست‌های قدیمی در همه کانال‌ها
    ۲. ارسال پست جدید در همه کانال‌ها
    """
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.replace("prod_repost_", ""))
    user = query.from_user

    await query.edit_message_text("⏳ در حال حذف پست‌های قدیمی و ارسال جدید...")

    from app.database.connection import AsyncSessionLocal
    from app.database.models import (
        Product,
        PostedMessage,
        ProductPublishStatus,
        Platform,
    )
    from app.services.customer_service import (
        get_customer_by_telegram_id,
        get_customer_eitaa_token,
    )
    from app.services.channel_service import get_customer_channels
    from app.services.business_service import (
        get_business_config_for_customer,
        get_business_for_customer,
    )
    from app.services.content.post_builder import build_post_caption
    from app.services.publisher.publisher_manager import publish_to_channel
    from app.services.publisher.posted_message_service import create_posted_message
    from sqlalchemy import select

    # ═══════════════════════════════════════════
    # مرحله ۱: پیدا کردن اطلاعات
    # ═══════════════════════════════════════════

    async with AsyncSessionLocal() as session:
        customer = await get_customer_by_telegram_id(session, user.id)
        if not customer:
            await query.edit_message_text("❌ خطا!")
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

        # همه پست‌های موجود این محصول
        posted_result = await session.execute(
            select(PostedMessage).where(PostedMessage.product_id == product_id)
        )
        posted_messages = list(posted_result.scalars().all())

        # همه کانال‌های ACTIVE مشتری
        channels = await get_customer_channels(session, customer.id, only_active=True)

        # توکن ایتا
        eitaa_token = None
        has_eitaa = any(ch.platform == Platform.EITAA for ch in channels)
        if has_eitaa:
            eitaa_token = await get_customer_eitaa_token(session, customer.id)

    if not channels:
        await query.edit_message_text("❌ کانالی متصل نیست!")
        return

    # ═══════════════════════════════════════════
    # مرحله ۲: حذف پست‌های قدیمی (با try/except قوی)
    # ═══════════════════════════════════════════

    log.info(f"🗑 [Repost] حذف پست‌های قدیمی محصول {product_id}")

    deleted_count = 0
    delete_errors = []

    for pm in posted_messages:
        # پیدا کن کانالش
        channel = next((c for c in channels if c.id == pm.channel_id), None)
        if not channel:
            log.warning(f"[Repost] کانال {pm.channel_id} پیدا نشد")
            continue

        # حذف پست
        try:
            if channel.platform == Platform.TELEGRAM:
                log.info(
                    f"[Repost] حذف پست تلگرام {pm.telegram_message_id} "
                    f"از {channel.channel_identifier}"
                )
                await context.bot.delete_message(
                    chat_id=channel.channel_identifier,
                    message_id=pm.telegram_message_id,
                )
                deleted_count += 1
                log.info(f"✅ [Repost] پست تلگرام {pm.telegram_message_id} حذف شد")

            elif channel.platform == Platform.EITAA:
                log.info(
                    f"[Repost] حذف پست ایتا {pm.telegram_message_id} "
                    f"از {channel.channel_identifier}"
                )
                if eitaa_token:
                    from app.services.publisher.eitaa_client import EitaaClient
                    client = EitaaClient(token=eitaa_token)
                    delete_result = await client.delete_message(
                        chat_id=channel.channel_identifier,
                        message_id=pm.telegram_message_id,
                    )
                    if delete_result.ok:
                        deleted_count += 1
                        log.info(f"✅ [Repost] پست ایتا {pm.telegram_message_id} حذف شد")
                    else:
                        log.warning(
                            f"⚠️ [Repost] حذف ایتا موفق نبود: "
                            f"{delete_result.error_message}"
                        )

        except Exception as e:
            log.warning(
                f"⚠️ [Repost] خطا در حذف پست {pm.telegram_message_id} "
                f"در {channel.platform.value}: {e}"
            )
            delete_errors.append(f"{channel.platform.value}: {str(e)[:50]}")
            # ⚠️ مهم: continue تا بقیه رو هم امتحان کنه
            continue

    log.info(f"🗑 [Repost] پایان حذف: {deleted_count} پست حذف شد")

    # ═══════════════════════════════════════════
    # مرحله ۳: پاک کردن رکوردهای PostedMessage از دیتابیس
    # ═══════════════════════════════════════════

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PostedMessage).where(PostedMessage.product_id == product_id)
        )
        pms = list(result.scalars().all())
        for pm in pms:
            await session.delete(pm)
        await session.commit()
        log.info(f"🗑 [Repost] {len(pms)} رکورد PostedMessage پاک شد")

    # ═══════════════════════════════════════════
    # مرحله ۴: کمی تاخیر (خصوصاً برای ایتا)
    # ═══════════════════════════════════════════

    import asyncio
    await asyncio.sleep(2)

    # ═══════════════════════════════════════════
    # مرحله ۵: ساخت کپشن جدید
    # ═══════════════════════════════════════════

    caption = build_post_caption(product, business_config, business)

    # ═══════════════════════════════════════════
    # مرحله ۶: ارسال پست‌های جدید
    # ═══════════════════════════════════════════

    log.info(f"📤 [Repost] ارسال پست‌های جدید محصول {product_id}")

    success_count = 0
    failed_count = 0
    results_list = []

    for channel in channels:
        try:
            log.info(
                f"[Repost] ارسال به {channel.platform.value}: "
                f"{channel.channel_identifier}"
            )

            result = await publish_to_channel(
                bot=context.bot,
                channel=channel,
                product=product,
                caption=caption,
                eitaa_token=eitaa_token,
            )

            if result.success and result.message_id:
                # ذخیره پست جدید
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
                success_count += 1
                results_list.append(
                    f"✅ {channel.platform.value}: {channel.channel_identifier}"
                )
                log.info(f"✅ [Repost] پست شد در {channel.channel_identifier}")
            else:
                failed_count += 1
                results_list.append(
                    f"❌ {channel.platform.value}: {channel.channel_identifier}\n"
                    f"    دلیل: {result.error_message}"
                )
                log.error(
                    f"❌ [Repost] ارسال fail: {channel.channel_identifier} - "
                    f"{result.error_message}"
                )

            # تاخیر کوچک بین ارسال‌ها
            await asyncio.sleep(1)

        except Exception as e:
            failed_count += 1
            log.error(
                f"❌ [Repost] خطا در ارسال به {channel.channel_identifier}: {e}",
                exc_info=True,
            )
            results_list.append(
                f"❌ {channel.platform.value}: {channel.channel_identifier}\n"
                f"    خطا: {str(e)[:50]}"
            )

    # ═══════════════════════════════════════════
    # مرحله ۷: نمایش نتیجه به کاربر
    # ═══════════════════════════════════════════

    text = (
        f"✅ عملیات کامل شد!\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🗑 پست‌های حذف شده: {deleted_count}\n"
        f"📤 پست‌های جدید: {success_count} موفق، {failed_count} ناموفق\n"
        f"━━━━━━━━━━━━━━━\n\n"
    )

    for r in results_list:
        text += f"{r}\n"

    if delete_errors:
        text += "\n⚠️ خطاهای حذف:\n"
        for err in delete_errors[:3]:
            text += f"• {err}\n"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت به محصول", callback_data=f"prod_view_{product_id}")]
        ]),
    )

    # ═══════════════════════════════════════════
    # مرحله ۸: ارسال منوی محصول به صورت پیام جدید
    # (چون edit_message_text نمی‌تونه Reply Keyboard بذاره)
    # ═══════════════════════════════════════════

    # این کار باعث میشه کاربر منوی محصول رو راحت‌تر ببینه
    # فقط اگه موفقیت‌آمیز بود
    if success_count > 0:
        try:
            await _send_product_menu_message(context, user.id, product_id)
        except Exception as e:
            log.warning(f"خطا در ارسال منوی محصول: {e}")


async def _send_product_menu_message(context, telegram_user_id: int, product_id: int) -> None:
    """
    ارسال یک پیام جدید با دکمه‌های اصلی محصول
    این پیام بعد از عملیات‌های طولانی به کاربر داده میشه که راحت به منو دسترسی داشته باشه
    """
    from app.database.models import Product, ProductPublishStatus, Platform
    from app.services.customer_service import get_customer_by_telegram_id
    from app.services.subscription.service import get_active_subscription
    from app.services.product_media_service import count_product_medias
    from sqlalchemy import select

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
            return

        media_count = await count_product_medias(session, product_id, Platform.TELEGRAM)
        subscription = await get_active_subscription(session, customer.id)
        can_use_ai = subscription is not None

    status = "✅ موجود" if product.is_available else "❌ ناموجود"
    published = "📤 منتشر شده" if product.publish_status == ProductPublishStatus.PUBLISHED else "⏳ منتشر نشده"

    if media_count > 0:
        image_status = f"🖼 {media_count} عکس آپلود شده ✅"
    elif product.image_url and product.image_url.strip():
        image_status = "🔗 عکس از لینک ✅"
    else:
        image_status = "❌ بدون عکس"

    text = (
        f"📦 <b>{product.product_name}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔖 {product.sku} | 💰 {int(product.price):,} ت\n"
        f"🚦 {status} | 📡 {published}\n"
        f"🖼 {image_status}\n"
        f"━━━━━━━━━━━━━━━"
    )

    keyboard = [
        [InlineKeyboardButton("👁 پیش‌نمایش پست", callback_data=f"prod_preview_{product.id}")],
        [InlineKeyboardButton("📤 ارسال به کانال", callback_data=f"prod_publish_{product.id}")],
    ]

    if can_use_ai:
        keyboard.append([
            InlineKeyboardButton("🤖 تولید توضیحات با AI", callback_data=f"ai_start_{product.id}")
        ])

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

    await context.bot.send_message(
        chat_id=telegram_user_id,
        text=text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )