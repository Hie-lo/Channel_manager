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
    user_id_to_check: int = None
) -> ChannelCheckResult:
    """
    بررسی ادمین بودن ربات و همچنین ادمین بودن خود کاربر در کانال (تلگرام یا بله)
    """
    try:
        chat = await bot.get_chat(channel_identifier)

        if chat.type not in ("channel", "supergroup"):
            return ChannelCheckResult(is_valid=False, error_message="این آیدی مربوط به کانال نیست")

        # ۱. بررسی ادمین بودن ربات ما
        bot_member = await bot.get_chat_member(chat.id, bot.id)
        if bot_member.status not in ("administrator", "creator"):
            return ChannelCheckResult(is_valid=False, error_message="ربات ادمین کانال نیست. ابتدا ربات را ادمین کانال کنید.")

        # ۲. بررسی ادمین بودن کاربر درخواست‌دهنده
        if user_id_to_check:
            try:
                user_member = await bot.get_chat_member(chat.id, user_id_to_check)
                if user_member.status not in ("administrator", "creator"):
                    return ChannelCheckResult(
                        is_valid=False, 
                        error_message="شما خودتان در این کانال ادمین نیستید! فقط مالکان و مدیران کانال می‌توانند آن را متصل کنند."
                    )
            except TelegramError:
                return ChannelCheckResult(
                    is_valid=False, 
                    error_message="حساب کاربری شما در این کانال یافت نشد یا دسترسی ادمین ندارد."
                )

        try:
            member_count = await bot.get_chat_member_count(chat.id)
        except Exception:
            member_count = 0

        return ChannelCheckResult(is_valid=True, channel_title=chat.title or "", member_count=member_count)

    except TelegramError as e:
        error_msg = str(e).lower()
        if "chat not found" in error_msg:
            return ChannelCheckResult(is_valid=False, error_message="کانال پیدا نشد. آیدی یا لینک را بررسی کنید.")
        return ChannelCheckResult(is_valid=False, error_message=f"خطا در بررسی کانال: {str(e)[:100]}")
    except Exception as e:
        return ChannelCheckResult(is_valid=False, error_message="خطای غیرمنتظره در بررسی کانال")


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
    platform: Platform = Platform.TELEGRAM
) -> tuple[bool, str]:
    """
    دیوار دفاعی دوم: بررسی وجود کانال در کل دیتابیس.
    Returns: (is_duplicate: bool, error_message: str)
    """
    # 1. آیا همین کاربر قبلاً این کانال را وصل کرده؟
    result_self = await session.execute(
        select(Channel).where(
            Channel.customer_id == customer_id,
            Channel.channel_identifier == channel_identifier,
            Channel.platform == platform
        ).limit(1)
    )
    if result_self.scalars().first():
        return True, "⚠️ این کانال قبلاً در لیست کانال‌های شما ثبت شده است."

    # 2. 🛡️ دیوار دفاعی دوم: آیا کاربر دیگری در کل سیستم این کانال را وصل کرده؟
    result_global = await session.execute(
        select(Channel).where(
            Channel.channel_identifier == channel_identifier,
            Channel.platform == platform
        ).limit(1)
    )
    if result_global.scalars().first():
        log.warning(f"🛡️ [Security] تلاش برای اتصال کانال تکراری سراسری: {channel_identifier} توسط مشتری {customer_id}")
        return True, "⛔ این کانال قبلاً توسط کاربر دیگری در سیستم ثبت شده است! اگر مالک این کانال هستید، با پشتیبانی تماس بگیرید."

    return False, ""