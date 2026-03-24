"""Extract and display address balances from SQLite for the first N blocks."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
from collections import defaultdict
from utils.bech32m import encode_puzzle_hash

DB_PATH = Path(r"C:\Users\pivovaizer\Downloads\mainnet\blockchain_v2_mainnet.sqlite")
MAX_HEIGHT = 100
ADDRESS_PREFIX = "xch"
MOJO = 10**12

def blob_to_int(b: bytes) -> int:
    return int.from_bytes(b, "big")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

query = """
SELECT puzzle_hash, amount
FROM coin_record
WHERE confirmed_index <= ?
    AND(
        spent_index = 0
        OR spent_index > ?
    )
"""

balances = defaultdict(int)

for row in cur.execute(query, (MAX_HEIGHT, MAX_HEIGHT)):
    ph = row["puzzle_hash"]
    amount = blob_to_int(row["amount"])
    balances[ph] += amount

print(f'Addresses with balance up to height {MAX_HEIGHT}: {len(balances)}\n')

for ph_bytes, balance in balances.items():
    xch = balance / MOJO
    if xch >= 0.01:
        address = encode_puzzle_hash(ph_bytes, ADDRESS_PREFIX)
        print(address, xch, "XCH")


conn.close()
