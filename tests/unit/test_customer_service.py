"""
تست سرویس مشتری
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.customer_service import (
    get_customer_by_telegram_id,
    create_customer,
    approve_customer,
    reject_customer,
)
from app.database.models import Customer, CustomerStatus


def make_mock_session(return_value=None):
    """ساخت session شبیه‌سازی شده"""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = return_value
    session.execute.return_value = result
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.mark.asyncio
async def test_get_customer_returns_none_when_not_found():
    """وقتی مشتری وجود ندارد باید None برگردد"""
    session = make_mock_session(return_value=None)
    result = await get_customer_by_telegram_id(session, 999999)
    assert result is None


@pytest.mark.asyncio
async def test_get_customer_returns_customer_when_found():
    """وقتی مشتری وجود دارد باید برگردد"""
    fake_customer = Customer()
    fake_customer.telegram_user_id = 123456
    session = make_mock_session(return_value=fake_customer)

    result = await get_customer_by_telegram_id(session, 123456)
    assert result is not None
    assert result.telegram_user_id == 123456


@pytest.mark.asyncio
async def test_create_customer_sets_pending_status():
    """مشتری جدید باید با وضعیت PENDING ساخته شود"""
    session = make_mock_session()

    await create_customer(
        session=session,
        telegram_user_id=111111,
        first_name="علی",
        last_name="احمدی",
        username="ali_ahmadi",
    )

    # چک کن session.add صدا زده شده
    assert session.add.called
    # بررسی وضعیت مشتری که اضافه شده
    added_customer = session.add.call_args[0][0]
    assert added_customer.customer_status == CustomerStatus.PENDING
    assert added_customer.telegram_user_id == 111111


@pytest.mark.asyncio
async def test_approve_customer_changes_status():
    """تایید مشتری باید وضعیت را به ACTIVE تغییر دهد"""
    fake_customer = Customer()
    fake_customer.telegram_user_id = 123456
    fake_customer.customer_status = CustomerStatus.PENDING

    session = make_mock_session(return_value=fake_customer)

    result = await approve_customer(session, 123456)
    assert result.customer_status == CustomerStatus.ACTIVE


@pytest.mark.asyncio
async def test_reject_customer_changes_status():
    """رد مشتری باید وضعیت را به REJECTED تغییر دهد"""
    fake_customer = Customer()
    fake_customer.telegram_user_id = 123456
    fake_customer.customer_status = CustomerStatus.PENDING

    session = make_mock_session(return_value=fake_customer)

    result = await reject_customer(session, 123456)
    assert result.customer_status == CustomerStatus.REJECTED