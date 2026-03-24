"""Migration 004 — Import blocks with resume support.

Imports block headers from the Chia SQLite database into PostgreSQL.
Progress is stored in sync_state.blocks_height — can be interrupted and resumed.

Usage:
    python db/004_import_blocks.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from psycopg2.extras import execute_values  # noqa: E402
from tqdm import tqdm  # noqa: E402

from config import BATCH_SIZE_BLOCKS, IMPORT_STEP  # noqa: E402
from utils import (  # noqa: E402
    connect_pg,
    connect_sqlite,
    ensure_sync_state,
    get_sqlite_tip,
    get_state,
    set_state,
)

_BLOCKS_QUERY = """
    SELECT
        fb.height,
        fb.header_hash,
        fb.prev_hash,
        COALESCE(MAX(cr_cb.timestamp), 0) AS block_timestamp,

        CASE
            WHEN EXISTS (
                SELECT 1 FROM coin_record cr_s
                WHERE cr_s.spent_index = fb.height LIMIT 1
            )
              OR EXISTS (
                SELECT 1 FROM coin_record cr_o
                WHERE cr_o.confirmed_index = fb.height AND cr_o.coinbase = 0 LIMIT 1
            )
            THEN 1
            ELSE 0
        END AS is_transaction_block

    FROM full_blocks fb
    LEFT JOIN coin_record cr_cb
           ON cr_cb.confirmed_index = fb.height AND cr_cb.coinbase = 1

    WHERE fb.in_main_chain = 1
      AND fb.height >= ?
      AND fb.height <= ?

    GROUP BY fb.height, fb.header_hash, fb.prev_hash
    ORDER BY fb.height
"""


# ---------------------------------------------------------------------------
# Batch insert
# ---------------------------------------------------------------------------

def _flush_blocks(cur, conn, batch: list) -> None:
    execute_values(
        cur,
        """
        INSERT INTO blocks (height, header_hash, prev_hash, timestamp, is_transaction_block)
        VALUES %s
        ON CONFLICT (height) DO NOTHING
        """,
        batch,
        page_size=BATCH_SIZE_BLOCKS,
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

        last = get_state(pg_conn, "blocks_height", default=-1)
        if last < 0:
            with pg_conn.cursor() as cur:
                cur.execute("SELECT COALESCE(MAX(height), -1) FROM blocks")
                last = int(cur.fetchone()[0])
            set_state(pg_conn, "blocks_height", last)

        start = last + 1
        print(f"Resume: blocks_height={last} -> start={start}")

        if start > tip:
            print("Blocks already at tip.")
            return

        total = tip - last
        s_cur = sqlite_conn.cursor()
        p_cur = pg_conn.cursor()

        with tqdm(total=total, desc="Blocks", unit="blk") as pbar:
            while start <= tip:
                end = min(start + IMPORT_STEP - 1, tip)

                s_cur.execute(_BLOCKS_QUERY, (start, end))

                batch: list = []
                for height, header_hash, prev_hash, ts, is_tx in s_cur:
                    batch.append((int(height), header_hash, prev_hash, int(ts), bool(is_tx)))

                    if len(batch) >= BATCH_SIZE_BLOCKS:
                        _flush_blocks(p_cur, pg_conn, batch)
                        pbar.update(len(batch))
                        batch.clear()

                if batch:
                    _flush_blocks(p_cur, pg_conn, batch)
                    pbar.update(len(batch))

                set_state(pg_conn, "blocks_height", end)
                start = end + 1

        s_cur.close()
        p_cur.close()

        print("Block import complete.")

    finally:
        pg_conn.close()
        sqlite_conn.close()


if __name__ == "__main__":
    main()
