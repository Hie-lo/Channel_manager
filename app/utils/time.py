"""
توابع کمکی زمان
"""

from datetime import datetime, UTC


def utc_now_naive() -> datetime:
    """
    زمان فعلی UTC به صورت naive
    فعلاً برای سازگاری با ستون‌های DateTime فعلی دیتابیس
    """
    return datetime.now(UTC).replace(tzinfo=None)