"""
سرویس رمزنگاری داده‌های حساس

استفاده:
    from app.utils.encryption import encrypt_text, decrypt_text
    
    encrypted = encrypt_text("secret data")
    original = decrypt_text(encrypted)
"""

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings
from app.utils.logger import log


_fernet_instance = None


def _get_fernet() -> Fernet | None:
    """گرفتن instance از Fernet (lazy loading)"""
    global _fernet_instance

    if _fernet_instance is not None:
        return _fernet_instance

    if not settings.ENCRYPTION_KEY:
        log.error("⚠️ ENCRYPTION_KEY تنظیم نشده! رمزنگاری غیرفعال است.")
        return None

    try:
        # کلید باید bytes باشه
        key = settings.ENCRYPTION_KEY.encode() if isinstance(settings.ENCRYPTION_KEY, str) else settings.ENCRYPTION_KEY
        _fernet_instance = Fernet(key)
        return _fernet_instance
    except Exception as e:
        log.error(f"خطا در ساخت Fernet: {e}")
        return None


def encrypt_text(plain_text: str) -> str:
    """
    رمزنگاری متن
    اگه رمزنگاری کار نکنه، متن اصلی برگردانده میشه (با warning)
    """
    if not plain_text:
        return plain_text

    fernet = _get_fernet()
    if not fernet:
        log.warning("⚠️ رمزنگاری غیرفعال - متن بدون رمز ذخیره میشه")
        return plain_text

    try:
        encrypted_bytes = fernet.encrypt(plain_text.encode())
        return encrypted_bytes.decode()
    except Exception as e:
        log.error(f"خطا در رمزنگاری: {e}")
        return plain_text


def decrypt_text(encrypted_text: str) -> str:
    """
    رمزگشایی متن
    اگه رمز نباشه (متن قدیمی)، همون متن برمی‌گرده
    اگه خطا بده، رشته خالی برمی‌گرده
    """
    if not encrypted_text:
        return encrypted_text

    fernet = _get_fernet()
    if not fernet:
        return encrypted_text

    try:
        decrypted_bytes = fernet.decrypt(encrypted_text.encode())
        return decrypted_bytes.decode()
    except InvalidToken:
        # متن رمز نشده - همون رو برگردون (سازگاری با داده‌های قدیمی)
        return encrypted_text
    except Exception as e:
        log.error(f"خطا در رمزگشایی: {e}")
        return ""


def mask_token(token: str, visible_start: int = 6, visible_end: int = 4) -> str:
    """
    مخفی کردن توکن برای نمایش/لاگ
    مثال: bot123:xxxx-xxxx-xxxx → bot123:...xxxx
    """
    if not token or len(token) < 10:
        return "***"

    start = token[:visible_start]
    end = token[-visible_end:]
    return f"{start}...{end}"