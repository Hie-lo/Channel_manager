"""
Job همگام‌سازی خودکار Google Sheet
"""

from telegram import Bot
from sqlalchemy import select

from app.database.connection import AsyncSessionLocal
from app.database.models import Customer, CustomerStatus, ProductPublishStatus
from app.services.customer_service import get_customer_by_telegram_id
from app.services.subscription.service import get_active_subscription
from app.services.sheet_connection_service import (
    get_sheet_connection,
    get_all_active_sheet_connections,
    update_sync_status,
)
from app.services.data_input.sheet_reader import read_google_sheet
from app.services.subscription.plans import get_plan
from app.services.business_service import (
    get_business_config_for_customer,
    get_business_for_customer,
)
from app.services.product_service import (
    get_all_products_by_customer,
    save_products_from_excel,
    detect_product_changes,
)
from app.services.channel_service import get_customer_channels
from app.services.content.post_builder import build_post_caption
from app.services.publisher.telegram_publisher import edit_post_in_telegram
from app.services.publisher.posted_message_service import (
    get_posted_message,
    update_posted_message,
)
from app.utils.logger import log


async def run_sheet_sync_job(bot: Bot) -> dict:
    """
    Job اصلی: همگام‌سازی همه شیت‌های فعال
    این تابع هر X ساعت اجرا میشه (بر اساس business config)
    """
    log.info("🔄 [Sheet Sync Job] شروع...")

    stats = {
        "total_customers": 0,
        "success_count": 0,
        "failed_count": 0,
        "details": [],
    }

    try:
        async with AsyncSessionLocal() as session:
            connections = await get_all_active_sheet_connections(session)

            if not connections:
                log.info("[Sheet Sync Job] هیچ اتصال فعالی نیست")
                stats["message"] = "هیچ اتصال Google Sheet فعالی نیست"
                return stats

            stats["total_customers"] = len(connections)
            log.info(f"[Sheet Sync Job] بررسی {len(connections)} اتصال...")

            for conn in connections:
                try:
                    # sync با ادیت خودکار پست‌ها
                    sync_result = await sync_customer_sheet(
                        bot,
                        conn.customer_id,
                        edit_posts_now=True,
                    )

                    if sync_result.get("error"):
                        stats["failed_count"] += 1
                        stats["details"].append(
                            f"مشتری {conn.customer_id}: ❌ {sync_result['error'][:50]}"
                        )
                    else:
                        stats["success_count"] += 1
                        new_count = sync_result.get("new_count", 0)
                        updated_count = sync_result.get("updated_count", 0)
                        edited_count = sync_result.get("edited_posts_count", 0)

                        details = f"مشتری {conn.customer_id}: ✅"
                        if new_count > 0:
                            details += f" جدید={new_count}"
                        if updated_count > 0:
                            details += f" آپدیت={updated_count}"
                        if edited_count > 0:
                            details += f" ادیت‌پست={edited_count}"
                        if new_count == 0 and updated_count == 0 and edited_count == 0:
                            details += " بدون تغییر"

                        stats["details"].append(details)
                except Exception as e:
                    log.error(f"خطا در sync مشتری {conn.customer_id}: {e}", exc_info=True)
                    stats["failed_count"] += 1
                    stats["details"].append(
                        f"مشتری {conn.customer_id}: ❌ خطا: {str(e)[:50]}"
                    )

        log.info(
            f"✅ [Sheet Sync Job] پایان - "
            f"موفق: {stats['success_count']}, ناموفق: {stats['failed_count']}"
        )
        return stats

    except Exception as e:
        log.error(f"❌ [Sheet Sync Job] خطا: {e}", exc_info=True)
        stats["error"] = str(e)
        return stats


