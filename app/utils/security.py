"""
سرویس امنیتی پیشرفته مقابله با اسپم (Anti-Spam with Cooldown Penalty)
"""
import time
from collections import defaultdict
from app.utils.logger import log

# ساختار ذخیره‌سازی: { user_id: { 'history': [timestamps], 'blocked_until': timestamp } }
_user_spam_data = defaultdict(lambda: {"history": [], "blocked_until": 0.0})

MAX_REQUESTS_PER_WINDOW = 5   # حداکثر ۵ درخواست
WINDOW_SECONDS = 8            # در بازه ۸ ثانیه‌ای
PENALTY_SECONDS = 10          # جریمه فریز ۱۰ ثانیه‌ای در صورت تخلف


def check_user_spam(user_id: int) -> tuple[bool, int]:
    """
    بررسی اسپم بودن کاربر با الگوریتم Penalty Cooldown
    Returns: (is_blocked: bool, remaining_cooldown_seconds: int)
    """
    now = time.time()
    user_data = _user_spam_data[user_id]

    # ۱. بررسی اینکه آیا کاربر در حال حاضر در زمان جریمه (Penalty) قرار دارد یا خیر
    if now < user_data["blocked_until"]:
        remaining = int(user_data["blocked_until"] - now) + 1
        return True, remaining

    # ۲. پاکسازی تاریخچه درخواست‌های قدیمی خارج از پنجره زمانی
    history = [t for t in user_data["history"] if now - t < WINDOW_SECONDS]
    user_data["history"] = history

    # ۳. آیا تعداد درخواست‌ها در این پنجره بیشتر از حد مجاز است؟
    if len(history) >= MAX_REQUESTS_PER_WINDOW:
        # اعمال جریمه ۱۰ ثانیه‌ای فریز کامل
        user_data["blocked_until"] = now + PENALTY_SECONDS
        user_data["history"] = []  # پاکسازی تاریخچه پس از جریمه
        log.warning(f"🛡️ [Anti-Spam] کاربر {user_id} لیمیت را رد کرد ({len(history)} درخواست در {WINDOW_SECONDS}s). جریمه: {PENALTY_SECONDS}s فریز.")
        return True, PENALTY_SECONDS

    # ۴. مجاز است - ثبت زمان درخواست
    user_data["history"].append(now)
    return False, 0