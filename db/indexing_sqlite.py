"""Create indexes in Chia's SQLite database to speed up import queries.

Run BEFORE import (004/005) to significantly speed up SELECT queries.

Usage:
    python db/indexing_sqlite.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
from tqdm import tqdm

from config import SQLITE_PATH

# ---------------------------------------------------------------------------
# Index definitions: (index_name, table, columns)
# ---------------------------------------------------------------------------
INDEXES = [
    # Single-column indexes
    ("idx_coin_record_confirmed_index",
     "coin_record",
     ("confirmed_index",)),

    ("idx_coin_record_spent_index",
     "coin_record",
     ("spent_index",)),

    ("idx_coin_record_puzzle_hash",
     "coin_record",
     ("puzzle_hash",)),

    # Composite indexes
    ("idx_coin_record_ph_unspent",
     "coin_record",
     ("puzzle_hash", "spent_index")),

    ("idx_coin_record_confirmed_ph",
     "coin_record",
     ("confirmed_index", "puzzle_hash")),

    ("idx_coin_record_ph_confirmed",
     "coin_record",
     ("puzzle_hash", "confirmed_index")),
]


def create_index(conn, index_name, table, columns):
    cols = ", ".join(columns)
    sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({cols});"
    conn.execute(sql)


def main():
    print(f"Connecting to SQLite: {SQLITE_PATH}\n")

    import os
    if not os.path.exists(SQLITE_PATH):
        print(f"SQLite database not found: {SQLITE_PATH}")
        return

    conn = sqlite3.connect(SQLITE_PATH)

    print("Creating indexes:")
    with conn:
        for index in tqdm(INDEXES, desc="Indexes", unit="idx"):
            create_index(conn, *index)

    conn.close()
    print("\nAll indexes created.")


if __name__ == "__main__":
    main()
