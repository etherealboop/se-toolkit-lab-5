#!/usr/bin/env python3
"""Test script for load_logs function."""

import asyncio
import sys
sys.path.insert(0, 'backend')

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.settings import settings
from app.etl import fetch_items, fetch_logs, load_items, load_logs
from app.models.interaction import InteractionLog


def get_database_url() -> str:
    return (
        f"postgresql+asyncpg://{settings.db_user}:{settings.db_password}"
        f"@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    )


async def main():
    print("Testing load_logs()...")
    
    # Create engine and ensure tables exist
    engine = create_async_engine(get_database_url())
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    # Fetch items and logs from API
    items = await fetch_items()
    print(f"✓ Получено {len(items)} элементов из API")
    
    # Load items first
    async with AsyncSession(engine) as session:
        await load_items(items, session)
        print("✓ Items загружены в БД")
    
    # Fetch logs (just a small batch for testing)
    logs = await fetch_logs()
    print(f"✓ Получено {len(logs)} логов из API")
    
    # Load logs
    async with AsyncSession(engine) as session:
        new_count = await load_logs(logs, items, session)
        print(f"✓ Создано {new_count} новых записей в БД")
        
        # Verify by querying
        result = await session.exec(select(InteractionLog))
        all_interactions = result.all()
        print(f"✓ Всего записей interactions в БД: {len(all_interactions)}")
        
        # Show some examples
        print("\nПримеры записей:")
        for interaction in all_interactions[:3]:
            print(f"  - id={interaction.id}, learner_id={interaction.learner_id}, item_id={interaction.item_id}, score={interaction.score}")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
