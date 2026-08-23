"""
سرویس امنیتی و مقابله با اسپم (Rate Limiting & Cooldowns)
"""
import time
from collections import defaultdict
from app.utils.logger import log

# ساختار ذخیره زمان درخواست‌ها در حافظه موقت: { user_id: { action: [timestamps] } }
_rate_limits: dict[int, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))


def is_rate_limited(user_id: int, action: str, max_requests: int, time_window_seconds: int) -> bool:
    """
    بررسی دقیق نرخ درخواست‌ها (Rate Limit Check)
    """
    now = time.time()
    history = _rate_limits[user_id][action]

    # حذف زمان‌های قدیمی خارج از پنجره زمانی
    valid_history = [t for t in history if now - t < time_window_seconds]
    _rate_limits[user_id][action] = valid_history

    # اگر تعداد درخواست‌های معتبر در این پنجره زمان >= حد مجاز است
    if len(valid_history) >= max_requests:
        return True

    # ثبت زمان درخواست فعلی
    _rate_limits[user_id][action].append(now)
    return False