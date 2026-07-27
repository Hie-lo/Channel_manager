"""
سرویس مدیریت اتصال Google Sheet
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import GoogleSheetConnection
from app.utils.logger import log
from app.utils.time import utc_now_naive


async def get_sheet_connection(
    session: AsyncSession,
    customer_id: int,
) -> GoogleSheetConnection | None:
    """گرفتن اتصال شیت مشتری"""
    result = await session.execute(
        select(GoogleSheetConnection).where(
            GoogleSheetConnection.customer_id == customer_id
        )
    )
    return result.scalar_one_or_none()


async def create_or_update_sheet_connection(
    session: AsyncSession,
    customer_id: int,
    sheet_url: str,
    sheet_id: str,
    worksheet_name: str = "Sheet1",
) -> GoogleSheetConnection:
    """ایجاد یا آپدیت اتصال شیت"""
    existing = await get_sheet_connection(session, customer_id)

    if existing:
        existing.sheet_url = sheet_url
        existing.sheet_id = sheet_id
        existing.worksheet_name = worksheet_name
        existing.is_active = True
        existing.updated_at = utc_now_naive()
        await session.commit()
        await session.refresh(existing)
        log.info(f"اتصال شیت مشتری {customer_id} آپدیت شد")
        return existing

    connection = GoogleSheetConnection(
        customer_id=customer_id,
        sheet_url=sheet_url,
        sheet_id=sheet_id,
        worksheet_name=worksheet_name,
        is_active=True,
        created_at=utc_now_naive(),
    )
    session.add(connection)
    await session.commit()
    await session.refresh(connection)
    log.info(f"اتصال شیت جدید برای مشتری {customer_id}")
    return connection


async def delete_sheet_connection(
    session: AsyncSession,
    customer_id: int,
) -> bool:
    """حذف اتصال شیت"""
    connection = await get_sheet_connection(session, customer_id)
    if not connection:
        return False

    await session.delete(connection)
    await session.commit()
    log.info(f"اتصال شیت مشتری {customer_id} حذف شد")
    return True


async def update_sync_status(
    session: AsyncSession,
    customer_id: int,
    success: bool,
    error_message: str | None = None,
) -> None:
    """آپدیت وضعیت آخرین sync"""
    connection = await get_sheet_connection(session, customer_id)
    if not connection:
        return

    connection.last_sync_at = utc_now_naive()
    connection.last_sync_status = "SUCCESS" if success else "FAILED"
    connection.last_error = error_message

    await session.commit()


async def get_all_active_sheet_connections(
    session: AsyncSession,
) -> list[GoogleSheetConnection]:
    """گرفتن همه اتصال‌های فعال (برای Job)"""
    result = await session.execute(
        select(GoogleSheetConnection).where(
            GoogleSheetConnection.is_active == True
        )
    )
    return list(result.scalars().all())