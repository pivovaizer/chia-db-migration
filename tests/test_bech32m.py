"""Tests for bech32m encode/decode (XCH address conversion)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.bech32m import encode_puzzle_hash, decode_puzzle_hash

# Real test vectors from the Chia mainnet blockchain.
# These puzzle hashes come from actual coinbase rewards in the first blocks.
TEST_VECTORS = [
    # Block 1 — farmer reward (2,625,000 XCH prefarm)
    (
        "3d8765d3a597ec1d99663f6c9816d915b9f68613ac94009884c4addaefcce6af",
        "xch18krkt5a9jlkpmxtx8akfs9kezkuldpsn4j2qpxyycjka4m7vu6hstf6hku",
    ),
    # Block 1 — pool reward (18,375,000 XCH prefarm)
    (
        "d23da14695a188ae5708dd152263c4db883eb27edeb936178d4d988b8f3ce5fc",
        "xch16g76z3545xy2u4cgm52jyc7ymwyravn7m6unv9udfkvghreuuh7qa9cvfl",
    ),
    # Block 5 — first regular farming reward
    (
        "f55e4a65688e32445b7825ebee3421dba900909e1e8d36b61ac680c6ff8498c1",
        "xch1740y5etg3ceygkmcyh47udppmw5spyy7r6xndds6c6qvdluynrqs9qmvgy",
    ),
]


def test_encode_known_vectors():
    """Encoding known puzzle hashes should produce expected addresses."""
    for ph_hex, expected_addr in TEST_VECTORS:
        ph_bytes = bytes.fromhex(ph_hex)
        result = encode_puzzle_hash(ph_bytes, "xch")
        assert result == expected_addr, f"Expected {expected_addr}, got {result}"
    print("  encode: known vectors OK")


def test_decode_known_vectors():
    """Decoding known addresses should produce expected puzzle hashes."""
    for ph_hex, addr in TEST_VECTORS:
        expected = bytes.fromhex(ph_hex)
        result = decode_puzzle_hash(addr)
        assert result == expected, f"Expected {ph_hex}, got {result.hex()}"
    print("  decode: known vectors OK")


def test_roundtrip():
    """Encoding then decoding should return the original puzzle hash."""
    import os
    for _ in range(100):
        ph = os.urandom(32)
        addr = encode_puzzle_hash(ph, "xch")
        decoded = decode_puzzle_hash(addr)
        assert decoded == ph, f"Roundtrip failed for {ph.hex()}"
    print("  roundtrip: 100 random hashes OK")


def test_testnet_prefix():
    """Should work with txch prefix for testnet."""
    ph = bytes(32)  # all zeros
    addr = encode_puzzle_hash(ph, "txch")
    assert addr.startswith("txch1")
    decoded = decode_puzzle_hash(addr)
    assert decoded == ph
    print("  testnet prefix OK")


def test_invalid_length():
    """Should reject puzzle hashes that aren't 32 bytes."""
    try:
        encode_puzzle_hash(b"\x00" * 31, "xch")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

    try:
        encode_puzzle_hash(b"\x00" * 33, "xch")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    print("  invalid length rejection OK")


def test_invalid_checksum():
    """Should reject addresses with bad checksums."""
    ph = bytes(32)
    addr = encode_puzzle_hash(ph, "xch")
    # Corrupt the last character
    bad_addr = addr[:-1] + ("q" if addr[-1] != "q" else "p")
    try:
        decode_puzzle_hash(bad_addr)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    print("  invalid checksum rejection OK")


if __name__ == "__main__":
    print("Running bech32m tests...\n")
    test_encode_known_vectors()
    test_decode_known_vectors()
    test_roundtrip()
    test_testnet_prefix()
    test_invalid_length()
    test_invalid_checksum()
    print("\nAll tests passed.")
