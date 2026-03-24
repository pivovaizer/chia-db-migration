"""SQLite helper functions for the Chia node database.

Provides a safe (read-only by default) connection to the local
blockchain SQLite database and metadata utilities.
"""
from __future__ import annotations

import sqlite3

from config import SQLITE_PATH


def connect_sqlite(
    path: str = SQLITE_PATH,
    *,
    readonly: bool = True,
) -> sqlite3.Connection:
    """Open the Chia SQLite database and return a connection.

    Opens in read-only mode by default to avoid accidentally
    corrupting the live node database.

    Args:
        path:     Path to the .sqlite file (default from config).
        readonly: If True, open in read-only mode (safe for the node).
                  Pass False if you need to create indexes or write.
    """
    import os
    if not os.path.exists(path):
        raise SystemExit(f"SQLite database not found: {path}")

    if readonly:
        uri = f"file:{path}?mode=ro"
        return sqlite3.connect(uri, uri=True)

    return sqlite3.connect(path)


def get_sqlite_tip(conn: sqlite3.Connection) -> int:
    """Return the current main chain tip height from SQLite."""
    cur = conn.cursor()
    cur.execute("SELECT MAX(height) FROM full_blocks WHERE in_main_chain = 1")
    tip = cur.fetchone()[0]
    return int(tip or 0)
