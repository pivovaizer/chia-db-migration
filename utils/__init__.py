"""ChiaExplorer utilities — публичный интерфейс пакета.

Импортируй отсюда, а не из подмодулей напрямую:

    from utils import blob_to_int, connect_pg, get_state, ...

Это позволяет менять внутреннюю структуру пакета, не ломая импорты
в скриптах db/.
"""
from utils.blob_to_int  import blob_to_int
from utils.pg_utils     import connect_pg, ensure_sync_state, get_state, set_state
from utils.sqlite_utils import connect_sqlite, get_sqlite_tip

__all__ = [
    # Конвертация
    "blob_to_int",
    # PostgreSQL
    "connect_pg",
    "ensure_sync_state",
    "get_state",
    "set_state",
    # SQLite
    "connect_sqlite",
    "get_sqlite_tip",
]
