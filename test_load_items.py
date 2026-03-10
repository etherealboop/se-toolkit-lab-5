#!/usr/bin/env python3
"""Test script for load_items function."""

import asyncio
import sys
sys.path.insert(0, 'backend')

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.settings import settings
from app.etl import fetch_items, load_items


def get_database_url() -> str:
    return (
        f"postgresql+asyncpg://{settings.db_user}:{settings.db_password}"
        f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    )


async def main():
    print("Testing load_items()...")
    
    # Create engine and ensure tables exist
    engine = create_async_engine(get_database_url())
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    # Fetch items from API
    items = await fetch_items()
    print(f"✓ Получено {len(items)} элементов из API")
    
    # Create session and load items
    async with AsyncSession(engine) as session:
        new_count = await load_items(items, session)
        print(f"✓ Создано {new_count} новых записей в БД")
        
        # Verify by querying
        result = await session.exec(select(ItemRecord))
        all_items = result.all()
        print(f"✓ Всего записей в БД: {len(all_items)}")
        
        # Show some examples
        print("\nПримеры записей:")
        for item in all_items[:5]:
            print(f"  - id={item.id}, type={item.type}, title={item.title}, parent_id={item.parent_id}")
    
    await engine.dispose()


if __name__ == "__main__":
    from sqlmodel import select
    from app.models.item import ItemRecord
    asyncio.run(main())
