"""Migration 006 — Create secondary indexes after full import.

Run AFTER import (004/005) is complete and tables are populated.
Creating indexes after loading data is much faster than keeping them
active during INSERTs.

All operations are idempotent (IF NOT EXISTS).

Usage:
    python db/006_create_indexes.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import connect_pg  # noqa: E402

# ---------------------------------------------------------------------------
# DDL — index creation
# ---------------------------------------------------------------------------

DDL = """
-- blocks
CREATE INDEX IF NOT EXISTS idx_blocks_timestamp ON blocks (timestamp);

-- coins: address balance / UTXO
CREATE INDEX IF NOT EXISTS idx_coins_ph_spent   ON coins (puzzle_hash, spent_height);

-- coins: address coin history
CREATE INDEX IF NOT EXISTS idx_coins_ph_created ON coins (puzzle_hash, created_height);

-- coins: block outputs
CREATE INDEX IF NOT EXISTS idx_coins_created_h  ON coins (created_height);

-- coins: block inputs (spent)
CREATE INDEX IF NOT EXISTS idx_coins_spent_h    ON coins (spent_height);

-- coins: block rewards
CREATE INDEX IF NOT EXISTS idx_coins_coinbase_h ON coins (coinbase, created_height);

-- block_tx_details: lookup by header_hash
CREATE INDEX IF NOT EXISTS idx_block_tx_details_hash ON block_tx_details (header_hash);
"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("Connecting to PostgreSQL...")
    conn = connect_pg()
    try:
        with conn.cursor() as cur:
            print("Creating indexes (this may take a few minutes)...")
            cur.execute(DDL)
        conn.commit()
        print("Indexes created.")
    except Exception as exc:
        conn.rollback()
        print("Error:", exc)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
