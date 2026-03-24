"""Вспомогательные функции для работы с PostgreSQL.

Предоставляет:
  - Фабрику подключения (connect_pg)
  - Управление таблицей sync_state для возобновляемого импорта

sync_state — это простое key/value-хранилище в PostgreSQL, которое позволяет
скриптам импорта продолжить работу с того места, где они остановились.
"""
from __future__ import annotations

import psycopg2
from psycopg2.extensions import connection as PgConnection

from config import PG_DSN


# ---------------------------------------------------------------------------
# Подключение
# ---------------------------------------------------------------------------

def connect_pg() -> PgConnection:
    """Открыть и вернуть новое psycopg2-соединение (autocommit=False).

    Returns:
        Открытое соединение с PostgreSQL.
    """
    conn = psycopg2.connect(PG_DSN)
    conn.autocommit = False
    return conn


# ---------------------------------------------------------------------------
# sync_state — контрольные точки для возобновляемого импорта
# ---------------------------------------------------------------------------

def ensure_sync_state(conn: PgConnection) -> None:
    """Создать таблицу sync_state, если она ещё не существует.

    sync_state хранит пары ключ/значение (TEXT → BIGINT), которые позволяют
    скриптам импорта продолжить после прерывания или ошибки.

    Args:
        conn: Активное соединение с PostgreSQL.
    """
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sync_state (
                key   TEXT   PRIMARY KEY,
                value BIGINT NOT NULL
            );
        """)
    conn.commit()


def get_state(conn: PgConnection, key: str, default: int = -1) -> int:
    """Прочитать значение прогресса из sync_state.

    Args:
        conn:    Активное соединение с PostgreSQL.
        key:     Ключ состояния (например, "blocks_height").
        default: Значение по умолчанию, если ключ отсутствует.

    Returns:
        Сохранённое целое значение или *default*.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT value FROM sync_state WHERE key = %s", (key,))
        row = cur.fetchone()
    return int(row[0]) if row else default


def set_state(conn: PgConnection, key: str, value: int) -> None:
    """Сохранить (upsert) значение прогресса в sync_state и сделать commit.

    Args:
        conn:  Активное соединение с PostgreSQL.
        key:   Ключ состояния.
        value: Значение высоты блока или счётчика для сохранения.
    """
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO sync_state (key, value)
            VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """, (key, int(value)))
    conn.commit()
