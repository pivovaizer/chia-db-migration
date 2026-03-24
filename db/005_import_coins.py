"""Migration 005 — Import coins with resume support.

Imports coin records (UTXO) from the Chia SQLite database into PostgreSQL.
Progress is stored in sync_state.coins_height — can be interrupted and resumed.

Usage:
    python db/005_import_coins.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from psycopg2.extras import execute_values  # noqa: E402
from tqdm import tqdm  # noqa: E402

from config import BATCH_SIZE_COINS, IMPORT_STEP  # noqa: E402
from utils import (  # noqa: E402
    blob_to_int,
    connect_pg,
    connect_sqlite,
    ensure_sync_state,
    get_sqlite_tip,
    get_state,
    set_state,
)

_COINS_QUERY = """
    SELECT coin_name, puzzle_hash, coin_parent, amount,
           confirmed_index, spent_index, coinbase
    FROM coin_record
    WHERE confirmed_index >= ?
      AND confirmed_index <= ?
    ORDER BY confirmed_index
"""


# ---------------------------------------------------------------------------
# Batch insert
# ---------------------------------------------------------------------------

def _flush_coins(cur, conn, batch: list) -> None:
    execute_values(
        cur,
        """
        INSERT INTO coins (coin_id, puzzle_hash, parent_coin_id, amount, created_height, spent_height, coinbase)
        VALUES %s
        ON CONFLICT (coin_id) DO NOTHING
        """,
        batch,
        page_size=BATCH_SIZE_COINS,
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("Connecting to SQLite...")
    sqlite_conn = connect_sqlite()

    print("Connecting to PostgreSQL...")
    pg_conn = connect_pg()

    try:
        ensure_sync_state(pg_conn)

        tip = get_sqlite_tip(sqlite_conn)
        print(f"SQLite tip (main chain): {tip}")

        last = get_state(pg_conn, "coins_height", default=-1)
        if last < 0:
            with pg_conn.cursor() as cur:
                cur.execute("SELECT COALESCE(MAX(created_height), -1) FROM coins")
                last = int(cur.fetchone()[0])
            set_state(pg_conn, "coins_height", last)

        start = last + 1
        print(f"Resume: coins_height={last} -> start={start}")

        if start > tip:
            print("Coins already at tip.")
            return

        # Count total coins to import for accurate progress bar
        s_count = sqlite_conn.cursor()
        s_count.execute(
            "SELECT COUNT(*) FROM coin_record WHERE confirmed_index >= ?",
            (start,),
        )
        total_coins = s_count.fetchone()[0]
        s_count.close()
        print(f"Coins to import: {total_coins:,}")

        s_cur = sqlite_conn.cursor()
        p_cur = pg_conn.cursor()

        with tqdm(total=total_coins, desc="Coins", unit="coin") as pbar:
            while start <= tip:
                end = min(start + IMPORT_STEP - 1, tip)

                s_cur.execute(_COINS_QUERY, (start, end))

                batch: list = []
                for coin_id, ph, parent, amount_blob, created_h, spent_h, coinbase in s_cur:
                    amount = blob_to_int(amount_blob)
                    spent_height = None if (spent_h is None or int(spent_h) == 0) else int(spent_h)

                    batch.append((coin_id, ph, parent, amount, int(created_h), spent_height, bool(coinbase)))

                    if len(batch) >= BATCH_SIZE_COINS:
                        _flush_coins(p_cur, pg_conn, batch)
                        pbar.update(len(batch))
                        batch.clear()

                if batch:
                    _flush_coins(p_cur, pg_conn, batch)
                    pbar.update(len(batch))

                set_state(pg_conn, "coins_height", end)
                start = end + 1

        s_cur.close()
        p_cur.close()

        print("Coin import complete.")

    finally:
        pg_conn.close()
        sqlite_conn.close()


if __name__ == "__main__":
    main()
