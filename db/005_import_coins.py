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

# SQL-запрос для выборки монет из SQLite (один диапазон высот по created_height)
_COINS_QUERY = """
    SELECT coin_name, puzzle_hash, coin_parent, amount,
           confirmed_index, spent_index, coinbase
    FROM coin_record
    WHERE confirmed_index >= ?
      AND confirmed_index <= ?
    ORDER BY confirmed_index
"""


# ---------------------------------------------------------------------------
# Импорт одного диапазона монет
# ---------------------------------------------------------------------------

def import_coins_range(sqlite_conn, pg_conn, start_h: int, end_h: int) -> None:
    """Импортировать монеты (по created_height) из [start_h, end_h].

    Args:
        sqlite_conn: Открытое соединение с SQLite (Chia).
        pg_conn:     Открытое соединение с PostgreSQL.
        start_h:     Начальная высота диапазона (включительно).
        end_h:       Конечная высота диапазона (включительно).
    """
    s_cur = sqlite_conn.cursor()
    p_cur = pg_conn.cursor()

    print(f"\n🪙 Монеты {start_h}..{end_h}")
    s_cur.execute(_COINS_QUERY, (start_h, end_h))

    batch: list = []
    for coin_id, ph, parent, amount_blob, created_h, spent_h, coinbase in tqdm(s_cur, desc="Coins", unit="coin"):
        amount       = blob_to_int(amount_blob)
        # spent_index = 0 в SQLite означает "не потрачена" (NULL в нашей схеме)
        spent_height = None if (spent_h is None or int(spent_h) == 0) else int(spent_h)

        batch.append((coin_id, ph, parent, amount, int(created_h), spent_height, bool(coinbase)))

        if len(batch) >= BATCH_SIZE_COINS:
            _flush_coins(p_cur, pg_conn, batch)
            batch.clear()

    if batch:
        _flush_coins(p_cur, pg_conn, batch)

    p_cur.close()
    s_cur.close()
    print("✅ Диапазон монет готов.")


def _flush_coins(cur, conn, batch: list) -> None:
    """Вставить батч монет в PostgreSQL и сделать commit."""
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
# Точка входа — главный цикл с resume
# ---------------------------------------------------------------------------

def main() -> None:
    print("🔗 Подключение к SQLite...")
    sqlite_conn = connect_sqlite()  # read-only

    print("🔗 Подключение к PostgreSQL...")
    pg_conn = connect_pg()

    try:
        ensure_sync_state(pg_conn)

        tip = get_sqlite_tip(sqlite_conn)
        print(f"📌 SQLite tip (main chain): {tip}")

        # Читаем последний сохранённый прогресс
        last = get_state(pg_conn, "coins_height", default=-1)
        if last < 0:
            # Sync_state пустой — подтягиваем факт из уже загруженных данных
            with pg_conn.cursor() as cur:
                cur.execute("SELECT COALESCE(MAX(created_height), -1) FROM coins")
                last = int(cur.fetchone()[0])
            set_state(pg_conn, "coins_height", last)

        start = last + 1
        print(f"📌 Resume: coins_height={last} -> start={start}")

        if start > tip:
            print("✅ Монеты уже на tip.")
            return

        while start <= tip:
            end = min(start + IMPORT_STEP - 1, tip)
            import_coins_range(sqlite_conn, pg_conn, start, end)
            set_state(pg_conn, "coins_height", end)
            print(f"✅ Прогресс: {end}")
            start = end + 1

        print("🎉 Импорт монет завершён.")

    finally:
        pg_conn.close()
        sqlite_conn.close()


if __name__ == "__main__":
    main()
