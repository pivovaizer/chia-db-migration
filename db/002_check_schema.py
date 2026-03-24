"""Миграция 002 — Проверка структуры схемы PostgreSQL.

Выводит список таблиц, колонок и индексов для быстрой диагностики.
Запускай после 001_init_schema.py чтобы убедиться, что схема создана корректно.

Использование:
    python db/002_check_schema.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import connect_pg  # noqa: E402


def query(conn, sql: str, params: tuple = ()) -> list:
    """Выполнить SQL и вернуть все строки результата."""
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def main() -> None:
    conn = connect_pg()
    try:
        # --- Список таблиц ---
        print("\n📌 Таблицы в схеме public:")
        for (name,) in query(conn, """
            SELECT tablename
            FROM pg_catalog.pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """):
            print(f"  - {name}")

        # --- Колонки: blocks ---
        print("\n📌 Колонки: blocks")
        for row in query(conn, """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'blocks'
            ORDER BY ordinal_position;
        """):
            print(" ", row)

        # --- Колонки: coins ---
        print("\n📌 Колонки: coins")
        for row in query(conn, """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'coins'
            ORDER BY ordinal_position;
        """):
            print(" ", row)

        # --- Индексы: coins ---
        print("\n📌 Индексы: coins")
        for name, definition in query(conn, """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public' AND tablename = 'coins'
            ORDER BY indexname;
        """):
            print(f"  - {name}\n    {definition}")

        print("\n✅ Готово.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
