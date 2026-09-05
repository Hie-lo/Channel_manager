import enum
from datetime import datetime

from sqlalchemy import (
    String,
    Integer,
    BigInteger,
    DateTime,
    ForeignKey,
    Boolean,
    Text,
    UniqueConstraint,
    Numeric,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Enum as SAEnum

from app.utils.time import utc_now_naive


class Base(DeclarativeBase):
    pass


class CustomerStatus(enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REJECTED = "REJECTED"


class Platform(enum.Enum):
    TELEGRAM = "TELEGRAM"
    EITAA = "EITAA"     
    BALE = "BALE"

class SubscriptionStatus(enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    GRACE = "GRACE"
    SUSPENDED = "SUSPENDED"


class TokenSource(enum.Enum):
    MONTHLY = "MONTHLY"
    PURCHASED = "PURCHASED"

class ProductPublishStatus(enum.Enum):
    """وضعیت انتشار محصول در کانال"""
    PENDING = "PENDING"           # هنوز منتشر نشده
    SCHEDULED = "SCHEDULED"       # در صف انتشار
    PUBLISHED = "PUBLISHED"       # منتشر شده
    FAILED = "FAILED"             # ارسال ناموفق
    SKIPPED = "SKIPPED"           # نادیده گرفته شده

class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ─── آیدی‌های پلتفرم‌ها ───
    telegram_user_id: Mapped[int | None] = mapped_column(
        BigInteger, unique=True, index=True, nullable=True
    )
    bale_user_id: Mapped[int | None] = mapped_column(
        BigInteger, unique=True, index=True, nullable=True
    )
    # آماده برای آینده:
    # rubika_user_id, eitaa_user_id, ...

    # ─── اطلاعات تلگرام ───
    telegram_first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    telegram_last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    telegram_username: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ─── اطلاعات بله ───
    bale_first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bale_last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bale_username: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ─── سازگاری با کد قدیمی (برای انتقال ساده) ───
    # این‌ها فیلدهای مجازی هستن که به فیلدهای پلتفرم اصلی اشاره می‌کنن
    # (property تعریف نمی‌کنیم چون در query استفاده میشن)
    # به جاش، همون first_name/last_name/username رو نگه می‌داریم:
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # ─── سایر ───
    source_platform: Mapped[str] = mapped_column(String(20), default="TELEGRAM")
    business_type_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    eitaa_bot_token: Mapped[str | None] = mapped_column(String(500), nullable=True)

    customer_status: Mapped[CustomerStatus] = mapped_column(
        SAEnum(CustomerStatus),
        default=CustomerStatus.PENDING
    )
    # ─── preset پست انتخابی مشتری ───
    selected_post_preset_id: Mapped[int | None] = mapped_column(
        ForeignKey("post_template_presets.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now_naive,
        onupdate=utc_now_naive
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)

    plan_key: Mapped[str] = mapped_column(String(50))
    status: Mapped[SubscriptionStatus] = mapped_column(
        SAEnum(SubscriptionStatus),
        default=SubscriptionStatus.PENDING
    )

    start_at: Mapped[datetime] = mapped_column(DateTime)
    end_at: Mapped[datetime] = mapped_column(DateTime)
    grace_end_at: Mapped[datetime] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)

    business_type_key: Mapped[str] = mapped_column(String(100))
    business_name: Mapped[str] = mapped_column(String(200))
    contact_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)

    platform: Mapped[Platform] = mapped_column(
        SAEnum(Platform),
        default=Platform.TELEGRAM
    )
    channel_identifier: Mapped[str] = mapped_column(String(200))
    
    # ─── آیدی تماس (username/id) برای هر پلتفرم ───
    contact_id_telegram: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contact_id_bale: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contact_id_eitaa: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone_telegram: Mapped[str | None] = mapped_column(String(30), nullable=True)
    phone_bale: Mapped[str | None] = mapped_column(String(30), nullable=True)
    phone_eitaa: Mapped[str | None] = mapped_column(String(30), nullable=True)
    
    # وضعیت فعال‌سازی برای پلتفرم‌های غیر تلگرام
    activation_status: Mapped[str] = mapped_column(
        String(30),
        default="ACTIVE"  # ACTIVE / PENDING_ACTIVATION
    )
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    connected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class AIToken(Base):
    __tablename__ = "ai_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)

    source: Mapped[TokenSource] = mapped_column(SAEnum(TokenSource))
    total_amount: Mapped[int] = mapped_column(Integer)
    used_amount: Mapped[int] = mapped_column(Integer, default=0)
    remaining_amount: Mapped[int] = mapped_column(Integer)

    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("customer_id", "sku", name="uq_customer_sku"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    business_id: Mapped[int | None] = mapped_column(ForeignKey("businesses.id"), nullable=True)
    sub_category_key: Mapped[str | None] = mapped_column(String(80), nullable=True)  # laptop, monitor, ...
    sku: Mapped[str] = mapped_column(String(80))
    product_name: Mapped[str] = mapped_column(String(250))

    price: Mapped[Numeric] = mapped_column(Numeric(18, 0), default=0)
    stock_qty: Mapped[int] = mapped_column(Integer, default=0)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)

    # ─── توضیحات (دستی یا سفارشی‌شده) ───
    description_custom: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # ─── توضیحات تولید شده توسط AI (ساختاریافته) ───
    ai_description: Mapped[str | None] = mapped_column(Text, nullable=True)  # توضیح اصلی
    ai_pros: Mapped[list] = mapped_column(JSONB, default=list)  # لیست مزایا ["مزیت 1", "مزیت 2", ...]
    ai_cons: Mapped[list] = mapped_column(JSONB, default=list)  # لیست معایب ["معایب 1", "معایب 2", ...]
    ai_details: Mapped[dict] = mapped_column(JSONB, default=dict)  # جزئیات تکمیلی AI برای قالب پست
    
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    specs: Mapped[dict] = mapped_column(JSONB, default=dict)
    publish_status: Mapped[ProductPublishStatus] = mapped_column(
        SAEnum(ProductPublishStatus),
        default=ProductPublishStatus.PENDING
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now_naive,
        onupdate=utc_now_naive
    )


class PostedMessage(Base):
    __tablename__ = "posted_messages"
    __table_args__ = (
        UniqueConstraint("product_id", "channel_id", name="uq_product_channel"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id"), index=True)

    platform: Mapped[Platform] = mapped_column(
        SAEnum(Platform),
        default=Platform.TELEGRAM
    )
    # ✅ BigInteger برای message_id تلگرام
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # آیدی همه پیام‌های media group (اگه آلبوم بود)
    # به صورت JSON list: [123, 124, 125]
    telegram_message_ids: Mapped[list] = mapped_column(JSONB, default=list)

    last_caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_price: Mapped[Numeric | None] = mapped_column(Numeric(18, 0), nullable=True)
    last_stock_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # هش عکس‌های آخرین پست برای تشخیص تغییر عکس (برای Bale و Eitaa)
    last_media_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now_naive,
        onupdate=utc_now_naive
    )

class PostingSettings(Base):
    """تنظیمات ارسال پست هر مشتری"""
    __tablename__ = "posting_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        unique=True,
        index=True,
    )

    # فعال بودن انتشار خودکار
    auto_publish_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # فاصله بین پست‌ها (به ساعت)
    interval_hours: Mapped[int] = mapped_column(Integer, default=3)
    # فاصله بین پست‌ها به دقیقه — واحد اصلی و دقیق‌تر از این به بعد
    interval_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    # ساعت‌های مجاز (0-23)
    posting_start_hour: Mapped[int] = mapped_column(Integer, default=9)
    posting_end_hour: Mapped[int] = mapped_column(Integer, default=22)
    # آیا AI به صورت خودکار توضیحات تولید کنه؟
    auto_ai_description: Mapped[bool] = mapped_column(Boolean, default=False)
    # زمان آخرین پست
    last_post_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now_naive,
        onupdate=utc_now_naive,
    )

class GoogleSheetConnection(Base):
    """اتصال Google Sheet هر مشتری"""
    __tablename__ = "google_sheet_connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"),
        unique=True,
        index=True,
    )

    sheet_url: Mapped[str] = mapped_column(Text)
    sheet_id: Mapped[str] = mapped_column(String(200))  # شناسه یکتای شیت
    worksheet_name: Mapped[str] = mapped_column(String(200), default="Sheet1")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String(50), nullable=True)  # SUCCESS/FAILED
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now_naive,
        onupdate=utc_now_naive,
    )

