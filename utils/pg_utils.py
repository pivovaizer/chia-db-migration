"""PostgreSQL helper functions.

Provides:
  - Connection factory (connect_pg)
  - sync_state table management for resumable imports

sync_state is a simple key/value store in PostgreSQL that allows
import scripts to resume from where they left off.
"""
from __future__ import annotations

import psycopg2
from psycopg2.extensions import connection as PgConnection

from config import PG_DSN


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def connect_pg() -> PgConnection:
    """Open and return a new psycopg2 connection (autocommit=False)."""
    conn = psycopg2.connect(PG_DSN)
    conn.autocommit = False
    return conn


# ---------------------------------------------------------------------------
# sync_state — checkpoints for resumable imports
# ---------------------------------------------------------------------------

def ensure_sync_state(conn: PgConnection) -> None:
    """Create the sync_state table if it doesn't exist yet."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sync_state (
                key   TEXT   PRIMARY KEY,
                value BIGINT NOT NULL
            );
        """)
    conn.commit()


def get_state(conn: PgConnection, key: str, default: int = -1) -> int:
    """Read a progress value from sync_state."""
    with conn.cursor() as cur:
        cur.execute("SELECT value FROM sync_state WHERE key = %s", (key,))
        row = cur.fetchone()
    return int(row[0]) if row else default


def set_state(conn: PgConnection, key: str, value: int) -> None:
    """Upsert a progress value into sync_state and commit."""
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO sync_state (key, value)
            VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """, (key, int(value)))
    conn.commit()
