"""Migration 001 — Create initial PostgreSQL schema.

Creates three tables:
  - blocks          : main chain block headers
  - coins           : Chia UTXO coins
  - block_tx_details: optional JSON cache of block details (RPC)

All operations are idempotent (IF NOT EXISTS) — safe to re-run.

Usage:
    python db/001_init_schema.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import connect_pg  # noqa: E402

# ---------------------------------------------------------------------------
# DDL — schema definition
# ---------------------------------------------------------------------------

DDL = """
-- blocks — one row per main chain block header
CREATE TABLE IF NOT EXISTS blocks (
    height               BIGINT  PRIMARY KEY,
    header_hash          BYTEA   UNIQUE NOT NULL,
    prev_hash            BYTEA   NOT NULL,
    timestamp            BIGINT  NOT NULL,
    is_transaction_block BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_blocks_timestamp ON blocks (timestamp);


-- coins — Chia UTXO model: one row per coin
CREATE TABLE IF NOT EXISTS coins (
    coin_id        BYTEA  PRIMARY KEY,
    puzzle_hash    BYTEA  NOT NULL,
    parent_coin_id BYTEA  NOT NULL,
    amount         BIGINT NOT NULL CHECK (amount >= 0),
    created_height BIGINT NOT NULL,
    spent_height   BIGINT NULL,                -- NULL = unspent (UTXO)
    coinbase       BOOLEAN NOT NULL DEFAULT FALSE

    -- FKs intentionally omitted: they slow down bulk imports.
    -- Can be added after import for validation:
    -- ,CONSTRAINT fk_coins_created FOREIGN KEY (created_height) REFERENCES blocks(height)
    -- ,CONSTRAINT fk_coins_spent   FOREIGN KEY (spent_height)   REFERENCES blocks(height)
);

-- Address balance / UTXO: WHERE puzzle_hash = ? AND spent_height IS NULL
CREATE INDEX IF NOT EXISTS idx_coins_ph_spent   ON coins (puzzle_hash, spent_height);

-- Address coin history: WHERE puzzle_hash = ? ORDER BY created_height
CREATE INDEX IF NOT EXISTS idx_coins_ph_created ON coins (puzzle_hash, created_height);

-- Block outputs: WHERE created_height = ?
CREATE INDEX IF NOT EXISTS idx_coins_created_h  ON coins (created_height);

-- Block inputs (spent): WHERE spent_height = ?
CREATE INDEX IF NOT EXISTS idx_coins_spent_h    ON coins (spent_height);

-- Block rewards: WHERE coinbase = TRUE AND created_height = ?
CREATE INDEX IF NOT EXISTS idx_coins_coinbase_h ON coins (coinbase, created_height);


-- block_tx_details — optional JSON cache of block details (from RPC)
CREATE TABLE IF NOT EXISTS block_tx_details (
    height         BIGINT      PRIMARY KEY REFERENCES blocks (height) ON DELETE CASCADE,
    header_hash    BYTEA       NOT NULL,
    details_json   JSONB       NOT NULL,
    schema_version INT         NOT NULL DEFAULT 1,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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
            print("Applying DDL schema...")
            cur.execute(DDL)
        conn.commit()
        print("Schema created successfully.")
    except Exception as exc:
        conn.rollback()
        print("Migration failed:", exc)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