class AIUsageLog(Base):
    """لاگ استفاده از AI (برای ردیابی و آمار)"""
    __tablename__ = "ai_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)

    usage_type: Mapped[str] = mapped_column(String(30))  # generate | improve
    tokens_used: Mapped[int] = mapped_column(Integer, default=1)
    model_used: Mapped[str] = mapped_column(String(100))

    accepted: Mapped[bool] = mapped_column(Boolean, default=False)  # آیا مشتری قبول کرد
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class Tutorial(Base):
    """آموزش‌ها (ویدیو، متن، FAQ)"""
    __tablename__ = "tutorials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # کلید یکتا برای هر آموزش (مثلاً "connect_channel", "upload_excel")
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    # عنوان نمایشی
    title: Mapped[str] = mapped_column(String(200))

    # دسته‌بندی: general / channel / upload / sheet / ai / subscription / faq
    category: Mapped[str] = mapped_column(String(50), index=True)

    # نوع: video / text / faq
    content_type: Mapped[str] = mapped_column(String(20))

    # محتوای متنی (برای text و faq)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # file_id ویدیو (برای video)
    video_file_id: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # کپشن ویدیو
    video_caption: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ترتیب نمایش
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    # فعال یا غیرفعال
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # برای FAQ - سوال کوتاه
    faq_question: Mapped[str | None] = mapped_column(String(300), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now_naive,
        onupdate=utc_now_naive,
    )

