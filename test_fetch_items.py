#!/usr/bin/env python3
"""Test script for fetch_items function."""

import asyncio
import sys
sys.path.insert(0, 'backend')

from app.etl import fetch_items


async def main():
    print("Testing fetch_items()...")
    try:
        items = await fetch_items()
        print(f"✓ Успешно получено {len(items)} элементов")
        if items:
            print("\nПервые 3 элемента:")
            for item in items[:3]:
                print(f"  - {item}")
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
