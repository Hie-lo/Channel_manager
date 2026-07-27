"""
مدیریت وضعیت مکالمه با کاربر
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any


class UserState(Enum):
    """حالت‌های مختلف کاربر"""
    IDLE = "idle"
    WAITING_CHANNEL_ID = "waiting_channel_id"
    WAITING_PAYMENT_RECEIPT = "waiting_payment_receipt"
    WAITING_EXCEL_FILE = "waiting_excel_file"  
    WAITING_SHEET_URL = "waiting_sheet_url" 
    WAITING_AI_TOKEN_RECEIPT = "waiting_ai_token_receipt"

@dataclass
class UserContext:
    state: UserState = UserState.IDLE
    data: dict[str, Any] = field(default_factory=dict)


_user_contexts: dict[int, UserContext] = {}


def set_user_state(user_id: int, state: UserState, data: dict | None = None) -> None:
    if user_id not in _user_contexts:
        _user_contexts[user_id] = UserContext()
    _user_contexts[user_id].state = state
    if data:
        _user_contexts[user_id].data.update(data)


def get_user_state(user_id: int) -> UserState:
    context = _user_contexts.get(user_id)
    return context.state if context else UserState.IDLE


def get_user_data(user_id: int) -> dict:
    context = _user_contexts.get(user_id)
    return context.data if context else {}


def clear_user_state(user_id: int) -> None:
    if user_id in _user_contexts:
        del _user_contexts[user_id]