"""Centralized configuration for ChiaExplorer.

All settings are read from environment variables / .env file.
Copy .env.example to .env and fill in the values.

Single source of truth — no other file should call os.getenv() or load_dotenv() directly.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (works regardless of cwd)
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------

PG_DSN: str = os.getenv("PG_DSN", "")
if not PG_DSN:
    raise SystemExit(
        "PG_DSN not found. Copy .env.example to .env and fill in the settings."
    )

# ---------------------------------------------------------------------------
# SQLite (local Chia node database)
# ---------------------------------------------------------------------------

# Can be overridden via SQLITE_PATH in .env
_default_sqlite = (
    Path.home() / "downloads" / "mainnet" / "blockchain_v2_mainnet.sqlite"
)
SQLITE_PATH: str = os.getenv("SQLITE_PATH", str(_default_sqlite))

# ---------------------------------------------------------------------------
# Import parameters (tunable via .env)
# ---------------------------------------------------------------------------

# Block height step per iteration
IMPORT_STEP: int = int(os.getenv("IMPORT_STEP", "200000"))

# Rows per INSERT batch for blocks table
BATCH_SIZE_BLOCKS: int = int(os.getenv("BATCH_SIZE_BLOCKS", "20000"))

# Rows per INSERT batch for coins table
BATCH_SIZE_COINS: int = int(os.getenv("BATCH_SIZE_COINS", "100000"))

# ---------------------------------------------------------------------------
# DB constants
# ---------------------------------------------------------------------------

# PostgreSQL BIGINT upper bound (2^63 - 1)
BIGINT_MAX: int = 2**63 - 1
