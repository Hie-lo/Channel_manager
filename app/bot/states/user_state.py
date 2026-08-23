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
    WAITING_CHANNEL_ID_TELEGRAM = "waiting_channel_id_telegram"  # ← مهم
    WAITING_CHANNEL_ID_EITAA = "waiting_channel_id_eitaa"
    WAITING_CHANNEL_ID_BALE = "waiting_channel_id_bale"
    WAITING_PAYMENT_RECEIPT = "waiting_payment_receipt"
    WAITING_EXCEL_FILE = "waiting_excel_file"
    WAITING_AI_TOKEN_RECEIPT = "waiting_ai_token_receipt"
    WAITING_PRODUCT_IMAGE = "waiting_product_image"
    WAITING_SHEET_URL = "waiting_sheet_url"
    VIEWING_AI_RESULT = "viewing_ai_result"
    ADMIN_SENDING_MESSAGE = "admin_sending_message"
    ADMIN_GIFTING_TOKENS = "admin_gifting_tokens"
    ADMIN_BROADCASTING = "admin_broadcasting"
    ADMIN_SEARCHING_CUSTOMER = "admin_searching_customer"
    WAITING_SUPPORT_MESSAGE = "waiting_support_message"
    ADMIN_REPLYING_TO_SUPPORT = "admin_replying_to_support"
    VIEWING_SYNC_PREVIEW = "viewing_sync_preview"
    WAITING_EDIT_POSTS_DECISION = "waiting_edit_posts_decision"
    WAITING_EITAA_TOKEN = "waiting_eitaa_token"
    WAITING_EITAA_CHAT_ID = "waiting_eitaa_chat_id"
    WAITING_FOR_LINK_CODE = "waiting_for_link_code"
    WAITING_CUSTOM_POST_TEXT = "waiting_custom_post_text"
    WAITING_CUSTOM_POST_PHOTOS = "waiting_custom_post_photos"
    VIEWING_CUSTOM_POST_PREVIEW = "viewing_custom_post_preview"
    WAITING_COLUMN_MAPPING = "waiting_column_mapping"
    
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