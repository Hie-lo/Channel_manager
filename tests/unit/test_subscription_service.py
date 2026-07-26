"""
تست سرویس اشتراک
"""

import pytest
from datetime import timedelta
from app.services.subscription.service import (
    calculate_days_remaining,
    is_in_grace_period,
    is_subscription_active,
)
from app.database.models import Subscription, SubscriptionStatus
from app.utils.time import utc_now_naive


def make_subscription(days_from_now: int, status=SubscriptionStatus.ACTIVE) -> Subscription:
    """ساخت اشتراک برای تست"""
    now = utc_now_naive()
    sub = Subscription()
    sub.status = status
    sub.start_at = now - timedelta(days=30 - days_from_now if days_from_now > 0 else 30 + abs(days_from_now))
    sub.end_at = now + timedelta(days=days_from_now)
    sub.grace_end_at = sub.end_at + timedelta(days=2)
    return sub


def test_days_remaining_positive():
    """۱۰ روز مانده"""
    sub = make_subscription(days_from_now=10)
    days = calculate_days_remaining(sub)
    assert 9 <= days <= 10


def test_days_remaining_expired():
    """منقضی شده"""
    sub = make_subscription(days_from_now=-5)
    days = calculate_days_remaining(sub)
    assert days == 0


def test_active_subscription_is_active():
    """اشتراک فعال با ۱۰ روز مانده"""
    sub = make_subscription(days_from_now=10)
    assert is_subscription_active(sub) is True


def test_expired_no_grace_not_active():
    """منقضی شده و مهلت هم تموم شده"""
    sub = make_subscription(days_from_now=-10)  # ۱۰ روز پیش منقضی
    assert is_subscription_active(sub) is False


def test_in_grace_period_still_active():
    """در مهلت تمدید هست"""
    sub = make_subscription(days_from_now=-1)  # ۱ روز پیش منقضی
    sub.status = SubscriptionStatus.GRACE
    # هنوز در مهلت ۲ روزه هست
    assert is_subscription_active(sub) is True


def test_is_in_grace_period_true():
    """چک مهلت تمدید"""
    sub = make_subscription(days_from_now=-1)
    assert is_in_grace_period(sub) is True


def test_is_in_grace_period_false_active():
    """اشتراک فعال، در مهلت نیست"""
    sub = make_subscription(days_from_now=10)
    assert is_in_grace_period(sub) is False


def test_none_subscription_not_active():
    """اگر subscription نباشه، False"""
    assert is_subscription_active(None) is False
    assert calculate_days_remaining(None) == 0
    assert is_in_grace_period(None) is False