class ProductPlatformMedia(Base):
    """
    ذخیره file_id عکس‌های محصول برای هر پلتفرم
    یک محصول می‌تونه چند عکس داشته باشه (order مشخص می‌کنه ترتیب)
    """
    __tablename__ = "product_platform_media"
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "platform",
            "media_order",
            name="uq_product_platform_media_order",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)

    platform: Mapped[Platform] = mapped_column(
        SAEnum(Platform),
        default=Platform.TELEGRAM,
    )

    # file_id عکس
    file_id: Mapped[str] = mapped_column(String(300))

    # ترتیب عکس (0 = اول، 1 = دوم، ...)
    media_order: Mapped[int] = mapped_column(Integer, default=0)

    # آپلود شده توسط مشتری یا از URL دانلود شده
    uploaded_by_customer: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utc_now_naive,
        onupdate=utc_now_naive,
    )

class AccountLinkCode(Base):
    """
    جدول ذخیره کدهای موقت برای اتصال حساب بین پلتفرم‌ها (مثلاً تلگرام به بله)
    """
    __tablename__ = "account_link_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True, nullable=False)
    
    # کد 6 رقمی
    link_code: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)
    
    # زمان انقضا (مثلا 5 دقیقه بعد از تولید)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # آیا این کد استفاده شده؟
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # شمارنده تلاش‌های ناموفق (برای جلوگیری از Brute-force)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


# ═══════════════════════════════════════════════════════
# مدل‌های ماژول هوشمند مپینگ و قالب پست
# ═══════════════════════════════════════════════════════

