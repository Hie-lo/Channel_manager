"""
Job انتشار خودکار محصولات
هر X دقیقه اجرا میشه و برای هر مشتری چک می‌کنه که آیا وقت پست بعدی رسیده
"""

from telegram import Bot
from sqlalchemy import select
from app.config import settings
from app.services.posting_settings_service import get_posting_settings
from app.services.ai_token_service import (
    get_total_available_tokens,
    consume_tokens,
    refund_tokens,
)
from app.services.ai_usage_log_service import log_ai_usage
from app.services.ai.service import generate_product_description
from app.database.models import Product
from app.database.connection import AsyncSessionLocal
from app.database.models import Customer, CustomerStatus
from app.services.customer_service import get_customer_by_telegram_id
from app.services.posting_settings_service import (
    get_all_customers_with_auto_publish,
    is_in_posting_hours,
    is_time_for_next_post,
    update_last_post_time,
)
from app.services.subscription.service import get_active_subscription
from app.services.product_service import (
    get_next_pending_product,
    mark_product_as_published,
    mark_product_as_failed,
)
from app.services.channel_service import get_customer_channels
from app.services.business_service import (
    get_business_config_for_customer,
    get_business_for_customer,
)
from app.services.content.post_builder import build_post_caption
from app.services.publisher.telegram_publisher import publish_post_to_telegram
from app.services.publisher.posted_message_service import create_posted_message
from app.utils.logger import log
from app.utils.time import utc_now_naive
from app.database.models import Product, Platform
from app.services.product_media_service import (
    get_product_medias,
    get_photo_sources_for_platform,
)
from app.services.publisher.telegram_publisher import (
    publish_post_to_telegram,
    publish_media_group_to_telegram,
)

async def run_auto_publish_job(bot: Bot) -> dict:
    """
    Job اصلی انتشار خودکار
    Returns: dict حاوی جزئیات نتیجه برای نمایش به ادمین
    """
    log.info("🔄 [Auto Publish Job] شروع...")

    stats = {
        "total_customers": 0,
        "published_count": 0,
        "skipped_no_hours": 0,
        "skipped_no_interval": 0,
        "skipped_no_products": 0,
        "skipped_no_channels": 0,
        "skipped_no_subscription": 0,
        "skipped_inactive": 0,
        "failed": 0,
        "details": [],
    }

    try:
        async with AsyncSessionLocal() as session:
            all_settings = await get_all_customers_with_auto_publish(session)

            if not all_settings:
                log.info("[Auto Publish Job] هیچ مشتری با auto_publish روشن نیست")
                stats["message"] = "هیچ مشتری با ارسال خودکار فعال نیست"
                return stats

            stats["total_customers"] = len(all_settings)
            log.info(f"[Auto Publish Job] بررسی {len(all_settings)} مشتری...")

            for settings_obj in all_settings:
                customer_id = settings_obj.customer_id

                # چک ساعت مجاز
                if not is_in_posting_hours(settings_obj):
                    log.info(
                        f"[Customer {customer_id}] "
                        f"⏰ خارج از ساعت مجاز "
                        f"({settings_obj.posting_start_hour}-{settings_obj.posting_end_hour}), رد شد"
                    )
                    stats["skipped_no_hours"] += 1
                    stats["details"].append(f"مشتری {customer_id}: خارج از ساعت مجاز")
                    continue

                # چک زمان پست بعدی
                if not is_time_for_next_post(settings_obj):
                    remaining = _calculate_remaining_minutes(settings_obj)
                    log.info(
                        f"[Customer {customer_id}] "
                        f"⏳ هنوز زمان پست بعدی نرسیده (تا {remaining} دقیقه دیگه)"
                    )
                    stats["skipped_no_interval"] += 1
                    stats["details"].append(
                        f"مشتری {customer_id}: {remaining} دقیقه تا پست بعدی"
                    )
                    continue

                # پردازش این مشتری
                result_status = await _process_customer_publish(
                    bot=bot,
                    customer_id=customer_id,
                )

                if result_status == "published":
                    stats["published_count"] += 1
                    stats["details"].append(f"مشتری {customer_id}: ✅ پست شد")
                elif result_status == "no_products":
                    stats["skipped_no_products"] += 1
                    stats["details"].append(f"مشتری {customer_id}: محصول pending ندارد")
                elif result_status == "no_channels":
                    stats["skipped_no_channels"] += 1
                    stats["details"].append(f"مشتری {customer_id}: کانالی متصل ندارد")
                elif result_status == "no_subscription":
                    stats["skipped_no_subscription"] += 1
                    stats["details"].append(f"مشتری {customer_id}: اشتراک ندارد")
                elif result_status == "inactive":
                    stats["skipped_inactive"] += 1
                    stats["details"].append(f"مشتری {customer_id}: حساب غیرفعال")
                else:  # failed
                    stats["failed"] += 1
                    stats["details"].append(f"مشتری {customer_id}: ❌ ارسال ناموفق")

        log.info(
            f"✅ [Auto Publish Job] پایان - "
            f"بررسی: {stats['total_customers']}, "
            f"ارسال: {stats['published_count']}, "
            f"رد شده (ساعت): {stats['skipped_no_hours']}, "
            f"رد شده (زمان): {stats['skipped_no_interval']}, "
            f"رد شده (بدون محصول): {stats['skipped_no_products']}"
        )
        return stats

    except Exception as e:
        log.error(f"❌ [Auto Publish Job] خطا: {e}", exc_info=True)
        stats["error"] = str(e)
        return stats