async def sync_customer_sheet(
    bot: Bot,
    customer_id: int,
    edit_posts_now: bool = True,   # ← جدید: اگه False، پست‌ها ادیت نمیشن
) -> dict:
    """
    همگام‌سازی شیت یک مشتری

    Args:
        edit_posts_now: اگه True، پست‌های تلگرام هم ادیت میشن
                       اگه False، فقط دیتابیس آپدیت میشه (پست‌ها بعداً ادیت میشن)
    """
    result = {
        "new_count": 0,
        "updated_count": 0,
        "unchanged_count": 0,
        "error_count": 0,
        "price_changes": [],
        "stock_changes": [],
        "edited_posts_count": 0,
        "pending_edits_count": 0,   # ← جدید: تعداد پست‌هایی که نیاز به ادیت دارن ولی نکردیم
    }

    async with AsyncSessionLocal() as session:
        customer_result = await session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = customer_result.scalar_one_or_none()

        if not customer or customer.customer_status != CustomerStatus.ACTIVE:
            result["error"] = "حساب مشتری فعال نیست"
            return result

        subscription = await get_active_subscription(session, customer.id)
        if not subscription:
            result["error"] = "اشتراک فعال ندارد"
            return result

        connection = await get_sheet_connection(session, customer.id)
        if not connection or not connection.is_active:
            result["error"] = "اتصال Google Sheet فعال نیست"
            return result

        business_config = get_business_config_for_customer(customer)
        business = await get_business_for_customer(session, customer.id)
        plan = get_plan(subscription.plan_key)

        existing_products = await get_all_products_by_customer(session, customer.id)
        existing_by_sku = {p.sku: p for p in existing_products}

    # خواندن شیت
    log.info(f"[Sync Customer {customer_id}] خواندن شیت...")
    sheet_data = read_google_sheet(
        sheet_id=connection.sheet_id,
        business_config=business_config,
        worksheet_name=connection.worksheet_name,
    )

    if sheet_data.is_empty and sheet_data.has_errors:
        first_error = sheet_data.all_errors[0] if sheet_data.all_errors else None
        error_msg = f"خطا در خواندن شیت: {first_error.message}" if first_error else "شیت خالی است"
        async with AsyncSessionLocal() as session:
            await update_sync_status(session, customer_id, False, error_msg)
        result["error"] = error_msg
        return result

    # تشخیص تغییرات
    for product_data in sheet_data.all_products:
        sku = product_data.get("sku")
        if not sku:
            continue

        existing = existing_by_sku.get(sku)
        if not existing:
            continue

        detection = detect_product_changes(existing, product_data)

        if detection.price_changed:
            result["price_changes"].append({
                "sku": sku,
                "name": existing.product_name,
                "old": detection.old_price,
                "new": detection.new_price,
                "product_id": existing.id,
            })

        if detection.stock_changed:
            result["stock_changes"].append({
                "sku": sku,
                "name": existing.product_name,
                "old": detection.old_stock,
                "new": detection.new_stock,
                "product_id": existing.id,
            })

    # ═══════════════════════════════════════
    # همیشه: ذخیره محصولات در دیتابیس
    # ═══════════════════════════════════════

    async with AsyncSessionLocal() as session:
        business_id = business.id if business else None

        save_result = await save_products_from_excel(
            session=session,
            customer_id=customer_id,
            business_id=business_id,
            products_data=sheet_data.all_products,
            max_products_limit=plan.max_products,
        )

        result["new_count"] = save_result.new_count
        result["updated_count"] = save_result.updated_count
        result["unchanged_count"] = save_result.unchanged_count
        result["error_count"] = save_result.error_count

    # ═══════════════════════════════════════
    # ادیت پست‌های موجود (فقط اگه edit_posts_now=True)
    # ═══════════════════════════════════════

    if result["price_changes"] or result["stock_changes"]:
        changed_product_ids = list(set(
            change["product_id"]
            for change in result["price_changes"] + result["stock_changes"]
        ))

        if edit_posts_now:
            # الان ادیت کن (Job خودکار)
            edited_count = await _edit_published_posts(
                bot=bot,
                customer_id=customer_id,
                product_ids=changed_product_ids,
            )
            result["edited_posts_count"] = edited_count
        else:
            # فقط شمارش کن که چند تا از این محصولات PUBLISHED هستن
            published_count = await _count_published_products(changed_product_ids)
            result["pending_edits_count"] = published_count

    # آپدیت وضعیت sync
    async with AsyncSessionLocal() as session:
        await update_sync_status(session, customer_id, True, None)

    return result


