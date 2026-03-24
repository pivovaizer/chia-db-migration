"""Миграция 001 — Создание начальной схемы PostgreSQL.

Создаёт три таблицы:
  - blocks          : заголовки блоков главной цепи
  - coins           : UTXO-монеты в стиле Chia
  - block_tx_details: опциональный JSON-кэш деталей блока (RPC)

Все операции идемпотентны (IF NOT EXISTS) — скрипт можно запускать повторно.

Использование:
    python db/001_init_schema.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Добавляем корень проекта в sys.path — иначе импорты utils/config не найдутся
# при запуске из любой директории (не только из корня).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import connect_pg  # noqa: E402

# ---------------------------------------------------------------------------
# DDL — определение схемы
# ---------------------------------------------------------------------------

DDL = """
-- -----------------------------------------------------------------------
-- blocks — один ряд на каждый заголовок блока главной цепи
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS blocks (
    height               BIGINT  PRIMARY KEY,
    header_hash          BYTEA   UNIQUE NOT NULL,
    prev_hash            BYTEA   NOT NULL,
    timestamp            BIGINT  NOT NULL,
    is_transaction_block BOOLEAN NOT NULL DEFAULT FALSE
);

-- Индекс для поиска блоков по диапазону времени
CREATE INDEX IF NOT EXISTS idx_blocks_timestamp ON blocks (timestamp);


-- -----------------------------------------------------------------------
-- coins — UTXO-модель Chia: один ряд на монету
-- -----------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS coins (
    coin_id        BYTEA  PRIMARY KEY,
    puzzle_hash    BYTEA  NOT NULL,            -- Chia-адрес (puzzle hash)
    parent_coin_id BYTEA  NOT NULL,
    amount         BIGINT NOT NULL CHECK (amount >= 0),   -- в mojo
    created_height BIGINT NOT NULL,            -- блок, в котором монета создана
    spent_height   BIGINT NULL,                -- NULL = монета не потрачена (UTXO)
    coinbase       BOOLEAN NOT NULL DEFAULT FALSE          -- True = блочная награда

    -- FK намеренно не добавлены: они замедляют массовый импорт.
    -- После завершения загрузки их можно включить и провалидировать:
    -- ,CONSTRAINT fk_coins_created FOREIGN KEY (created_height) REFERENCES blocks(height)
    -- ,CONSTRAINT fk_coins_spent   FOREIGN KEY (spent_height)   REFERENCES blocks(height)
);

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
-- block_tx_details — опциональный JSON-кэш деталей блока (из RPC)
-- -----------------------------------------------------------------------
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
# Точка входа
# ---------------------------------------------------------------------------

def main() -> None:
    print("🔗 Подключение к PostgreSQL...")
    conn = connect_pg()
    try:
        with conn.cursor() as cur:
            print("🧱 Применение DDL-схемы...")
            cur.execute(DDL)
        conn.commit()
        print("✅ Схема создана успешно.")
    except Exception as exc:
        conn.rollback()
        print("❌ Миграция не удалась:", exc)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
