"""
سیستم لاگ‌گیری مرکزی
همه لاگ‌ها از اینجا رد میشن
"""

import sys
from loguru import logger
from app.config import settings


def setup_logger():
    """تنظیم لاگر اصلی برنامه"""

    # حذف لاگر پیش‌فرض
    logger.remove()

    # لاگ در کنسول (ترمینال)
    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
    )

    # لاگ در فایل (برای بررسی بعدی)
    logger.add(
        "logs/bot_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="1 day",      # هر روز فایل جدید
        retention="30 days",   # ۳۰ روز نگه‌داری
        compression="zip",     # فشرده‌سازی فایل‌های قدیمی
        encoding="utf-8",
    )

    return logger


# لاگر آماده استفاده
log = setup_logger()