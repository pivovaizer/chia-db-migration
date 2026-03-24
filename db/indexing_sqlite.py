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

# ----------------------------
# Список индексов
# (index_name, table, columns)
# columns может быть строкой или кортежем
# ----------------------------
INDEXES = [
    # ------------------------
    # БАЗОВЫЕ ИНДЕКСЫ
    # ------------------------

    # Outputs блока (созданные coins)
    ("idx_coin_record_confirmed_index",
     "coin_record",
     ("confirmed_index",)),

    # Inputs блока (потраченные coins)
    ("idx_coin_record_spent_index",
     "coin_record",
     ("spent_index",)),

    # Все coins адреса
    ("idx_coin_record_puzzle_hash",
     "coin_record",
     ("puzzle_hash",)),

    # ------------------------
    # СОСТАВНЫЕ ИНДЕКСЫ (очень важно)
    # ------------------------

    # UTXO адреса:
    # WHERE puzzle_hash = ? AND spent_index IS NULL
    ("idx_coin_record_ph_unspent",
     "coin_record",
     ("puzzle_hash", "spent_index")),

    # Outputs блока с адресами:
    # WHERE confirmed_index = ?
    ("idx_coin_record_confirmed_ph",
     "coin_record",
     ("confirmed_index", "puzzle_hash")),

    # История адреса (in + out)
    # WHERE puzzle_hash = ? ORDER BY confirmed_index
    ("idx_coin_record_ph_confirmed",
     "coin_record",
     ("puzzle_hash", "confirmed_index")),
]

# ----------------------------
# Создание индекса
# ----------------------------
def create_index(conn, index_name, table, columns):
    cols = ", ".join(columns)
    sql = f"""
    CREATE INDEX IF NOT EXISTS {index_name}
    ON {table} ({cols});
    """
    conn.execute(sql)

# ----------------------------
# Основной процесс
# ----------------------------
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

# ----------------------------
# Entry point
# ----------------------------
if __name__ == "__main__":
    main()
