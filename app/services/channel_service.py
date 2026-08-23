"""
سرویس مدیریت کانال‌ها
اتصال کانال، بررسی وضعیت، لیست کانال‌ها
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Bot
from telegram.error import TelegramError

from app.database.models import Channel, Customer, Platform
from app.utils.logger import log
from app.utils.time import utc_now_naive


class ChannelCheckResult:
    """نتیجه بررسی کانال"""

    def __init__(
        self,
        is_valid: bool,
        error_message: str = "",
        channel_title: str = "",
        member_count: int = 0,
    ):
        self.is_valid = is_valid
        self.error_message = error_message
        self.channel_title = channel_title
        self.member_count = member_count


async def check_bot_is_admin_in_channel(
    bot: Bot,
    channel_identifier: str,
    telegram_user_id: int = None  # 🛡️ اضافه کردن آیدی درخواست دهنده
) -> ChannelCheckResult:
    """
    بررسی ادمین بودن ربات و همچنین ادمین بودن خود کاربر در کانال تلگرام
    """
    try:
        chat = await bot.get_chat(channel_identifier)

        if chat.type not in ("channel", "supergroup"):
            return ChannelCheckResult(is_valid=False, error_message="این آیدی مربوط به کانال نیست")

        # ۱. بررسی ادمین بودن ربات
        bot_member = await bot.get_chat_member(chat.id, bot.id)
        if bot_member.status not in ("administrator", "creator"):
            return ChannelCheckResult(is_valid=False, error_message="ربات ادمین کانال نیست")

        if bot_member.status == "administrator" and not bot_member.can_post_messages:
            return ChannelCheckResult(is_valid=False, error_message="ربات مجوز ارسال پیام در کانال را ندارد")

        # ۲. 🛡️ بررسی ادمین بودن کاربر درخواست دهنده (جلوگیری از سرقت کانال)
        if telegram_user_id:
            try:
                user_member = await bot.get_chat_member(chat.id, telegram_user_id)
                if user_member.status not in ("administrator", "creator"):
                    return ChannelCheckResult(is_valid=False, error_message="شما خودتان ادمین این کانال نیستید! فقط مالکان و مدیران می‌توانند کانال را متصل کنند.")
            except TelegramError as e:
                # اگر کاربر در کانال حضور نداشته باشد یا نتوانیم او را پیدا کنیم
                return ChannelCheckResult(is_valid=False, error_message="نتوانستیم وضعیت ادمین بودن شما در این کانال را تأیید کنیم.")

        try:
            member_count = await bot.get_chat_member_count(chat.id)
        except Exception:
            member_count = 0

        return ChannelCheckResult(is_valid=True, channel_title=chat.title or "", member_count=member_count)

    except TelegramError as e:
        error_msg = str(e).lower()
        if "chat not found" in error_msg:
            return ChannelCheckResult(is_valid=False, error_message="کانال پیدا نشد. آیدی رو چک کنید")
        return ChannelCheckResult(is_valid=False, error_message=f"خطا: {str(e)[:100]}")
    except Exception as e:
        return ChannelCheckResult(is_valid=False, error_message="خطای غیرمنتظره")


async def add_channel_for_customer(
    session: AsyncSession,
    customer_id: int,
    channel_identifier: str,
    platform: Platform = Platform.TELEGRAM,
    activation_status: str = "ACTIVE",
) -> Channel:
    """اضافه کردن کانال جدید برای مشتری"""
    channel = Channel(
        customer_id=customer_id,
        platform=platform,
        channel_identifier=channel_identifier,
        is_connected=(activation_status == "ACTIVE"),
        connected_at=utc_now_naive() if activation_status == "ACTIVE" else None,
        activation_status=activation_status,
        created_at=utc_now_naive(),
    )
    session.add(channel)
    await session.commit()
    await session.refresh(channel)
    log.info(
        f"کانال جدید: {channel_identifier} ({platform.value}) "
        f"برای مشتری {customer_id}"
    )
    return channel


async def get_customer_channels(
    session: AsyncSession,
    customer_id: int,
    only_active: bool = False,
) -> list[Channel]:
    """لیست کانال‌های یک مشتری"""
    query = select(Channel).where(Channel.customer_id == customer_id)

    if only_active:
        query = query.where(Channel.activation_status == "ACTIVE")

    result = await session.execute(query)
    return list(result.scalars().all())


async def get_channel_by_id(
    session: AsyncSession,
    channel_id: int,
) -> Channel | None:
    """پیدا کردن کانال با آیدی (نسخه ایمن)"""
    result = await session.execute(
        select(Channel).where(Channel.id == channel_id).limit(1)
    )
    return result.scalars().first()


async def delete_channel(
    session: AsyncSession,
    channel_id: int,
) -> bool:
    """حذف کانال"""
    channel = await get_channel_by_id(session, channel_id)
    if not channel:
        return False

    await session.delete(channel)
    await session.commit()
    log.info(f"کانال حذف شد: {channel_id}")
    return True


async def check_channel_already_exists(
    session: AsyncSession,
    customer_id: int,
    channel_identifier: str,
) -> bool:
    """چک کن کانال قبلاً برای این مشتری اضافه شده یا نه (نسخه ایمن)"""
    result = await session.execute(
        select(Channel).where(
            Channel.customer_id == customer_id,
            Channel.channel_identifier == channel_identifier,
        ).limit(1)  # 🛡️ فقط یک رکورد را محدود می‌کنیم
    )
    # به جای scalar_one_or_none از first استفاده می‌کنیم تا در صورت وجود رکوردهای داپلیکیت کرش نکند
    return result.scalars().first() is not None