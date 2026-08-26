"""
سرویس مدیریت BusinessMappingProfile
ذخیره و بازیابی دائمی پروفایل مپینگ هر کسب‌وکار.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import BusinessMappingProfile
from app.services.data_input.smart_detector import (
    SmartDetectionResult,
    ColumnDetectionResult,
    DetectionMethod,
)
from app.utils.time import utc_now_naive
from app.utils.logger import log


# ─────────────────────────────────────────────────────────────────────────────

async def get_mapping_profile(
    session: AsyncSession,
    customer_id: int,
) -> BusinessMappingProfile | None:
    """دریافت پروفایل مپینگ مشتری"""
    result = await session.execute(
        select(BusinessMappingProfile)
        .where(BusinessMappingProfile.customer_id == customer_id)
        .limit(1)
    )
    return result.scalars().first()


async def save_mapping_from_detection(
    session: AsyncSession,
    customer_id: int,
    detection: SmartDetectionResult,
) -> BusinessMappingProfile:
    """
    ذخیره یا آپدیت پروفایل مپینگ بر اساس نتیجه SmartDetection.
    """
    profile = await get_mapping_profile(session, customer_id)

    col   = detection.columns
    sheet = detection.sheet

    data = {
        "detected_sheet_name": sheet.sheet_name,
        "subcategory_key":     sheet.subcategory.key if sheet.subcategory else None,
        "detection_method":    col.method,
        "confidence_score":    round(detection.overall_score, 3),
        "column_map":          col.column_map,
        "raw_headers":         col.raw_headers,
        "is_confirmed":        not detection.needs_wizard and not detection.needs_confirm,
        "updated_at":          utc_now_naive(),
    }

    if profile:
        for k, v in data.items():
            setattr(profile, k, v)
    else:
        profile = BusinessMappingProfile(customer_id=customer_id, **data)
        session.add(profile)

    await session.commit()
    await session.refresh(profile)
    log.info(f"[MappingService] پروفایل مپینگ ذخیره شد: customer={customer_id}")
    return profile


async def save_mapping_from_wizard(
    session: AsyncSession,
    customer_id: int,
    sheet_name: str,
    subcategory_key: str,
    column_map: dict[str, int],
    ignored_fields: list[str],
    raw_headers: list[str],
) -> BusinessMappingProfile:
    """
    ذخیره مپینگ بعد از تکمیل ویزارد توسط کاربر.
    """
    profile = await get_mapping_profile(session, customer_id)

    data = {
        "detected_sheet_name": sheet_name,
        "subcategory_key":     subcategory_key,
        "detection_method":    "wizard",
        "confidence_score":    1.0,
        "column_map":          column_map,
        "ignored_fields":      ignored_fields,
        "raw_headers":         raw_headers,
        "is_confirmed":        True,
        "updated_at":          utc_now_naive(),
    }

    if profile:
        for k, v in data.items():
            setattr(profile, k, v)
    else:
        profile = BusinessMappingProfile(customer_id=customer_id, **data)
        session.add(profile)

    await session.commit()
    await session.refresh(profile)
    log.info(f"[MappingService] پروفایل ویزارد ذخیره شد: customer={customer_id}")
    return profile


async def confirm_mapping(
    session: AsyncSession,
    customer_id: int,
) -> BusinessMappingProfile | None:
    """تأیید مپینگ توسط کاربر (برای حالت needs_confirm)"""
    profile = await get_mapping_profile(session, customer_id)
    if not profile:
        return None

    profile.is_confirmed = True
    profile.updated_at   = utc_now_naive()
    await session.commit()
    await session.refresh(profile)
    return profile


async def delete_mapping_profile(
    session: AsyncSession,
    customer_id: int,
) -> None:
    """حذف پروفایل مپینگ (برای شروع مجدد)"""
    profile = await get_mapping_profile(session, customer_id)
    if profile:
        await session.delete(profile)
        await session.commit()
        log.info(f"[MappingService] پروفایل مپینگ حذف شد: customer={customer_id}")
