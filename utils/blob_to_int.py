"""Decode Chia BLOB amounts to Python int.

Chia stores coin amounts (in mojo) as variable-length big-endian integers
in SQLite BLOB fields. This module provides a robust decoder that handles
edge cases: leading zero bytes, oversized BLOBs (>8 bytes), memoryview
inputs, and None inputs.

The value must fit into a PostgreSQL BIGINT (signed 64-bit).
"""
from __future__ import annotations

from config import BIGINT_MAX


def blob_to_int(value: bytes | memoryview | None) -> int:
    """Decode a BLOB amount field from SQLite into a BIGINT-compatible int.

    Decoding strategy:
      1. Strip leading zero bytes, decode as big-endian.
      2. If BLOB is longer than 8 bytes, take the last 8 bytes
         and try both byte orders (big/little), pick the smallest valid one.
      3. If neither fits in BIGINT, raise ValueError.
    """
    if value is None:
        return 0

    if isinstance(value, memoryview):
        value = value.tobytes()

    raw = bytes(value)
    if not raw:
        return 0

    # Fast path: big-endian without leading zeros
    stripped = raw.lstrip(b"\x00")
    if 0 < len(stripped) <= 8:
        candidate = int.from_bytes(stripped, "big", signed=False)
        if candidate <= BIGINT_MAX:
            return candidate

    # Fallback: analyze the last 8 bytes
    # Chia sometimes adds padding bytes in front; the tail is the real value.
    tail = raw[-8:] if len(raw) > 8 else raw
    big_endian    = int.from_bytes(tail, "big",    signed=False)
    little_endian = int.from_bytes(tail, "little", signed=False)

    valid = [v for v in (big_endian, little_endian) if v <= BIGINT_MAX]
    if valid:
        return min(valid)

    raise ValueError(
        f"BLOB amount does not fit in BIGINT "
        f"(len={len(raw)}, big={big_endian}, little={little_endian})"
    )
