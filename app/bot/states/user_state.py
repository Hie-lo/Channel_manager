"""
مدیریت وضعیت مکالمه با کاربر
هر کاربر ممکنه در حالت خاصی باشه (مثلاً منتظر آیدی کانال)
"""

from enum import Enum


class UserState(Enum):
    """حالت‌های مختلف کاربر"""
    IDLE = "idle"                              # حالت عادی
    WAITING_CHANNEL_ID = "waiting_channel_id"  # منتظر ارسال آیدی کانال


# ذخیره وضعیت هر کاربر
# در آینده به Redis منتقل می‌شود
_user_states: dict[int, UserState] = {}


def set_user_state(user_id: int, state: UserState) -> None:
    """تنظیم وضعیت کاربر"""
    _user_states[user_id] = state


def get_user_state(user_id: int) -> UserState:
    """گرفتن وضعیت کاربر"""
    return _user_states.get(user_id, UserState.IDLE)


def clear_user_state(user_id: int) -> None:
    """پاک کردن وضعیت کاربر"""
    if user_id in _user_states:
        del _user_states[user_id]