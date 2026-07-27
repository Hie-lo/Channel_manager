"""
تست توابع کمکی scheduler
"""

from datetime import timedelta
from unittest.mock import patch
from app.services.posting_settings_service import (
    is_time_for_next_post,
    is_in_posting_hours,
)
from app.database.models import PostingSettings
from app.utils.time import utc_now_naive


def make_settings(
    interval=3,
    start_hour=9,
    end_hour=22,
    last_post_hours_ago=None,
) -> PostingSettings:
    """ساخت settings تستی"""
    s = PostingSettings()
    s.interval_hours = interval
    s.posting_start_hour = start_hour
    s.posting_end_hour = end_hour

    if last_post_hours_ago is not None:
        s.last_post_at = utc_now_naive() - timedelta(hours=last_post_hours_ago)
    else:
        s.last_post_at = None

    return s


def test_first_post_ever_returns_true():
    """اگه هنوز پستی نداده، وقت پست هست"""
    s = make_settings(interval=3, last_post_hours_ago=None)
    assert is_time_for_next_post(s) is True


def test_recent_post_returns_false():
    """اگه به تازگی پست داده، وقت پست بعدی نیست"""
    s = make_settings(interval=3, last_post_hours_ago=1)
    assert is_time_for_next_post(s) is False


def test_old_post_returns_true():
    """اگه از پست قبلی به اندازه interval گذشته، وقت پست هست"""
    s = make_settings(interval=3, last_post_hours_ago=4)
    assert is_time_for_next_post(s) is True


def test_exactly_interval_returns_true():
    """دقیقاً به اندازه interval گذشته"""
    s = make_settings(interval=3, last_post_hours_ago=3)
    assert is_time_for_next_post(s) is True