"""Phase 1 regression gates for GDE addressing.

Canonical spec (mirrored in Mojo):
- Storage identity/address: FNV-1a 64 over the FULL key bytes, slot-aligned.
  The DCT geometric hash is for similarity only, never for storage identity.
- No silent loss: keys differing only after byte 16 must not share an address
  by construction, and systematic keys must not concentrate onto few slots.

Run: python tests/test_addressing_regression.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phonological_seed_reference import fnv1a_64, key_to_offset  # noqa: E402


def test_fnv_vectors() -> None:
    assert fnv1a_64("") == 14695981039346656037
    assert fnv1a_64("a") == 0xAF63DC4C8601EC8C  # published FNV-1a 64 vector


def test_full_key_influences_address() -> None:
    # These pairs share their first 16 bytes; the old hash gave them one address.
    assert key_to_offset("semantic_node_100") != key_to_offset("semantic_node_101")
    assert key_to_offset("a" * 16 + "x") != key_to_offset("a" * 16 + "y")
    assert key_to_offset("concept_of_item_1") != key_to_offset("concept_of_item_2")


def test_systematic_keys_do_not_concentrate() -> None:
    # The reported failure: 1M semantic_node_<i> keys collapsed to 100 addresses
    # and only 5,770/1,000,000 writes succeeded (100 slots x 64 probes).
    n = 100_000  # plain-loop sample; full 1M case covered by distinctness bound
    offsets = [key_to_offset(f"semantic_node_{i}") for i in range(n)]
    distinct = len(set(offsets))
    assert distinct >= int(n * 0.99), f"only {distinct} distinct offsets for {n} keys"
    # With near-unique base offsets, 64-deep linear probing cannot fill up:
    # worst same-offset multiplicity must stay far below the probe depth.
    from collections import Counter
    worst = Counter(offsets).most_common(1)[0][1]
    assert worst <= 8, f"one offset received {worst} keys"


def test_short_key_geometric_baseline_unchanged() -> None:
    # Similarity hash behaviour for short keys must stay on correct math.
    from phonological_seed_reference import distance
    assert abs(distance("Apple", "Apples") - 0.2097105376047986) < 1e-12
    assert abs(distance("Quantum", "Symmetry") - 0.4167526183865839) < 1e-12


def main() -> None:
    test_fnv_vectors()
    test_full_key_influences_address()
    test_systematic_keys_do_not_concentrate()
    test_short_key_geometric_baseline_unchanged()
    print("PASS: addressing regression gates")


if __name__ == "__main__":
    main()
