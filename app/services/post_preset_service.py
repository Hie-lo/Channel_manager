"""
سرویس مدیریت نمونه‌های آماده‌ی پست (Post Template Presets)

ادمین این نمونه‌ها را طراحی می‌کند؛ مشتری فقط از بینشان انتخاب می‌کند.
هر preset متعلق به یک نوع کسب‌وکار است و اختیاری به یک زیردسته محدود می‌شود.
"""

from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import PostTemplatePreset, Customer
from app.utils.time import utc_now_naive
from app.utils.logger import log


# ─────────────────────────────────────────────────────────────────────────────
# CRUD ادمین
# ─────────────────────────────────────────────────────────────────────────────

async def create_preset(
    session: AsyncSession,
    business_type_key: str,
    name_fa: str,
    template_text: str,
    subcategory_key: str | None = None,
    display_order: int = 0,
) -> PostTemplatePreset:
    """ساخت یک preset جدید (فقط ادمین)"""
    preset = PostTemplatePreset(
        business_type_key=business_type_key,
        subcategory_key=subcategory_key,
        name_fa=name_fa,
        template_text=template_text,
        is_active=True,
        display_order=display_order,
        created_at=utc_now_naive(),
        updated_at=utc_now_naive(),
    )
    session.add(preset)
    await session.commit()
    await session.refresh(preset)
    log.info(f"[PostPreset] preset جدید ساخته شد: id={preset.id}, biz={business_type_key}")
    return preset


async def get_preset_by_id(
    session: AsyncSession,
    preset_id: int,
) -> PostTemplatePreset | None:
    """پیدا کردن preset با آیدی (نسخه ایمن)"""
    result = await session.execute(
        select(PostTemplatePreset).where(PostTemplatePreset.id == preset_id).limit(1)
    )
    return result.scalars().first()


async def list_all_presets_for_admin(
    session: AsyncSession,
    business_type_key: str,
) -> list[PostTemplatePreset]:
    """همه‌ی preset های یک کسب‌وکار برای ادمین (فعال و غیرفعال)"""
    result = await session.execute(
        select(PostTemplatePreset)
        .where(PostTemplatePreset.business_type_key == business_type_key)
        .order_by(PostTemplatePreset.display_order, PostTemplatePreset.id)
    )
    return list(result.scalars().all())


async def list_presets_for_customer(
    session: AsyncSession,
    business_type_key: str,
    subcategory_key: str | None = None,
) -> list[PostTemplatePreset]:
    """
    preset های قابل‌انتخاب یک مشتری: عمومیِ کسب‌وکار (subcategory_key=None)
    + مخصوصِ همون زیردسته، در یک کوئری.
    """
    conditions = [
        PostTemplatePreset.business_type_key == business_type_key,
        PostTemplatePreset.is_active == True,
    ]
    if subcategory_key:
        conditions.append(
            or_(
                PostTemplatePreset.subcategory_key.is_(None),
                PostTemplatePreset.subcategory_key == subcategory_key,
            )
        )
    else:
        conditions.append(PostTemplatePreset.subcategory_key.is_(None))

    result = await session.execute(
        select(PostTemplatePreset)
        .where(and_(*conditions))
        .order_by(PostTemplatePreset.display_order, PostTemplatePreset.id)
    )
    return list(result.scalars().all())


async def update_preset_text(
    session: AsyncSession,
    preset_id: int,
    template_text: str,
) -> PostTemplatePreset | None:
    preset = await get_preset_by_id(session, preset_id)
    if not preset:
        return None
    preset.template_text = template_text
    preset.updated_at = utc_now_naive()
    await session.commit()
    await session.refresh(preset)
    return preset


async def rename_preset(
    session: AsyncSession,
    preset_id: int,
    name_fa: str,
) -> PostTemplatePreset | None:
    preset = await get_preset_by_id(session, preset_id)
    if not preset:
        return None
    preset.name_fa = name_fa
    preset.updated_at = utc_now_naive()
    await session.commit()
    await session.refresh(preset)
    return preset


async def set_preset_active(
    session: AsyncSession,
    preset_id: int,
    is_active: bool,
) -> PostTemplatePreset | None:
    """فعال/غیرفعال کردن preset (soft-delete امن — مشتری‌های قبلی نمی‌شکنن)"""
    preset = await get_preset_by_id(session, preset_id)
    if not preset:
        return None
    preset.is_active = is_active
    preset.updated_at = utc_now_naive()
    await session.commit()
    await session.refresh(preset)
    return preset


async def delete_preset(
    session: AsyncSession,
    preset_id: int,
) -> bool:
    """حذف کامل preset (فقط وقتی مطمئنیم هیچ مشتری‌ای انتخابش نکرده)"""
    preset = await get_preset_by_id(session, preset_id)
    if not preset:
        return False

    # جلوگیری از حذف چیزی که هنوز یه مشتری بهش وابسته‌ست
    result = await session.execute(
        select(Customer.id).where(Customer.selected_post_preset_id == preset_id).limit(1)
    )
    if result.scalars().first():
        log.warning(f"[PostPreset] حذف preset {preset_id} رد شد: هنوز مشتری بهش وصل است")
        return False

    await session.delete(preset)
    await session.commit()
    log.info(f"[PostPreset] preset حذف شد: id={preset_id}")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# انتخاب مشتری
# ─────────────────────────────────────────────────────────────────────────────

async def select_preset_for_customer(
    session: AsyncSession,
    customer_id: int,
    preset_id: int,
) -> bool:
    """ثبت انتخاب preset برای یک مشتری"""
    result = await session.execute(
        select(Customer).where(Customer.id == customer_id).limit(1)
    )
    customer = result.scalars().first()
    if not customer:
        return False

    customer.selected_post_preset_id = preset_id
    customer.updated_at = utc_now_naive()
    await session.commit()
    log.info(f"[PostPreset] مشتری {customer_id} preset {preset_id} را انتخاب کرد")
    return True


async def get_selected_preset(
    session: AsyncSession,
    customer_id: int,
) -> PostTemplatePreset | None:
    """preset فعلاً انتخاب‌شده‌ی یک مشتری (اگر انتخاب نکرده باشد None)"""
    result = await session.execute(
        select(Customer).where(Customer.id == customer_id).limit(1)
    )
    customer = result.scalars().first()
    if not customer or not customer.selected_post_preset_id:
        return None

    return await get_preset_by_id(session, customer.selected_post_preset_id)