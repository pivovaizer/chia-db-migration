# ChiaExplorer DB Migration

Tool for migrating Chia blockchain data from the local node's SQLite database into PostgreSQL — powering the Chia Explorer backend.

## Why

The Chia node stores its blockchain in SQLite (`blockchain_v2_mainnet.sqlite`). This doesn't work for a web explorer: no concurrent queries, no network access, slow JOINs. This project migrates the data into PostgreSQL with a proper schema and indexes.

## Quick start

```bash
# 1. Clone and set up the environment
git clone <repo-url>
cd chiadbmgration
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt

# 2. Configure connections
cp .env.example .env
# Fill in PG_DSN and optionally SQLITE_PATH
```

## Migration order

```
001 → 002 → 003 → 004 → 005 → 006
```

| Step | Script | What it does |
|------|--------|--------------|
| 1 | `python db/001_init_schema.py` | Create tables and indexes in PostgreSQL |
| 2 | `python db/002_check_schema.py` | Verify the schema was created correctly |
| 3 | `python db/003_reset_db.py` | Drop secondary indexes (speeds up import) |
| 4 | `python db/004_import_blocks.py` | Import blocks from SQLite → PostgreSQL |
| 5 | `python db/005_import_coins.py` | Import coins from SQLite → PostgreSQL |
| 6 | `python db/006_create_indexes.py` | Create secondary indexes after import |

**Import can be interrupted and resumed** — progress is saved in the `sync_state` table.

## Configuration (.env)

| Variable | Required | Description |
|----------|:--------:|-------------|
| `PG_DSN` | yes | PostgreSQL connection DSN |
| `SQLITE_PATH` | no | Path to the node's SQLite database (default: `~/downloads/mainnet/blockchain_v2_mainnet.sqlite`) |
| `IMPORT_STEP` | no | Blocks per iteration (default: 200,000) |
| `BATCH_SIZE_BLOCKS` | no | Rows per INSERT batch for blocks (default: 20,000) |
| `BATCH_SIZE_COINS` | no | Rows per INSERT batch for coins (default: 100,000) |

## Project structure

```
chiadbmgration/
├── config.py                # Centralized configuration from .env
├── requirements.txt         # Dependencies
├── .env.example             # Configuration template
├── db/
│   ├── 001_init_schema.py       # Create tables
│   ├── 002_check_schema.py      # Verify schema
│   ├── 003_reset_db.py          # Reset database & drop indexes
│   ├── 004_import_blocks.py     # Import blocks (with resume)
│   ├── 005_import_coins.py      # Import coins (with resume)
│   └── 006_create_indexes.py    # Create indexes after import
├── utils/
│   ├── __init__.py          # Package public interface
│   ├── pg_utils.py          # PostgreSQL: connection, sync_state
│   ├── sqlite_utils.py      # SQLite: connection, get_tip
│   └── blob_to_int.py       # Chia BLOB amount decoding
└── tests/
    ├── show_sqlite_blocks_structure.py  # Inspect SQLite structure
    ├── pull_from_sqlite_address.py      # Test: address balances
    └── indexing_sqlite.py               # Create indexes in SQLite
```
