import pytest
from sqlalchemy import text
from app.database.connection import engine


@pytest.mark.asyncio
async def test_db_can_connect():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1