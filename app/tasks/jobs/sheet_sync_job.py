"""
Job همگام‌سازی خودکار Google Sheet
(نسخه بهینه‌شده با قابلیت پردازش موازی و مدیریت Rate Limit)
"""

import asyncio
import random
from typing import List, Dict, Any, Optional

from telegram import Bot
from sqlalchemy import select

from app.database.connection import AsyncSessionLocal
from app.database.models import (
    Customer,
    CustomerStatus,
    Platform,
    Product,
    ProductPublishStatus,
    PostedMessage,
)
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
from app.services.publisher.publisher_manager import edit_channel_post
from app.services.publisher.posted_message_service import (
    get_posted_message,
    update_posted_message,
)
from app.utils.logger import log


# ═══════════════════════════════════════════════════════════════
# تنظیمات محدودیت نرخ و همزمانی به ازای هر پلتفرم
# ═══════════════════════════════════════════════════════════════

PLATFORM_CONFIG = {
    Platform.TELEGRAM: {
        "max_concurrent": 10,  # تعداد درخواست‌های همزمان
        "base_delay": 0.3,  # تأخیر پایه بین درخواست‌ها (ثانیه)
        "retry_delay": 2.0,  # تأخیر در صورت خطای Rate Limit
        "max_retries": 3,
    },
    Platform.BALE: {
        "max_concurrent": 8,
        "base_delay": 0.5,
        "retry_delay": 3.0,
        "max_retries": 3,
    },
    Platform.EITAA: {
        "max_concurrent": 3,  # ایتا محدودیت بیشتری دارد
        "base_delay": 1.5,  # چون delete + send انجام می‌دهد
        "retry_delay": 5.0,
        "max_retries": 5,
    },
}


# ═══════════════════════════════════════════════════════════════
# توابع اصلی Job (بدون تغییر)
# ═══════════════════════════════════════════════════════════════

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
                    # ۱. sync شیت
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
                        continue

                    # ۲. ادیت پست‌های معلق (اگه از قبل sync دستی شده ولی پست‌ها ادیت نشدن)
                    pending_result = await apply_pending_post_edits(
                        bot, conn.customer_id
                    )
                    pending_edited = pending_result.get("edited_count", 0)

                    # ۳. جمع‌بندی
                    stats["success_count"] += 1
                    new_count = sync_result.get("new_count", 0)
                    updated_count = sync_result.get("updated_count", 0)
                    edited_count = sync_result.get("edited_posts_count", 0) + pending_edited

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
    edit_posts_now: bool = True,
    is_manual: bool = False,  # 💡 پرچم همگام‌سازی دستی/اولیه
    custom_maps: dict = None,
    ignored_fields: list = None,
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
        "pending_edits_count": 0,
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
        custom_map=custom_maps,
        ignored_fields=ignored_fields,
    )

    if sheet_data.has_errors:
        mapping_errors = [
            err
            for err in sheet_data.all_errors
            if getattr(err, "error_type", "") == "missing_column"
        ]
        validation_errors = [
            err
            for err in sheet_data.all_errors
            if getattr(err, "error_type", "") != "missing_column"
        ]

        if mapping_errors and (is_manual or edit_posts_now is False):
            return {
                "requires_mapping_wizard": True,
                "missing_fields": sheet_data.missing_mapping_fields,
                "headers": sheet_data.headers,
                "sheet_id": connection.sheet_id,
            }

        if mapping_errors:
            error_msg = f"خطا در خواندن شیت: {mapping_errors[0].message}"
            if edit_posts_now:
                async with AsyncSessionLocal() as session:
                    await update_sync_status(session, customer_id, False, error_msg)
            result["error"] = error_msg
            return result

        if validation_errors:
            result["skipped_rows"] = [
                f"ردیف {e.row_number} ({e.worksheet}): {e.message}"
                for e in validation_errors[:20]
            ]
            result["skipped_count"] = len(validation_errors)
            log.warning(
                f"[Sync Customer {customer_id}] {len(validation_errors)} ردیف "
                f"به‌خاطر داده‌ی ناقص/نامعتبر نادیده گرفته شدن"
            )

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
            result["price_changes"].append(
                {
                    "sku": sku,
                    "name": existing.product_name,
                    "old": detection.old_price,
                    "new": detection.new_price,
                    "product_id": existing.id,
                }
            )

        if detection.stock_changed:
            result["stock_changes"].append(
                {
                    "sku": sku,
                    "name": existing.product_name,
                    "old": detection.old_stock,
                    "new": detection.new_stock,
                    "product_id": existing.id,
                }
            )

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
        changed_product_ids = list(
            set(
                change["product_id"]
                for change in result["price_changes"] + result["stock_changes"]
            )
        )

        if edit_posts_now:
            edited_count = await _edit_published_posts(
                bot=bot,
                customer_id=customer_id,
                product_ids=changed_product_ids,
            )
            result["edited_posts_count"] = edited_count
        else:
            published_count = await _count_published_products(changed_product_ids)
            result["pending_edits_count"] = published_count

    # آپدیت وضعیت sync
    async with AsyncSessionLocal() as session:
        await update_sync_status(session, customer_id, True, None)

    return result


