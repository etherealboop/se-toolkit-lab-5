#!/usr/bin/env python3
"""Test script for sync function (full ETL pipeline)."""

import asyncio
import sys
sys.path.insert(0, 'backend')

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.settings import settings
from app.etl import sync


def get_database_url() -> str:
    return (
        f"postgresql+asyncpg://{settings.db_user}:{settings.db_password}"
        f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    )


async def main():
    print("Testing sync() - full ETL pipeline...")
    
    # Create engine and ensure tables exist
    engine = create_async_engine(get_database_url())
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    # Run full ETL sync
    async with AsyncSession(engine) as session:
        result = await sync(session)
        print(f"\n✓ ETL pipeline завершена:")
        print(f"  - new_records: {result['new_records']}")
        print(f"  - total_records: {result['total_records']}")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
