"""
تنظیمات کلی برنامه
همه تنظیمات از فایل .env خوانده میشن
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# مسیر ریشه پروژه
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

# خواندن قطعی فایل .env
load_dotenv(dotenv_path=ENV_FILE)


class Settings:
    """تنظیمات اصلی برنامه"""

    # Telegram
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_CHAT_ID: int = int(os.getenv("ADMIN_CHAT_ID", "0"))

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    # AI
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")
    AI_MODEL: str = os.getenv("AI_MODEL", "meta-llama/llama-3.1-8b-instruct:free")

    # Encryption
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")

    # App
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()