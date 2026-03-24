"""Migration 006 — Create secondary indexes after full import.

Run AFTER import (004/005) is complete and tables are populated.
Создавать индексы после загрузки данных — намного быстрее, чем держать их
активными во время INSERT (PostgreSQL перестраивает индекс инкрементально).

Все операции идемпотентны (IF NOT EXISTS).

Использование:
    python db/008_create_index_after_import.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import connect_pg  # noqa: E402

# ---------------------------------------------------------------------------
# DDL — создание индексов
# ---------------------------------------------------------------------------

DDL = """
-- -----------------------------------------------------------------------
-- blocks
-- -----------------------------------------------------------------------

-- Поиск блоков по временному диапазону
CREATE INDEX IF NOT EXISTS idx_blocks_timestamp ON blocks (timestamp);


-- -----------------------------------------------------------------------
-- coins
-- -----------------------------------------------------------------------

-- Баланс / UTXO адреса: WHERE puzzle_hash = ? AND spent_height IS NULL
CREATE INDEX IF NOT EXISTS idx_coins_ph_spent   ON coins (puzzle_hash, spent_height);

-- История монет адреса: WHERE puzzle_hash = ? ORDER BY created_height
CREATE INDEX IF NOT EXISTS idx_coins_ph_created ON coins (puzzle_hash, created_height);

-- Outputs блока: WHERE created_height = ?
CREATE INDEX IF NOT EXISTS idx_coins_created_h  ON coins (created_height);

-- Inputs блока (потраченные): WHERE spent_height = ?
CREATE INDEX IF NOT EXISTS idx_coins_spent_h    ON coins (spent_height);

-- Блочные награды: WHERE coinbase = TRUE AND created_height = ?
CREATE INDEX IF NOT EXISTS idx_coins_coinbase_h ON coins (coinbase, created_height);


-- -----------------------------------------------------------------------
-- block_tx_details
-- -----------------------------------------------------------------------

-- Поиск кэша по header_hash
CREATE INDEX IF NOT EXISTS idx_block_tx_details_hash ON block_tx_details (header_hash);
"""


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

def main() -> None:
    print("🔗 Подключение к PostgreSQL...")
    conn = connect_pg()
    try:
        with conn.cursor() as cur:
            print("🧱 Создание индексов (это может занять несколько минут)...")
            cur.execute(DDL)
        conn.commit()
        print("✅ Индексы созданы.")
    except Exception as exc:
        conn.rollback()
        print("❌ Ошибка:", exc)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
