"""Migration 002 — Verify PostgreSQL schema structure.

Prints tables, columns, and indexes for quick diagnostics.
Run after 001_init_schema.py to confirm the schema was created correctly.

Usage:
    python db/002_check_schema.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import connect_pg  # noqa: E402


def query(conn, sql: str, params: tuple = ()) -> list:
    """Execute SQL and return all result rows."""
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def main() -> None:
    conn = connect_pg()
    try:
        print("\nTables in public schema:")
        for (name,) in query(conn, """
            SELECT tablename
            FROM pg_catalog.pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """):
            print(f"  - {name}")

        print("\nColumns: blocks")
        for row in query(conn, """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'blocks'
            ORDER BY ordinal_position;
        """):
            print(" ", row)

        print("\nColumns: coins")
        for row in query(conn, """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'coins'
            ORDER BY ordinal_position;
        """):
            print(" ", row)

        print("\nIndexes: coins")
        for name, definition in query(conn, """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public' AND tablename = 'coins'
            ORDER BY indexname;
        """):
            print(f"  - {name}\n    {definition}")

        print("\nDone.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
