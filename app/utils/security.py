"""
سرویس امنیتی و مقابله با اسپم (Rate Limiting & Cooldowns)
"""
import time
from collections import defaultdict
from app.utils.logger import log

# ساختار: { user_id: { action_name: [timestamp1, timestamp2, ...] } }
_rate_limits: dict[int, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))


def is_rate_limited(user_id: int, action: str, max_requests: int, time_window_seconds: int) -> bool:
    """
    بررسی می‌کند که آیا کاربر از حد مجاز درخواست‌ها عبور کرده است یا خیر.
    
    Args:
        user_id: آیدی کاربر
        action: نام عملیات (مثلاً 'sync_sheet' یا 'send_post')
        max_requests: حداکثر تعداد درخواست مجاز
        time_window_seconds: پنجره زمانی به ثانیه (مثلاً ۶۰ ثانیه)
        
    Returns:
        True اگر کاربر لیمیت شده باشد (اسپم)، False اگر مجاز باشد.
    """
    now = time.time()
    history = _rate_limits[user_id][action]
    
    # پاکسازی زمان‌های قدیمی‌تر از پنجره زمانی
    history = [t for t in history if now - t < time_window_seconds]
    _rate_limits[user_id][action] = history

    # اگر تعداد درخواست‌ها در این بازه بیشتر از حد مجاز است
    if len(history) >= max_requests:
        log.warning(f"🛡 [Rate Limit] کاربر {user_id} روی عملیات '{action}' لیمیت شد.")
        return True

    # اگر مجاز است، زمان فعلی را ثبت کن
    _rate_limits[user_id][action].append(now)
    return False