def _calculate_remaining_minutes(settings_obj) -> int:
    """محاسبه دقیقه‌های باقیمانده تا پست بعدی"""
    from datetime import timedelta
    from app.services.posting_settings_service import get_interval_minutes

    if not settings_obj.last_post_at:
        return 0

    now = utc_now_naive()
    required_interval = timedelta(minutes=get_interval_minutes(settings_obj))
    next_post_time = settings_obj.last_post_at + required_interval

    if now >= next_post_time:
        return 0

    delta = next_post_time - now
    return int(delta.total_seconds() / 60)


async def _process_customer_publish(bot: Bot, customer_id: int) -> str:
    """
    پردازش یک مشتری: پیدا کردن محصول بعدی و ارسال به همه کانال‌هاش
    Returns: "published" | "no_products" | "no_channels" | 
             "no_subscription" | "inactive" | "failed"
    """
    async with AsyncSessionLocal() as session:
        # گرفتن مشتری
        result = await session.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = result.scalar_one_or_none()

        if not customer or customer.customer_status != CustomerStatus.ACTIVE:
            log.info(f"[Customer {customer_id}] ❌ حساب فعال نیست")
            return "inactive"

        # چک اشتراک فعال
        subscription = await get_active_subscription(session, customer.id)
        if not subscription:
            log.info(f"[Customer {customer_id}] ❌ اشتراک فعال ندارد")
            return "no_subscription"

        # گرفتن کانال‌ها
        channels = await get_customer_channels(session, customer.id, only_active=True)
        if not channels:
            log.info(f"[Customer {customer_id}] ❌ کانالی متصل ندارد")
            return "no_channels"

        # گرفتن محصول بعدی
        product = await get_next_pending_product(session, customer.id)
        if not product:
            log.info(f"[Customer {customer_id}] ⚠️ محصول pending موجود ندارد")
            return "no_products"

        # آماده‌سازی
        business_config = get_business_config_for_customer(customer)
        business = await get_business_for_customer(session, customer.id)

    if not business_config:
        log.warning(f"[Customer {customer_id}] business_config نداره")
        return "failed"
    # چک کن AI خودکار فعال هست و محصول توضیحات نداره
    async with AsyncSessionLocal() as session:
        settings_obj = await get_posting_settings(session, customer_id)
        auto_ai = settings_obj.auto_ai_description if settings_obj else False

    # متغیر برای نگه داشتن هشدار AI
    ai_notification = None  # اگر مقدار داشته باشه، به مشتری بعد از پست فرستاده میشه

    # 💡 تابع کمکی برای شمارش تعداد کلمات
    def _count_words(text: str | None) -> int:
        if not text or not text.strip():
            return 0
        # حذف ایموجی‌ها و فاصله‌های اضافی
        clean_text = text.replace("📝", "").strip()
        return len(clean_text.split())

    current_word_count = _count_words(product.description_custom)
    MIN_WORD_THRESHOLD = 10  # حداقل کلمات مقبول برای عدم استفاده از AI

    # شرط اجرا: اگر کلاً متن ندارد، یا اگر متن کمتر از ۱۰ کلمه است
    should_trigger_ai = auto_ai and (current_word_count < MIN_WORD_THRESHOLD)

    if should_trigger_ai:
        # تعیین Mode مناسب برای AI
        ai_mode = "improve" if current_word_count > 0 else "new"

        # چک توکن
        async with AsyncSessionLocal() as session:
            available_tokens = await get_total_available_tokens(session, customer.id)

        if available_tokens < 1:
            log.warning(f"⚠️ [Customer {customer_id}] AI خودکار فعال ولی توکن کافی نیست")
            ai_notification = (
                f"⚠️ برای محصول <b>{product.product_name}</b> AI اجرا نشد!\n"
                f"دلیل: توکن AI کافی ندارید.\n"
                f"محصول با همان متن فعلی پست شد.\n\n"
                f"💡 برای خرید توکن به منوی '🤖 توکن AI' برید."
            )
        else:
            log.info(
                f"🤖 [Customer {customer_id}] تولید AI خودکار ({ai_mode}) "
                f"برای {product.sku} (تعداد کلمات فعلی: {current_word_count})"
            )

            # مصرف توکن
            async with AsyncSessionLocal() as session:
                consumed = await consume_tokens(session, customer.id, 1)

            if consumed:
                # فراخوانی AI با حالت مناسب (new یا improve)
                ai_result = await generate_product_description(
                    product=product,
                    business_config=business_config,
                    mode=ai_mode,
                )

                if ai_result.success:
                    # ذخیره در دیتابیس
                    async with AsyncSessionLocal() as session:
                        result_prod = await session.execute(
                            select(Product).where(Product.id == product.id)
                        )
                        p = result_prod.scalar_one_or_none()
                        if p:
                            p.description_custom = ai_result.formatted_text
                            await session.commit()
                            product.description_custom = ai_result.formatted_text

                        # لاگ
                        await log_ai_usage(
                            session=session,
                            customer_id=customer.id,
                            product_id=product.id,
                            usage_type=f"auto_{ai_mode}",
                            tokens_used=1,
                            model_used=settings.AI_MODEL,
                            accepted=True,
                            raw_response=ai_result.raw_response,
                        )
                    log.info(f"✅ [Customer {customer_id}] AI خودکار با موفقیت اعمال شد برای {product.sku}")
                else:
                    # عودت توکن در صورت خطا
                    async with AsyncSessionLocal() as session:
                        await refund_tokens(session, customer.id, 1)
                    log.warning(f"⚠️ [Customer {customer_id}] AI ناموفق: {ai_result.error_message}")
                    ai_notification = (
                        f"⚠️ برای محصول <b>{product.product_name}</b> AI اجرا نشد!\n"
                        f"دلیل: {ai_result.error_message}\n"
                        f"توکن به حساب شما بازگشت."
                    )
    else:
        log.info(
            f"⚠️ [Customer {customer_id}] AI خودکار فعال ولی "
            f"توکن کافی نیست، ارسال بدون AI"
        )
    # ساخت کپشن
    caption = build_post_caption(product, business_config, business)

    log.info(
        f"📤 [Customer {customer_id}] ارسال محصول {product.sku} "
        f"به {len(channels)} کانال"
    )

    # ارسال به هر کانال
    any_success = False
    failed_channels: list[str] = []
    # ارسال به همه کانال‌های ACTIVE (تلگرام + ایتا)
    from app.services.publisher.publisher_manager import publish_to_channel
    from app.services.publisher.posted_message_service import create_posted_message

    # گرفتن توکن ایتا (اگه کانال ایتا داره)
    eitaa_token = None
    has_eitaa_channel = any(ch.platform == Platform.EITAA for ch in channels)

    if has_eitaa_channel:
        async with AsyncSessionLocal() as session:
            from app.services.customer_service import get_customer_eitaa_token
            eitaa_token = await get_customer_eitaa_token(session, customer.id)

    from app.services.publisher.publisher_manager import publish_to_channels_parallel
    import asyncio
    
    any_success = False

    # 🚀 فراخوانی لایه موازی که در گام 1 نوشتیم
    parallel_results = await publish_to_channels_parallel(
        bot=bot,
        channels=channels,
        product=product,
        caption=caption,
        eitaa_token=eitaa_token
    )

    # پردازش نتایج برگشتی
    for idx, result in enumerate(parallel_results):
        channel = channels[idx]
        
        if result.success and result.message_id:
            # ذخیره در posted_messages
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
            any_success = True
            log.info(f"✅ [Customer {customer_id}] پست شد در {channel.platform.value}: {channel.channel_identifier}")
        else:
            failed_channels.append(
                f"{channel.platform.value} ({channel.channel_identifier}): {result.error_message}"
            )
            log.error(
                f"❌ [Customer {customer_id}] ارسال به "
                f"{channel.platform.value}: {channel.channel_identifier} "
                f"ناموفق: {result.error_message}"
            )

    # آپدیت وضعیت محصول و زمان آخرین پست
    async with AsyncSessionLocal() as session:
        if any_success:
            await mark_product_as_published(session, product.id)
            await update_last_post_time(session, customer_id)

            # ساخت پیام اطلاع
            notification_text = (
                f"📤 پست خودکار ارسال شد\n"
                f"━━━━━━━━━━━━━━━\n"
                f"محصول: {product.product_name}\n"
                f"کد: {product.sku}\n"
                f"━━━━━━━━━━━━━━━"
            )

            # اگه هشدار AI بود، اضافه کن
            if ai_notification:
                notification_text += f"\n\n{ai_notification}"

            # 🆕 اگه بعضی کانال‌ها fail شدن، در کنار موفقیت کلی گزارش بده
            if failed_channels:
                notification_text += (
                    f"\n\n⚠️ <b>پست در {len(failed_channels)} کانال ارسال نشد:</b>\n"
                )
                for f in failed_channels[:10]:
                    notification_text += f"• {f}\n"

            try:
                await bot.send_message(
                    chat_id=customer.telegram_user_id,
                    text=notification_text,
                    parse_mode="HTML",
                )
            except Exception as e:
                log.warning(f"خطا در اطلاع به مشتری: {e}")

            return "published"
        else:
            await mark_product_as_failed(session, product.id)

            # حتی اگه پست fail شد، هشدار AI رو بفرست
            try:
                fail_text = (
                    f"❌ ارسال پست ناموفق (در همه‌ی کانال‌ها)\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"محصول: {product.product_name}\n"
                    f"کد: {product.sku}\n"
                )
                if failed_channels:
                    fail_text += "\n<b>جزئیات خطا:</b>\n"
                    for f in failed_channels[:10]:
                        fail_text += f"• {f}\n"
                if ai_notification:
                    fail_text += f"\n{ai_notification}"

                await bot.send_message(
                    chat_id=customer.telegram_user_id,
                    text=fail_text,
                    parse_mode="HTML",
                )
            except Exception as e:
                log.warning(f"خطا در اطلاع به مشتری: {e}")

            return "failed"