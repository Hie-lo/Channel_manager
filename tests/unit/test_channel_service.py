"""
تست سرویس کانال
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.channel_service import (
    check_channel_already_exists,
    add_channel_for_customer,
    ChannelCheckResult,
)


def make_mock_session(return_value=None):
    """ساخت session شبیه‌سازی شده"""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = return_value
    result.scalars.return_value.all.return_value = []
    session.execute.return_value = result
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_check_channel_already_exists_returns_false_when_not_exists():
    """وقتی کانال وجود نداره باید False برگرده"""
    session = make_mock_session(return_value=None)
    result = await check_channel_already_exists(session, 1, "@test_channel")
    assert result is False


@pytest.mark.asyncio
async def test_add_channel_for_customer_creates_channel():
    """اضافه کردن کانال جدید"""
    session = make_mock_session()

    await add_channel_for_customer(
        session=session,
        customer_id=1,
        channel_identifier="@my_channel",
    )

    assert session.add.called
    added_channel = session.add.call_args[0][0]
    assert added_channel.channel_identifier == "@my_channel"
    assert added_channel.customer_id == 1
    assert added_channel.is_connected is True


def test_channel_check_result_valid():
    """تست کلاس ChannelCheckResult در حالت valid"""
    result = ChannelCheckResult(
        is_valid=True,
        channel_title="Test Channel",
        member_count=100,
    )
    assert result.is_valid is True
    assert result.channel_title == "Test Channel"
    assert result.member_count == 100
    assert result.error_message == ""


def test_channel_check_result_invalid():
    """تست کلاس ChannelCheckResult در حالت invalid"""
    result = ChannelCheckResult(
        is_valid=False,
        error_message="ربات ادمین نیست",
    )
    assert result.is_valid is False
    assert result.error_message == "ربات ادمین نیست"