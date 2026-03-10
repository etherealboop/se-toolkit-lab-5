#!/usr/bin/env python3
"""Test script for fetch_logs function."""

import asyncio
import sys
sys.path.insert(0, 'backend')

from app.etl import fetch_logs


async def main():
    print("Testing fetch_logs()...")
    try:
        logs = await fetch_logs()
        print(f"✓ Успешно получено {len(logs)} логов")
        if logs:
            print("\nПервые 3 лога:")
            for log in logs[:3]:
                print(f"  - {log}")
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
