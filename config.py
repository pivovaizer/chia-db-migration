"""Централизованная конфигурация ChiaExplorer.

Все настройки читаются из переменных окружения / файла .env.
Чтобы настроить проект — скопируй .env.example в .env и заполни значения.

Принцип: единая точка правды (Single Source of Truth).
Ни один другой файл не должен напрямую вызывать os.getenv() или load_dotenv().
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Загружаем .env из корня проекта (работает независимо от cwd)
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------

PG_DSN: str = os.getenv("PG_DSN", "")
if not PG_DSN:
    raise SystemExit(
        "❌ Переменная PG_DSN не найдена. "
        "Скопируй .env.example в .env и заполни настройки."
    )

# ---------------------------------------------------------------------------
# SQLite (локальная база Chia-ноды)
# ---------------------------------------------------------------------------

# Можно переопределить через SQLITE_PATH в .env
_default_sqlite = (
    Path.home() / "downloads" / "mainnet" / "blockchain_v2_mainnet.sqlite"
)
SQLITE_PATH: str = os.getenv("SQLITE_PATH", str(_default_sqlite))

# ---------------------------------------------------------------------------
# Параметры импорта (можно тюнить через .env)
# ---------------------------------------------------------------------------

# Шаг по высоте блока при итерации (сколько блоков обрабатывается за один "круг")
IMPORT_STEP: int = int(os.getenv("IMPORT_STEP", "200000"))

# Количество строк в одном INSERT-батче для таблицы blocks
BATCH_SIZE_BLOCKS: int = int(os.getenv("BATCH_SIZE_BLOCKS", "20000"))

# Количество строк в одном INSERT-батче для таблицы coins
BATCH_SIZE_COINS: int = int(os.getenv("BATCH_SIZE_COINS", "100000"))

# ---------------------------------------------------------------------------
# Константы БД
# ---------------------------------------------------------------------------

# Верхняя граница PostgreSQL BIGINT (2^63 − 1)
BIGINT_MAX: int = 2**63 - 1
