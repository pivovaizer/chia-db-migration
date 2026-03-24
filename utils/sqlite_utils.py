"""Вспомогательные функции для работы с SQLite-базой Chia-ноды.

Предоставляет безопасное (read-only по умолчанию) подключение к
локальной SQLite-базе блокчейна и утилиты для получения метаданных.
"""
from __future__ import annotations

import sqlite3

from config import SQLITE_PATH


def connect_sqlite(
    path: str = SQLITE_PATH,
    *,
    readonly: bool = True,
) -> sqlite3.Connection:
    """Открыть SQLite-базу Chia и вернуть соединение.

    По умолчанию открывается в режиме read-only (uri mode), чтобы
    случайно не повредить живую базу данных ноды.

    Args:
        path:     Путь к .sqlite-файлу (по умолчанию из config).
        readonly: Если True — открыть в режиме чтения (безопасно для ноды).
                  Передай False, если нужно создавать индексы или писать.

    Returns:
        Открытое соединение sqlite3.

    Raises:
        SystemExit: Если файл не найден по указанному пути.
    """
    import os
    if not os.path.exists(path):
        raise SystemExit(f"❌ SQLite-база не найдена: {path}")

    if readonly:
        # URI mode: ?mode=ro гарантирует, что запись невозможна
        uri = f"file:{path}?mode=ro"
        return sqlite3.connect(uri, uri=True)

    return sqlite3.connect(path)


def get_sqlite_tip(conn: sqlite3.Connection) -> int:
    """Вернуть высоту текущего tip главной цепи из SQLite.

    Args:
        conn: Открытое соединение к базе блокчейна Chia.

    Returns:
        Максимальная высота в full_blocks где in_main_chain = 1, или 0.
    """
    cur = conn.cursor()
    cur.execute("SELECT MAX(height) FROM full_blocks WHERE in_main_chain = 1")
    tip = cur.fetchone()[0]
    return int(tip or 0)
