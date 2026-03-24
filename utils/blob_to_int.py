"""Декодирование BLOB-суммы Chia в Python int.

Chia хранит суммы монет (в mojo) как переменной длины big-endian integers
в SQLite BLOB-полях. Этот модуль предоставляет надёжный декодер,
который обрабатывает крайние случаи:
  - ведущие нулевые байты
  - oversized BLOB (длиннее 8 байт)
  - memoryview-входы вместо bytes
  - None-входы

Значение должно вписываться в PostgreSQL BIGINT (signed 64-bit).
"""
from __future__ import annotations

from config import BIGINT_MAX


def blob_to_int(value: bytes | memoryview | None) -> int:
    """Декодировать BLOB-поле amount из SQLite в int, совместимый с BIGINT.

    Стратегия декодирования:
      1. Обрезаем ведущие нулевые байты, декодируем как big-endian.
      2. Если BLOB длиннее 8 байт — берём последние 8 байт
         и пробуем оба порядка (big/little), выбираем наименьший допустимый.
      3. Если ни один вариант не влезает в BIGINT — бросаем ValueError.

    Args:
        value: Сырые байты, memoryview или None из SQLite.

    Returns:
        Неотрицательное целое — количество mojo.

    Raises:
        ValueError: Если значение не укладывается в signed 64-bit integer.
    """
    if value is None:
        return 0

    if isinstance(value, memoryview):
        value = value.tobytes()

    raw = bytes(value)
    if not raw:
        return 0

    # --- Быстрый путь: big-endian без ведущих нулей ---
    stripped = raw.lstrip(b"\x00")
    if 0 < len(stripped) <= 8:
        candidate = int.from_bytes(stripped, "big", signed=False)
        if candidate <= BIGINT_MAX:
            return candidate

    # --- Запасной путь: анализируем последние 8 байт ---
    # Chia иногда добавляет паддинг-байты спереди; хвост — реальное значение.
    tail = raw[-8:] if len(raw) > 8 else raw
    big_endian    = int.from_bytes(tail, "big",    signed=False)
    little_endian = int.from_bytes(tail, "little", signed=False)

    valid = [v for v in (big_endian, little_endian) if v <= BIGINT_MAX]
    if valid:
        return min(valid)

    raise ValueError(
        f"BLOB-сумма не помещается в BIGINT "
        f"(len={len(raw)}, big={big_endian}, little={little_endian})"
    )
