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

    # ✅ BigInteger برای پشتیبانی از آیدی‌های بزرگ تلگرام
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)

    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)

    business_type_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    customer_status: Mapped[CustomerStatus] = mapped_column(
        SAEnum(CustomerStatus),
        default=CustomerStatus.PENDING
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

    description_manual: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    last_caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_price: Mapped[Numeric | None] = mapped_column(Numeric(18, 0), nullable=True)
    last_stock_qty: Mapped[int | None] = mapped_column(Integer, nullable=True)

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