class BusinessMappingProfile(Base):
    """
    پروفایل مپینگ هر کسب‌وکار.
    ذخیره دائمی نگاشت شیت→زیردسته و ستون→فیلد استاندارد.
    یک رکورد به ازای هر customer.
    برای اضافه کردن کسب‌وکار جدید فقط باید config.py را گسترش داد؛
    این جدول به‌طور خودکار پروفایل جدید می‌سازد.
    """
    __tablename__ = "business_mapping_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"), unique=True, index=True
    )

    # نام شیت شناسایی‌شده (e.g. "لباس", "laptops", "Sheet1")
    detected_sheet_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # کلید زیردسته‌ای که به این شیت نگاشته شده (e.g. "clothing", "laptop")
    subcategory_key: Mapped[str | None] = mapped_column(String(80), nullable=True)

    # روش شناسایی: auto_exact | auto_fuzzy | auto_heuristic | wizard
    detection_method: Mapped[str] = mapped_column(String(30), default="wizard")

    # امتیاز اطمینان (0.0 – 1.0)
    confidence_score: Mapped[float] = mapped_column(Numeric(4, 3), default=0.0)

    # نگاشت ستون‌ها: {"field_key": col_index}  e.g. {"product_name": 2, "price": 5}
    column_map: Mapped[dict] = mapped_column(JSONB, default=dict)

    # فیلدهایی که کاربر انتخاب کرده نادیده بگیره: ["color", "material"]
    ignored_fields: Mapped[list] = mapped_column(JSONB, default=list)

    # هدرهای خام اولین شیت (برای نمایش در ویرایش مجدد)
    raw_headers: Mapped[list] = mapped_column(JSONB, default=list)

    # آیا این مپینگ توسط کاربر تأیید و ذخیره شده؟
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now_naive, onupdate=utc_now_naive
    )


class PostTemplate(Base):
    """
    قالب پست هر کسب‌وکار — کاملاً سفارشی‌سازی‌پذیر توسط مشتری.
    یک رکورد به ازای هر customer.
    هر بار که کسب‌وکار جدیدی اضافه شود، متد get_default_body_fields
    در post_template_service آن را پشتیبانی می‌کند.
    """
    __tablename__ = "post_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"), unique=True, index=True
    )

    # نام نمایشی قالب
    template_name: Mapped[str] = mapped_column(String(200), default="قالب پیش‌فرض")

    # ─── عنوان ───
    # الگوی عنوان: از placeholder {field_key} پشتیبانی می‌کند
    # مثال: "🧥 {brand} | {product_name}"
    title_pattern: Mapped[str] = mapped_column(String(500), default="{product_name}")
    title_bold: Mapped[bool] = mapped_column(Boolean, default=True)

    # ─── بدنه ───
    # لیست مرتب فیلدها برای نمایش در بدنه پست:
    # [{"key": "price", "label": "💰 قیمت", "format": "{value:,} تومان", "enabled": true}, ...]
    body_fields: Mapped[list] = mapped_column(JSONB, default=list)

    # جداکننده بین فیلدها (پیش‌فرض: خط جدید)
    field_separator: Mapped[str] = mapped_column(String(20), default="\n")

    # ─── فیلترهای ردیف ───
    skip_if_out_of_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    skip_if_price_zero: Mapped[bool] = mapped_column(Boolean, default=True)
    min_stock: Mapped[int] = mapped_column(Integer, default=1)

    # ─── رسانه ───
    use_image: Mapped[bool] = mapped_column(Boolean, default=True)
    fallback_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── پاورقی ───
    contact_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # هشتگ‌های ثابت: ["#پوشاک", "#خرید_آنلاین"]
    static_hashtags: Mapped[list] = mapped_column(JSONB, default=list)
    # هشتگ‌های پویا: [{"field": "brand", "prefix": "#"}, {"field": "color", "prefix": "#رنگ_"}]
    dynamic_hashtags: Mapped[list] = mapped_column(JSONB, default=list)

    # ─── چیدمان ───
    # text_only | text_with_image
    layout: Mapped[str] = mapped_column(String(30), default="text_with_image")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now_naive, onupdate=utc_now_naive
    )

class PostTemplatePreset(Base):
    """
    نمونه‌ی آماده‌ی پست که خود ادمین طراحی می‌کنه.
    هر preset مخصوص یک نوع کسب‌وکار (و اختیاری: یک زیردسته) است؛
    مشتری‌ها فقط از بین این‌ها انتخاب می‌کنن، ویرایش آزاد ندارن.
    """
    __tablename__ = "post_template_presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    business_type_key: Mapped[str] = mapped_column(String(100), index=True)
    # None یعنی این preset برای کل کسب‌وکار عمومیه (مخصوص یک زیردسته نیست)
    subcategory_key: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)

    name_fa: Mapped[str] = mapped_column(String(200))
    # متن خام قالب، دقیقاً مثل فایل‌های .txt فعلی با {placeholder}
    template_text: Mapped[str] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now_naive, onupdate=utc_now_naive
    )