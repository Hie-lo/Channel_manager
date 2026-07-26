"""
تست مدیریت وضعیت کاربر
"""

from app.bot.states.user_state import (
    UserState,
    set_user_state,
    get_user_state,
    clear_user_state,
)


def test_default_state_is_idle():
    """وضعیت پیش‌فرض باید IDLE باشه"""
    state = get_user_state(999999)
    assert state == UserState.IDLE


def test_set_and_get_state():
    """ست کردن و گرفتن وضعیت"""
    set_user_state(111, UserState.WAITING_CHANNEL_ID)
    assert get_user_state(111) == UserState.WAITING_CHANNEL_ID


def test_clear_state():
    """پاک کردن وضعیت"""
    set_user_state(222, UserState.WAITING_CHANNEL_ID)
    clear_user_state(222)
    assert get_user_state(222) == UserState.IDLE


def test_clear_nonexistent_state():
    """پاک کردن وضعیت غیرموجود نباید خطا بده"""
    clear_user_state(888888)  # وضعیت نداشته
    assert get_user_state(888888) == UserState.IDLE