async def _count_published_products(product_ids: list[int]) -> int:
    """شمارش محصولاتی که publish شدن (نیاز به ادیت پست دارن)"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Product).where(
                Product.id.in_(product_ids),
                Product.publish_status == ProductPublishStatus.PUBLISHED,
            )
        )
        return len(list(result.scalars().all()))


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


# ═══════════════════════════════════════════════════════════════
# بخش بهینه‌شده: ویرایش موازی پست‌ها با مدیریت Rate Limit
# ═══════════════════════════════════════════════════════════════

async def _edit_published_posts(
    bot: Bot,
    customer_id: int,
    product_ids: List[int],
) -> int:
    """
    ویرایش پست‌های منتشر شده در همه کانال‌های مشتری
    به‌صورت موازی با محدودیت همزمانی و مدیریت هوشمند Rate Limit
    برای محصولاتی که در product_ids هستن
    """
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
        active_channels = [c for c in channels if c.activation_status == "ACTIVE"]

        if not active_channels:
            log.warning(f"[Edit Posts] مشتری {customer_id} کانال ACTIVE نداره")
            return 0

        # محصولات
        products_result = await session.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        products = list(products_result.scalars().all())

        if not products:
            log.info("[Edit Posts] هیچ محصولی برای ادیت یافت نشد")
            return 0

    log.info(
        f"[Edit Posts] شروع ادیت موازی: {len(products)} محصول، "
        f"{len(active_channels)} کانال"
    )

    # ── گروه‌بندی تسک‌ها بر اساس پلتفرم ──
    tasks_by_platform = {platform: [] for platform in Platform}
    eitaa_token = None

    for product in products:
        caption = build_post_caption(product, business_config, business)
        for channel in active_channels:
            platform = channel.platform

            # دریافت posted_message
            async with AsyncSessionLocal() as session:
                posted = await get_posted_message(session, product.id, channel.id)

            if not posted or not posted.telegram_message_id:
                log.info(
                    f"[Edit Posts] محصول {product.sku} در {platform.value}: "
                    f"{channel.channel_identifier} پست نشده، رد شد"
                )
                continue

            # اگر ایتا است، توکن را یک بار بگیریم
            if platform == Platform.EITAA and eitaa_token is None:
                async with AsyncSessionLocal() as session:
                    from app.services.customer_service import get_customer_eitaa_token

                    eitaa_token = await get_customer_eitaa_token(session, customer.id)

            tasks_by_platform[platform].append(
                {
                    "channel": channel,
                    "product": product,
                    "caption": caption,
                    "old_message_id": posted.telegram_message_id,
                    "posted_message": posted,
                    "eitaa_token": eitaa_token if platform == Platform.EITAA else None,
                }
            )

    total_tasks = sum(len(t) for t in tasks_by_platform.values())
    if total_tasks == 0:
        log.info("[Edit Posts] هیچ کاری برای ادیت وجود ندارد")
        return 0

    log.info(
        f"[Edit Posts] {total_tasks} تسک در {len([t for t in tasks_by_platform.values() if t])} پلتفرم"
    )

    # ── اجرای تسک‌های هر پلتفرم به‌صورت جداگانه با تنظیمات مخصوص ──
    all_success_count = 0
    for platform, tasks in tasks_by_platform.items():
        if not tasks:
            continue

        config = PLATFORM_CONFIG.get(platform)
        if not config:
            config = PLATFORM_CONFIG[Platform.TELEGRAM]  # fallback

        success_count = await _edit_tasks_with_retry(
            tasks=tasks,
            platform=platform,
            config=config,
            bot=bot,
        )
        all_success_count += success_count

    log.info(f"[Edit Posts] پایان: {all_success_count} پست از {total_tasks} با موفقیت ادیت شد")
    return all_success_count


async def _edit_tasks_with_retry(
    tasks: List[dict],
    platform: Platform,
    config: dict,
    bot: Bot,
) -> int:
    """
    اجرای تسک‌های یک پلتفرم با محدودیت همزمانی، Retry و Backoff.
    """
    semaphore = asyncio.Semaphore(config["max_concurrent"])
    success_count = 0

    async def _limited_edit(task_data: dict) -> bool:
        nonlocal success_count
        async with semaphore:
            # تأخیر پایه با کمی جیتر (random) برای جلوگیری از همزمانی دقیق
            base_delay = config["base_delay"] * (1 + random.uniform(0, 0.2))
            await asyncio.sleep(base_delay)

            # اجرا با Retry
            for attempt in range(config["max_retries"] + 1):
                try:
                    result = await _edit_single_post_with_fallback(
                        **task_data,
                        platform=platform,
                        bot=bot,
                    )
                    if result:
                        success_count += 1
                        return True
                    else:
                        # false برگرداند، خطای غیرقابل بازیابی (مثلاً پیام وجود ندارد)
                        return False
                except Exception as e:
                    error_msg = str(e).lower()
                    # تشخیص Rate Limit
                    if (
                        "rate limit" in error_msg
                        or "too many" in error_msg
                        or "429" in error_msg
                    ):
                        if attempt < config["max_retries"]:
                            # Backoff: تأخیر افزایشی
                            wait = config["retry_delay"] * (2 ** attempt) * (
                                1 + random.uniform(0, 0.3)
                            )
                            log.warning(
                                f"[Edit Posts] Rate Limit در {platform.value} - "
                                f"تلاش {attempt+1}/{config['max_retries']} - "
                                f"تأخیر {wait:.1f}s"
                            )
                            await asyncio.sleep(wait)
                            continue
                        else:
                            log.error(
                                f"[Edit Posts] Rate Limit در {platform.value} - "
                                f"بعد از {config['max_retries']} تلاش شکست خورد"
                            )
                            return False
                    else:
                        # خطای دیگر
                        log.error(
                            f"[Edit Posts] خطا در {platform.value}: {e}",
                            exc_info=True,
                        )
                        return False
            return False

    # اجرای همه تسک‌ها با gather و ادامه در صورت خطا
    results = await asyncio.gather(
        *[_limited_edit(task) for task in tasks],
        return_exceptions=True,
    )

    # success_count قبلاً به‌روز شده، اما برای اطمینان از صحت از results هم می‌توان استفاده کرد
    return success_count


async def _edit_single_post_with_fallback(
    channel,
    product,
    caption: str,
    old_message_id: int,
    posted_message,
    eitaa_token: Optional[str] = None,
    platform: Platform = None,
    bot: Bot = None,
) -> bool:
    """
    ویرایش یک پست با مدیریت سناریوی حذف ناموفق (پیام قبلاً حذف شده است).
    در صورت خطای حذف، پیام جدید ارسال می‌شود و message_id به‌روز می‌شود.
    """
    try:
        edit_result = await edit_channel_post(
            bot=bot,
            channel=channel,
            product=product,
            new_caption=caption,
            old_message_id=old_message_id,
            eitaa_token=eitaa_token,
        )

        if edit_result.success:
            # به‌روزرسانی posted_message
            async with AsyncSessionLocal() as session:
                # اگر پیام جدید ارسال شده باشد، message_id جدید در edit_result موجود است
                new_message_id = getattr(edit_result, "new_message_id", old_message_id)
                # شیء posted_message را به‌روز می‌کنیم (بدون کوئری اضافی)
                posted_message.telegram_message_id = new_message_id
                posted_message.last_caption = caption
                posted_message.last_price = int(product.price) if product.price else 0
                posted_message.last_stock_qty = product.stock_qty or 0
                session.add(posted_message)
                await session.commit()

            log.info(
                f"✅ [Edit Posts] {product.sku} در {channel.channel_identifier} "
                f"(پلتفرم {platform.value if platform else '?'}) ادیت شد"
            )
            return True
        else:
            log.warning(
                f"⚠️ [Edit Posts] ادیت {product.sku} در {channel.channel_identifier} "
                f"ناموفق: {edit_result.error_message}"
            )
            return False

    except Exception as e:
        log.error(
            f"❌ [Edit Posts] استثنا در {product.sku} - {channel.channel_identifier}: {e}",
            exc_info=True,
        )
        return False


# ═══════════════════════════════════════════════════════════════
# تابع apply_pending_post_edits (به‌روز شده با رویکرد جدید)
# ═══════════════════════════════════════════════════════════════

async def apply_pending_post_edits(bot: Bot, customer_id: int) -> dict:
    """
    ادیت پست‌های تلگرام برای محصولاتی که در دیتابیس تغییر کردن
    ولی هنوز پست تلگرامشون آپدیت نشده

    منطق: مقایسه product.price/stock_qty با posted_message.last_price/last_stock_qty
    """
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
                current_price = int(product.price) if product.price else 0
                last_price = int(pm.last_price) if pm.last_price is not None else None
                current_stock = product.stock_qty or 0
                last_stock = pm.last_stock_qty if pm.last_stock_qty is not None else -1

                if last_price is None or current_price != last_price or current_stock != last_stock:
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

    edited_count = await _edit_published_posts(
        bot=bot,
        customer_id=customer_id,
        product_ids=products_needing_edit,
    )

    return {"edited_count": edited_count}