async def _count_published_products(product_ids: list[int]) -> int:
    """شمارش محصولاتی که publish شدن (نیاز به ادیت پست دارن)"""
    async with AsyncSessionLocal() as session:
        from app.database.models import Product, ProductPublishStatus
        result = await session.execute(
            select(Product).where(
                Product.id.in_(product_ids),
                Product.publish_status == ProductPublishStatus.PUBLISHED,
            )
        )
        return len(list(result.scalars().all()))


async def _edit_published_posts(
    bot: Bot,
    customer_id: int,
    product_ids: list[int],
) -> int:
    """
    ویرایش پست‌های منتشر شده در همه کانال‌های مشتری
    برای محصولاتی که در product_ids هستن
    """
    edited_count = 0

    async with AsyncSessionLocal() as session:
        # اطلاعات مشتری
        customer_result = await session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = customer_result.scalar_one_or_none()
        if not customer:
            log.warning(f"[Edit Posts] مشتری {customer_id} پیدا نشد")
            return 0

        business_config = get_business_config_for_customer(customer)
        business = await get_business_for_customer(session, customer.id)
        channels = await get_customer_channels(session, customer.id)

        if not channels:
            log.warning(f"[Edit Posts] مشتری {customer_id} کانال نداره")
            return 0

        # فقط کانال‌های ACTIVE
        active_channels = [c for c in channels if c.activation_status == "ACTIVE"]

        if not active_channels:
            log.warning(f"[Edit Posts] مشتری {customer_id} کانال ACTIVE نداره")
            return 0

        # محصولات
        from app.database.models import Product
        products_result = await session.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        products = list(products_result.scalars().all())

    log.info(
        f"[Edit Posts] شروع ادیت: {len(products)} محصول، "
        f"{len(active_channels)} کانال"
    )

    for product in products:
        # ساخت کپشن جدید
        caption = build_post_caption(product, business_config, business)

        for channel in active_channels:
            # پیدا کن پست قبلی
            async with AsyncSessionLocal() as session:
                posted = await get_posted_message(session, product.id, channel.id)

            if not posted or not posted.telegram_message_id:
                log.info(
                    f"[Edit Posts] محصول {product.sku} در کانال "
                    f"{channel.channel_identifier} پست نشده، رد شد"
                )
                continue

            # چک عکس داره یا نه
            from app.services.product_media_service import get_product_medias
            async with AsyncSessionLocal() as session:
                medias = await get_product_medias(session, product.id, channel.platform)
            has_photo = len(medias) > 0 or bool(product.image_url)

            # ادیت
            edit_result = await edit_post_in_telegram(
                bot=bot,
                channel_identifier=channel.channel_identifier,
                message_id=posted.telegram_message_id,
                new_caption=caption,
                has_photo=has_photo,
            )

            if edit_result.success:
                # آپدیت posted_message با مقادیر جدید
                async with AsyncSessionLocal() as session:
                    posted_fresh = await get_posted_message(
                        session, product.id, channel.id
                    )
                    if posted_fresh:
                        await update_posted_message(
                            session=session,
                            posted_message=posted_fresh,
                            new_caption=caption,
                            new_price=int(product.price),
                            new_stock_qty=product.stock_qty,
                        )
                edited_count += 1
                log.info(
                    f"✅ [Edit Posts] {product.sku} در "
                    f"{channel.channel_identifier} ادیت شد"
                )
            else:
                log.error(
                    f"❌ [Edit Posts] خطا در {product.sku} - "
                    f"{channel.channel_identifier}: {edit_result.error_message}"
                )

    log.info(f"[Edit Posts] پایان: {edited_count} پست ادیت شد")
    return edited_count


