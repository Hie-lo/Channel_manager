"""
سرویس امنیتی مقابله با اسپم و کنترل نرخ درخواست‌ها (Rate Limiting & Anti-Spam)
"""
import time
from collections import defaultdict
from app.utils.logger import log

# ۱. حافظه موقت اسپم‌گارد سراسری: { user_id: { 'history': [timestamps], 'blocked_until': timestamp } }
_user_spam_data = defaultdict(lambda: {"history": [], "blocked_until": 0.0})

# ۲. حافظه موقت اکشن‌های خاص: { user_id: { action: [timestamps] } }
_action_rate_limits = defaultdict(lambda: defaultdict(list))

MAX_REQUESTS_PER_WINDOW = 5   # حداکثر ۵ درخواست
WINDOW_SECONDS = 8            # در بازه ۸ ثانیه‌ای
PENALTY_SECONDS = 10          # جریمه فریز ۱۰ ثانیه‌ای در صورت تخلف


def check_user_spam(user_id: int) -> tuple[bool, int]:
    """
    بررسی اسپم بودن کاربر با الگوریتم Penalty Cooldown (برای اسپم‌گارد سراسری)
    Returns: (is_blocked: bool, remaining_cooldown_seconds: int)
    """
    now = time.time()
    user_data = _user_spam_data[user_id]

    # ۱. بررسی زمان جریمه فعال
    if now < user_data["blocked_until"]:
        remaining = int(user_data["blocked_until"] - now) + 1
        return True, remaining

    # ۲. پاکسازی درخواست‌های قدیمی
    history = [t for t in user_data["history"] if now - t < WINDOW_SECONDS]
    user_data["history"] = history

    # ۳. چک تعداد درخواست‌ها
    if len(history) >= MAX_REQUESTS_PER_WINDOW:
        user_data["blocked_until"] = now + PENALTY_SECONDS
        user_data["history"] = []  # پاکسازی تاریخچه پس از جریمه
        log.warning(f"🛡️ [Anti-Spam] کاربر {user_id} لیمیت سراسری را رد کرد ({len(history)} درخواست در {WINDOW_SECONDS}s). جریمه: {PENALTY_SECONDS}s فریز.")
        return True, PENALTY_SECONDS

    # ۴. ثبت زمان درخواست فعلی
    user_data["history"].append(now)
    return False, 0


def is_rate_limited(user_id: int, action: str, max_requests: int, time_window_seconds: int) -> bool:
    """
    بررسی نرخ درخواست برای یک اکشن خاص (مثل sync_sheet یا publish_post)
    """
    now = time.time()
    history = _action_rate_limits[user_id][action]

    # حذف زمان‌های قدیمی خارج از پنجره زمانی
    valid_history = [t for t in history if now - t < time_window_seconds]
    _action_rate_limits[user_id][action] = valid_history

    if len(valid_history) >= max_requests:
        log.warning(f"🛡️ [Rate Limit] کاربر {user_id} در اکشن '{action}' لیمیت شد ({len(valid_history)} درخواست در {time_window_seconds}s).")
        return True

    _action_rate_limits[user_id][action].append(now)
    return False