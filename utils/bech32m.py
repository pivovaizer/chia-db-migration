"""Bech32m encoding/decoding for Chia XCH addresses.

Implements BIP-350 (bech32m) to convert between puzzle_hash bytes and
human-readable xch1... addresses. No external dependencies.
"""
from __future__ import annotations

CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
BECH32M_CONST = 0x2BC830A3


def _bech32_polymod(values: list[int]) -> int:
    gen = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for v in values:
        b = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ v
        for i in range(5):
            chk ^= gen[i] if ((b >> i) & 1) else 0
    return chk


def _bech32_hrp_expand(hrp: str) -> list[int]:
    return [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]


def _bech32m_create_checksum(hrp: str, data: list[int]) -> list[int]:
    polymod = _bech32_polymod(_bech32_hrp_expand(hrp) + data + [0] * 6) ^ BECH32M_CONST
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]


def _bech32m_verify_checksum(hrp: str, data: list[int]) -> bool:
    return _bech32_polymod(_bech32_hrp_expand(hrp) + data) == BECH32M_CONST


def _convertbits(data: bytes | list[int], frombits: int, tobits: int, pad: bool = True) -> list[int]:
    acc = 0
    bits = 0
    result: list[int] = []
    maxv = (1 << tobits) - 1
    for value in data:
        acc = (acc << frombits) | value
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            result.append((acc >> bits) & maxv)
    if pad:
        if bits:
            result.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        raise ValueError("Invalid padding")
    return result


def encode_puzzle_hash(puzzle_hash: bytes, prefix: str = "xch") -> str:
    """Encode a 32-byte puzzle hash into a bech32m address string.

    Args:
        puzzle_hash: 32 bytes representing the puzzle hash.
        prefix:      Human-readable prefix ("xch" for mainnet, "txch" for testnet).

    Returns:
        Bech32m encoded address string (e.g. "xch1...").
    """
    if len(puzzle_hash) != 32:
        raise ValueError(f"puzzle_hash must be 32 bytes, got {len(puzzle_hash)}")
    data5 = _convertbits(puzzle_hash, 8, 5)
    checksum = _bech32m_create_checksum(prefix, data5)
    return prefix + "1" + "".join(CHARSET[d] for d in data5 + checksum)


def decode_puzzle_hash(address: str) -> bytes:
    """Decode a bech32m address string back into a 32-byte puzzle hash.

    Args:
        address: Bech32m encoded address (e.g. "xch1...").

    Returns:
        32 bytes representing the puzzle hash.
    """
    address = address.lower()
    pos = address.rfind("1")
    if pos < 1:
        raise ValueError("Invalid bech32m address: missing separator")

    hrp = address[:pos]
    data_part = address[pos + 1:]

    data = [CHARSET.find(c) for c in data_part]
    if -1 in data:
        raise ValueError("Invalid bech32m address: bad character")

    if not _bech32m_verify_checksum(hrp, data):
        raise ValueError("Invalid bech32m checksum")

    # Strip the 6-byte checksum, convert 5-bit back to 8-bit
    decoded = _convertbits(data[:-6], 5, 8, pad=False)
    result = bytes(decoded)

    if len(result) != 32:
        raise ValueError(f"Decoded puzzle hash must be 32 bytes, got {len(result)}")
    return result
