# Nairobi Protocol - Geometric Determinism Engine (GDE)

> DOI: https://doi.org/10.5281/zenodo.20036883  
> Author: Tom Kimingi - RRD Kenya  
> License: MIT

## What It Is

The Geometric Determinism Engine is a deterministic address-computation layer for knowledge retrieval.

This repository is an architecture prototype and verification harness. It demonstrates the core deterministic addressing design, storage experiments, and benchmark evidence; it is not a full production-ready retrieval system.

Given an input key, the GDE computes the exact byte address where that key's knowledge chunk should live, then seeks directly to that address in a file-backed store. It does not scan a corpus, traverse a vector index, or train a model.

```text
input key
  -> universal_geometric_hash()
  -> coordinate_to_offset()
  -> file seek + read
  -> knowledge chunk
```

The current root programs use sparse files with direct `seek` and `read` operations. The project documentation may use "mmap" historically, but the checked-in demo path does not yet call an explicit mmap API.

## Core Formula

```text
raw_offset = Sum(|vi| * wi) mod ADDRESS_SPACE
aligned_offset = (raw_offset // SLOT_SIZE) * SLOT_SIZE
```

Where:

- `vi` is component `i` of the 24D normalized hash vector.
- `wi` is `(i + 1) * 2654435761`.
- `ADDRESS_SPACE` defaults to `100 GB`.
- `SLOT_SIZE` defaults to `256 bytes`.

The shared implementation lives in `src/1_gateway/addressing.mojo`.

## Repository Layout

```text
src/
  0_refinery/        Python semantic and ontology processing
  1_gateway/         Hashing, addressing, slot storage, integrity
  2_execution/       Coordinate bridge and execution kernels
tests/               Python and Mojo verification harnesses
docs/                Architecture, storage, testing, deployment notes
```

Important entrypoints:

- `knowledge_store.mojo`: writes 10 demo chunks into `knowledge_store.bin`.
- `query_engine.mojo`: retrieves those chunks by recomputing offsets.
- `benchmark_retrieval.mojo`: 1,000,000 query retrieval benchmark.
- `benchmark_collision_mojo.mojo`: 10,000 key collision check.
- `stress_test_mmap.mojo`: 100GB sparse-file boundary check.
- `stress_test_1m.mojo`: 1,000,000 deterministic seek stress check.
- `src/1_gateway/stress_test_v2.mojo`: 1,000,000 structured-store write benchmark.

## Requirements

- Linux or WSL2 Ubuntu.
- ext4 or another filesystem with good sparse-file behavior.
- x86_64 CPU.
- 4 GB RAM minimum.
- Pixi.

Install Pixi if needed:

```bash
curl -fsSL https://pixi.sh/install.sh | sh
```

Install project dependencies:

```bash
pixi project channel add https://conda.modular.com/max
pixi install
```

Pixi installs Python, MAX/Mojo, NetworkX, SQLite, and supporting tooling from `pixi.toml`.

## Quick Start

Run the lightweight smoke suite:

```bash
pixi run test-smoke
```

Run individual checks:

```bash
pixi run seed-ref
pixi run bench-refinery
pixi run seed-mojo
pixi run bench-mojo
pixi run integrity
```

Run the direct storage demo:

```bash
truncate -s 100G knowledge_store.bin
pixi run store-write
pixi run query
```

Run benchmarks and stress checks:

```bash
pixi run bench-retrieval
pixi run collision

truncate -s 100G stress_test_model.bin
pixi run stress-mmap
pixi run stress-1m
```

Run the longer structured-store write stress test:

```bash
pixi run stress-v2
```

## Current Verified Results

Latest local verification date: 2026-05-23.

```text
seed-ref: PASS
bench-refinery: PASS
seed-mojo: PASS
bench-mojo: PASS
integrity: PASS
knowledge store write: 10 verified, 0 failed
query engine: average 82.0573 us over 10 demo queries
retrieval benchmark: 25.709419067 us/query, 38,896.2503 queries/sec
collision benchmark: 0 collisions across 10,000 generated keys
consistency baseline: VERIFIED
100GB boundary stress: PASS
1,000,000 seek stress: PASS
structured-store 1M write stress: 13,682.489 ops/sec
```

See `docs/TESTING.md` for full command output and interpretation.

## Storage Modes

The repository currently contains two storage paths:

- Simple direct store: root demo scripts write raw payloads at deterministic 256-byte slots.
- Structured store: `src/1_gateway/structured_store.mojo` adds slot headers, FNV-1a key fingerprints, CRC32 payload integrity, tombstones, and bounded linear probing.

The structured store is the path to harden for real applications. The simple root store is useful for explaining the core deterministic addressing mechanism.

## Non-goals / Current Limits

- Architecture prototype, not production system: the repo validates core mechanics and documents pending production layers.
- Exact-key retrieval only: the GDE returns data when the lookup key resolves to the same deterministic address used at write time.
- No fuzzy semantic retrieval yet: queries such as "what is a neural network?" are not automatically mapped to stored keys such as `neural network architecture`.
- No document ingestion or chunking yet: there is no committed pipeline for splitting source documents, assigning canonical chunk keys, writing manifests, or listing stored keys.
- Collision handling depends on the storage path: the structured store handles occupied slots with fingerprints, CRC checks, and bounded probing; the simple root demo store writes directly to computed offsets and can overwrite on collision.
- The Python semantic refinery and the Mojo storage engine are still demonstration layers, not a unified production ingestion/retrieval pipeline.

## Status

| Component | Status |
|---|---|
| 24D phonological hash | Implemented and checked against Python reference |
| Deterministic offset formula | Implemented in `addressing.mojo` |
| Simple direct retrieval demo | Verified |
| Structured slot store | Implemented, stress-tested |
| Collision check | 0 collisions in current 10K benchmark |
| Python semantic refinery | Implemented demo benchmark |
| Explicit mmap API integration | Pending |
| Multi-process write safety | Pending |
| API/LLM integration | Pending |

## More Documentation

- `docs/ARCHITECTURE.md`: system design and data flow.
- `docs/STORAGE.md`: slot layout, simple store, structured store, generated files.
- `docs/TESTING.md`: test commands, expected outputs, benchmark values.
- `docs/DEPLOYMENT.md`: deployment and hardware notes.

## Built By

Tom Kimingi - Nairobi, Kenya  
RRD Kenya 2026  
https://github.com/tkimingi25-spec/Nairobi_Protocol-GDE-
