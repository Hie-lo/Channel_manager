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
                    result = await sync_customer_sheet(bot, conn.customer_id)

                    if result.get("error"):
                        stats["failed_count"] += 1
                        stats["details"].append(
                            f"مشتری {conn.customer_id}: ❌ {result['error'][:50]}"
                        )
                    else:
                        stats["success_count"] += 1
                        changes = (
                            result.get("new_count", 0)
                            + result.get("updated_count", 0)
                        )
                        stats["details"].append(
                            f"مشتری {conn.customer_id}: ✅ {changes} تغییر"
                        )
                except Exception as e:
                    log.error(f"خطا در sync مشتری {conn.customer_id}: {e}")
                    stats["failed_count"] += 1

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
        changed_product_ids = set()
        for change in result["price_changes"] + result["stock_changes"]:
            changed_product_ids.add(change["product_id"])

        # شمارش پست‌های PUBLISHED (که نیاز به ادیت دارن)
        published_product_ids = await _count_published_products(
            list(changed_product_ids)
        )

        if edit_posts_now:
            # الان ادیت کن
            edited_count = await _edit_published_posts(
                bot=bot,
                customer_id=customer_id,
                product_ids=list(changed_product_ids),
            )
            result["edited_posts_count"] = edited_count
        else:
            # فقط شمارش کن، ادیت نکن
            result["pending_edits_count"] = published_product_ids

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
    """ویرایش پست‌های منتشر شده"""
    edited_count = 0

    async with AsyncSessionLocal() as session:
        customer_result = await session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = customer_result.scalar_one_or_none()
        if not customer:
            return 0

        business_config = get_business_config_for_customer(customer)
        business = await get_business_for_customer(session, customer.id)
        channels = await get_customer_channels(session, customer.id, only_active=True)

        from app.database.models import Product
        products_result = await session.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        products = list(products_result.scalars().all())

    for product in products:
        # فقط محصولات منتشر شده رو ویرایش کن
        if product.publish_status != ProductPublishStatus.PUBLISHED:
            continue

        caption = build_post_caption(product, business_config, business)

        for channel in channels:
            async with AsyncSessionLocal() as session:
                posted = await get_posted_message(session, product.id, channel.id)

            if not posted or not posted.telegram_message_id:
                continue

            has_photo = bool(product.image_url)

            edit_result = await edit_post_in_telegram(
                bot=bot,
                channel_identifier=channel.channel_identifier,
                message_id=posted.telegram_message_id,
                new_caption=caption,
                has_photo=has_photo,
            )

            if edit_result.success:
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
                edited_count += 1
                log.info(
                    f"✅ [Sync] پست ویرایش شد: "
                    f"{channel.channel_identifier} - {product.sku}"
                )
            else:
                log.error(
                    f"❌ [Sync] ویرایش ناموفق: "
                    f"{channel.channel_identifier} - {product.sku}: "
                    f"{edit_result.error_message}"
                )

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
    """
    async with AsyncSessionLocal() as session:
        # پیدا کن همه محصولاتی که PUBLISHED هستن
        from app.database.models import Product, ProductPublishStatus, PostedMessage
        products_result = await session.execute(
            select(Product).where(
                Product.customer_id == customer_id,
                Product.publish_status == ProductPublishStatus.PUBLISHED,
            )
        )
        published_products = list(products_result.scalars().all())

        if not published_products:
            return {"edited_count": 0, "message": "محصول منتشر شده‌ای نیست"}

        # چک کن کدوم‌هاشون قیمت/موجودی تغییر کرده نسبت به posted_messages
        products_needing_edit = []
        for product in published_products:
            posted_result = await session.execute(
                select(PostedMessage).where(PostedMessage.product_id == product.id)
            )
            posted_messages = list(posted_result.scalars().all())

            for pm in posted_messages:
                # اگه قیمت یا موجودی فرق داره، نیاز به ادیت
                price_changed = pm.last_price is not None and int(pm.last_price) != int(product.price)
                stock_changed = pm.last_stock_qty is not None and pm.last_stock_qty != product.stock_qty

                if price_changed or stock_changed:
                    products_needing_edit.append(product.id)
                    break

    if not products_needing_edit:
        return {"edited_count": 0, "message": "همه پست‌ها به‌روز هستن"}

    # ادیت
    edited_count = await _edit_published_posts(
        bot=bot,
        customer_id=customer_id,
        product_ids=products_needing_edit,
    )

    return {"edited_count": edited_count}