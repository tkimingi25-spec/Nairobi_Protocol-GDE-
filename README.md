# Nairobi Protocol - Geometric Determinism Engine (GDE)

> **DOI:** https://doi.org/10.5281/zenodo.20036883
> **Author:** Tom Kimingi - RRD Kenya
> **License:** MIT

## What It Is

The GDE is a deterministic address-computation layer for knowledge retrieval.

Given an input key, it:

1. Builds a 24D phonological hash.
2. Converts that hash into a deterministic byte offset.
3. Seeks directly to that offset in a file-backed store.

The checked-in root programs currently use file `seek` and `read` operations over sparse files. They do not yet use an explicit mmap API.

## Core Formula

```text
raw_offset = Sum(|vi| * wi) mod ADDRESS_SPACE
aligned_offset = (raw_offset // SLOT_SIZE) * SLOT_SIZE
```

Where:

- `vi` is component `i` of the 24D normalized hash
- `wi` is `(i + 1) * 2654435761`
- `ADDRESS_SPACE` defaults to `100 GB`
- `SLOT_SIZE` defaults to `256 bytes`

The shared implementation lives in [src/1_gateway/addressing.mojo](/C:/Users/hp/Desktop/GEOMETRIC%20DETERMINISM%20ENGINE/src/1_gateway/addressing.mojo:1).

## Current Runtime Path

```text
input key
  -> universal_geometric_hash()   src/1_gateway/phonological.mojo
  -> coordinate_to_offset()       src/1_gateway/addressing.mojo
  -> seek + read                  knowledge_store.bin
```

## Environment

- OS: Linux / WSL2 Ubuntu recommended
- Filesystem: ext4 recommended for sparse file behavior
- CPU: x86_64
- RAM: 4 GB minimum

`pixi.toml` is currently configured for `linux-64`, so the Mojo tasks should be run from WSL or another Linux environment.

## Running

Install:

```bash
pixi project channel add https://conda.modular.com/max
pixi install
```

Seed the reference Python checks:

```bash
pixi run seed-ref
pixi run bench-refinery
```

Run the Mojo seed and bench tasks:

```bash
pixi run seed-mojo
pixi run bench-mojo
```

Root Mojo entrypoints:

```bash
truncate -s 100G knowledge_store.bin
pixi run mojo -I src/1_gateway knowledge_store.mojo
pixi run mojo -I src/1_gateway query_engine.mojo
pixi run mojo -I src/1_gateway benchmark_retrieval.mojo
pixi run mojo -I src/1_gateway benchmark_collision_mojo.mojo

truncate -s 100G stress_test_model.bin
pixi run mojo stress_test_mmap.mojo
pixi run mojo stress_test_1m.mojo
pixi run mojo -I src/1_gateway consistency_check.mojo
```

## Status

| Component | Status |
|---|---|
| Hash function | Unified across Mojo and Python reference |
| Offset formula | Centralized in `addressing.mojo` |
| Collision benchmark | Uses aligned store offsets |
| Consistency baseline | Refreshed for current hash |
| Root storage path | File-backed seek/read |
| Explicit mmap integration | Pending |

## Notes

- Historical benchmark numbers from older revisions should be re-run in WSL before being treated as current.
- The semantic refinery Python path still runs independently from the Mojo runtime path.

## Built By

Tom Kimingi - Nairobi, Kenya
RRD Kenya 2026
https://github.com/tkimingi25-spec/Nairobi_Protocol-GDE-
