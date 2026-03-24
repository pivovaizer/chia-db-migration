"""Migration 003 — Full database reset.

Clears all data from blocks, coins, block_tx_details and sync_state tables.
Опционально удаляет вторичные индексы таблицы coins (для ускорения повторного импорта).

⚠️ ВНИМАНИЕ: Это деструктивная операция! Все данные будут удалены.
   Используй только перед полным повторным импортом.

Использование:
    python db/005_reset_db.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import connect_pg  # noqa: E402

# ---------------------------------------------------------------------------
# Настройки
# ---------------------------------------------------------------------------

# True = удалить вторичные индексы coins (ускоряет следующий импорт)
# После импорта пересоздай их: python db/008_create_index_after_import.py
DROP_SECONDARY_COIN_INDEXES: bool = True


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _truncate_all_tables(cur) -> None:
    """Очистить все таблицы через TRUNCATE, безопасно обходя отсутствие sync_state."""
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
    """Удалить все вторичные индексы таблицы coins, оставив только первичный ключ."""
    cur.execute("""
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = 'coins'
        ORDER BY indexname;
    """)
    indexes = cur.fetchall()

    for (name,) in indexes:
        # Пропускаем PRIMARY KEY-индекс (обычно заканчивается на _pkey)
        if name.endswith("_pkey"):
            continue
        cur.execute(f'DROP INDEX IF EXISTS "{name}";')


def _print_counts(cur) -> None:
    """Вывести количество строк в основных таблицах после сброса."""
    for table in ("blocks", "coins", "block_tx_details"):
        cur.execute(f"SELECT COUNT(*) FROM {table};")
        print(f"  {table}: {cur.fetchone()[0]}")


def _print_remaining_indexes(cur) -> None:
    """Вывести оставшиеся индексы таблицы coins."""
    cur.execute("""
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = 'coins'
        ORDER BY indexname;
    """)
    for (name,) in cur.fetchall():
        print(f"  - {name}")


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

def main() -> None:
    conn = connect_pg()
    try:
        with conn.cursor() as cur:
            print("🧹 TRUNCATE всех таблиц...")
            _truncate_all_tables(cur)

            if DROP_SECONDARY_COIN_INDEXES:
                print("🧨 Удаление вторичных индексов coins (оставляем только PK)...")
                _drop_secondary_coin_indexes(cur)
                print("✅ Вторичные индексы удалены.")

        conn.commit()

        # Проверка — выводим счётчики и оставшиеся индексы
        with conn.cursor() as cur:
            print("\n📌 Строк после сброса:")
            _print_counts(cur)

            print("\n📌 Оставшиеся индексы coins:")
            _print_remaining_indexes(cur)

        print("\n🎉 Сброс завершён.")

    except Exception as exc:
        conn.rollback()
        print("❌ Сброс не удался:", exc)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
