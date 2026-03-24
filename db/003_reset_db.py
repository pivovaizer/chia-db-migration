"""Migration 003 — Full database reset.

Clears all data from blocks, coins, block_tx_details and sync_state tables.
Optionally drops secondary indexes on coins to speed up the next import.

WARNING: This is a destructive operation. All data will be deleted.
Use only before a full re-import.

Usage:
    python db/003_reset_db.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import connect_pg  # noqa: E402

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

# True = drop secondary coin indexes (speeds up the next import)
# After import, recreate them with: python db/006_create_indexes.py
DROP_SECONDARY_COIN_INDEXES: bool = True


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _truncate_all_tables(cur) -> None:
    """Truncate all tables, safely handling missing sync_state."""
    cur.execute("""
        DO $$
        BEGIN
            IF to_regclass('public.sync_state') IS NOT NULL THEN
                EXECUTE 'TRUNCATE TABLE block_tx_details, coins, blocks, sync_state RESTART IDENTITY;';
            ELSE
                EXECUTE 'TRUNCATE TABLE block_tx_details, coins, blocks RESTART IDENTITY;';
            END IF;
        END $$;
    """)


def _drop_secondary_coin_indexes(cur) -> None:
    """Drop all secondary indexes on coins, keeping only the primary key."""
    cur.execute("""
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = 'coins'
        ORDER BY indexname;
    """)
    indexes = cur.fetchall()

    for (name,) in indexes:
        if name.endswith("_pkey"):
            continue
        cur.execute(f'DROP INDEX IF EXISTS "{name}";')


def _print_counts(cur) -> None:
    """Print row counts for main tables after reset."""
    for table in ("blocks", "coins", "block_tx_details"):
        cur.execute(f"SELECT COUNT(*) FROM {table};")
        print(f"  {table}: {cur.fetchone()[0]}")


def _print_remaining_indexes(cur) -> None:
    """Print remaining indexes on coins table."""
    cur.execute("""
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = 'coins'
        ORDER BY indexname;
    """)
    for (name,) in cur.fetchall():
        print(f"  - {name}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    conn = connect_pg()
    try:
        with conn.cursor() as cur:
            print("Truncating all tables...")
            _truncate_all_tables(cur)

            if DROP_SECONDARY_COIN_INDEXES:
                print("Dropping secondary coin indexes (keeping PK only)...")
                _drop_secondary_coin_indexes(cur)
                print("Secondary indexes dropped.")

        conn.commit()

        with conn.cursor() as cur:
            print("\nRow counts after reset:")
            _print_counts(cur)

            print("\nRemaining indexes on coins:")
            _print_remaining_indexes(cur)

        print("\nReset complete.")

    except Exception as exc:
        conn.rollback()
        print("Reset failed:", exc)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
