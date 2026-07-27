"""
تست سرویس تنظیمات ارسال
"""

from app.services.posting_settings_service import calculate_posts_per_day
from app.database.models import PostingSettings


def make_settings(start=9, end=22, interval=3) -> PostingSettings:
    s = PostingSettings()
    s.posting_start_hour = start
    s.posting_end_hour = end
    s.interval_hours = interval
    return s


def test_posts_per_day_normal():
    """۹ صبح تا ۲۲ شب، هر ۳ ساعت → ۴ پست در روز"""
    s = make_settings(start=9, end=22, interval=3)
    assert calculate_posts_per_day(s) == 4


def test_posts_per_day_hourly():
    """۹ تا ۲۲، هر ۱ ساعت → ۱۳ پست"""
    s = make_settings(start=9, end=22, interval=1)
    assert calculate_posts_per_day(s) == 13


def test_posts_per_day_all_day():
    """۰ تا ۲۴، هر ۳ ساعت → ۸ پست"""
    s = make_settings(start=0, end=24, interval=3)
    assert calculate_posts_per_day(s) == 8


def test_posts_per_day_zero_interval():
    """فاصله صفر → صفر پست (جلوگیری از تقسیم بر صفر)"""
    s = make_settings(start=9, end=22, interval=0)
    assert calculate_posts_per_day(s) == 0


def test_posts_per_day_invalid_hours():
    """ساعت پایان قبل از شروع → صفر"""
    s = make_settings(start=22, end=9, interval=3)
    assert calculate_posts_per_day(s) == 0