async def _send_sync_report(bot: Bot, telegram_user_id: int, result: dict) -> None:
    """ارسال گزارش تغییرات به مشتری"""
    try:
        text = "🔔 گزارش همگام‌سازی\n━━━━━━━━━━━━━━━\n"

        if result["new_count"] > 0:
            text += f"🆕 محصول جدید: {result['new_count']}\n"

        if result["price_changes"]:
            text += f"💰 تغییر قیمت: {len(result['price_changes'])} مورد\n"
            for change in result["price_changes"][:5]:
                arrow = "📈" if change["new"] > change["old"] else "📉"
                text += (
                    f"  {arrow} {change['name'][:30]}\n"
                    f"     {change['old']:,} → {change['new']:,}\n"
                )
            if len(result["price_changes"]) > 5:
                text += f"  ... و {len(result['price_changes']) - 5} مورد دیگر\n"

        if result["stock_changes"]:
            text += f"\n📦 تغییر موجودی: {len(result['stock_changes'])} مورد\n"
            for change in result["stock_changes"][:5]:
                status = "❌ ناموجود" if change["new"] == 0 else f"✅ {change['new']}"
                text += f"  • {change['name'][:30]}: {status}\n"
            if len(result["stock_changes"]) > 5:
                text += f"  ... و {len(result['stock_changes']) - 5} مورد دیگر\n"

        if result.get("edited_posts_count", 0) > 0:
            text += f"\n✏️ پست‌های ویرایش شده: {result['edited_posts_count']}\n"

        text += "━━━━━━━━━━━━━━━"

        await bot.send_message(chat_id=telegram_user_id, text=text)
    except Exception as e:
        log.error(f"خطا در ارسال گزارش sync: {e}")

async def apply_pending_post_edits(bot: Bot, customer_id: int) -> dict:
    """
    ادیت پست‌های تلگرام برای محصولاتی که در دیتابیس تغییر کردن
    ولی هنوز پست تلگرامشون آپدیت نشده

    منطق: مقایسه product.price/stock_qty با posted_message.last_price/last_stock_qty
    """
    from app.database.models import Product, ProductPublishStatus, PostedMessage
    from decimal import Decimal

    async with AsyncSessionLocal() as session:
        # همه محصولات PUBLISHED مشتری
        products_result = await session.execute(
            select(Product).where(
                Product.customer_id == customer_id,
                Product.publish_status == ProductPublishStatus.PUBLISHED,
            )
        )
        published_products = list(products_result.scalars().all())

        if not published_products:
            return {"edited_count": 0, "message": "محصول منتشر شده‌ای نیست"}

        # پیدا کن محصولاتی که نیاز به ادیت دارن
        products_needing_edit = []

        for product in published_products:
            # همه posted_messages این محصول
            posted_result = await session.execute(
                select(PostedMessage).where(PostedMessage.product_id == product.id)
            )
            posted_messages = list(posted_result.scalars().all())

            if not posted_messages:
                continue

            for pm in posted_messages:
                # قیمت فعلی محصول
                current_price = int(product.price) if product.price else 0

                # قیمت ذخیره شده در آخرین پست
                # اگه last_price None باشه، حتماً نیاز به ادیت داره
                if pm.last_price is None:
                    products_needing_edit.append(product.id)
                    log.info(
                        f"[Pending Edit] محصول {product.sku}: "
                        f"last_price=None، نیاز به ادیت"
                    )
                    break

                last_price = int(pm.last_price)

                # موجودی
                current_stock = product.stock_qty or 0
                last_stock = pm.last_stock_qty if pm.last_stock_qty is not None else -1

                if current_price != last_price or current_stock != last_stock:
                    products_needing_edit.append(product.id)
                    log.info(
                        f"[Pending Edit] محصول {product.sku}: "
                        f"قیمت {last_price} → {current_price}, "
                        f"موجودی {last_stock} → {current_stock}"
                    )
                    break

    if not products_needing_edit:
        return {"edited_count": 0, "message": "همه پست‌ها به‌روز هستن"}

    log.info(f"[Pending Edit] {len(products_needing_edit)} محصول نیاز به ادیت دارن")

    # ادیت
    edited_count = await _edit_published_posts(
        bot=bot,
        customer_id=customer_id,
        product_ids=products_needing_edit,
    )

    return {"edited_count": edited_count}