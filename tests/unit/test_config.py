"""
تست تنظیمات برنامه
اولین تست ما! چک میکنه تنظیمات درست خونده میشن
"""


def test_settings_exist():
    """چک کن کلاس Settings وجود داره"""
    from app.config import Settings
    s = Settings()
    assert s is not None


def test_bot_token_is_string():
    """چک کن BOT_TOKEN رشته‌ست"""
    from app.config import settings
    assert isinstance(settings.BOT_TOKEN, str)


def test_admin_chat_id_is_integer():
    """چک کن ADMIN_CHAT_ID عدده"""
    from app.config import settings
    assert isinstance(settings.ADMIN_CHAT_ID, int)


def test_debug_is_boolean():
    """چک کن DEBUG بولینه"""
    from app.config import settings
    assert isinstance(settings.DEBUG, bool)