# Nairobi Protocol — Geometric Determinism Engine (GDE)

> DOI: https://doi.org/10.5281/zenodo.20036883  
> Author: Tom Kimingi — RRD Kenya  
> License: MIT

## Executive framing (what this repository is and is not)

This repository is a systems prototype and verification harness that demonstrates a deterministic, geometry-driven addressing layer for large-scale knowledge persistence and retrieval. It is not a conventional dense-parameter model; we do not attempt to load a 100B-parameter dense tensor into a 4 GB RAM budget.

Instead, the GDE separates semantic reasoning (a small local `refinery`) from durable parametric memory. The runtime shifts the parameter-scale state to disk (a sparse file addressing space, typically sized to 100 GB in experiments) while keeping the in-memory footprint bounded by transient buffers and the small local model state. This decoupling is mathematical and operational — storage and addressing are O(1) at the physical layer, so RAM usage does not scale with the addressable parameter-space.

Practical implication: the system does not create a 100B dense tensor in memory. It instead encodes canonical keys and deterministically maps them to fixed-size physical slots in a sparse file; reads/writes operate on fixed 256‑byte slots with constant-time seeks and bounded linear probing. See the Structured Storage section for exact wire-format details and the Benchmarks section for experimental throughput and memory observations.

## Dual-layer Architecture (separation of concerns)

- **Upstream — The Semantic Refinery (Python)**: a small local model + ontology-guided extractor that resolves raw text into canonical, deterministic keys. This component is implemented in `src/0_refinery/` and exercised by `tests/phonological_seed_reference.py` and `pixi` tasks. Its purpose is to map noisy NL into stable canonical identifiers suitable for exact-key storage.

- **Downstream — The Deterministic Gateway (Mojo)**: a purpose-built memory bank implemented in `src/1_gateway/`. Given a canonical key, it computes a 24‑dimensional phonological hash (`universal_geometric_hash`), projects the vector to an aligned byte offset (`coordinate_to_offset` in `addressing.mojo`), and performs an O(1) seek+slot read or write. There is no vector similarity scan at query time — retrieval is address-driven and exact-key based.

Flow (high-level):

```text
raw text -> semantic refinery (Python) -> canonical key
                         -> deterministic gateway (Mojo)
canonical key -> 24D hash -> deterministic offset -> seek to 256B slot -> read/write
```

## V2 Structured Storage — wire format and invariants

The V2 storage engine moves past raw overwrites and uses a self-verifying, fixed‑slot wire format implemented in `src/1_gateway/structured_store.mojo` and defined in `src/1_gateway/slot_format.mojo`.

Key invariants and on‑disk layout:

- Slot size: 256 bytes (`SLOT_SIZE = 256`).
- Header size: 32 bytes (`HEADER_SIZE = 32`).
- Payload capacity: 224 bytes (`PAYLOAD_CAPACITY = 224`).
- Fingerprint: 8‑byte FNV‑1a (`fnv1a_64`) used to validate a candidate slot (see `src/1_gateway/fingerprint.mojo`).
- Integrity: 4‑byte CRC32 (`crc32_compute`) stored in the header to detect silent corruption (see `src/1_gateway/integrity.mojo`).
- Probing: bounded linear probing with `MAX_PROBE_DEPTH = 64` to limit worst-case work while handling occupied slots.
- Chaining/continuation: a `FLAG_CONTINUATION` bit is available to mark continuation slots for payloads larger than `PAYLOAD_CAPACITY` (the wire format includes an `is_continuation` flag). See `src/1_gateway/slot_format.mojo` and `src/1_gateway/structured_store.mojo` for the exact implementation.

Concrete rationale:

- Fingerprint + CRC32: the fingerprint provides a fast, low-collision identity check; CRC32 detects accidental corruption. The two together keep reads conservative (reject on mismatch) while avoiding heavy per-read metadata.
- Fixed-size slots and bounded probing: fixed 256‑byte slots give predictable fs semantics and alignment; limiting probes to 64 keeps the physical work per operation bounded (constant-time behavior in expectation and by design). These choices prioritize predictable latency under high-scale address spaces.

Files of interest (implementation):

- `src/1_gateway/structured_store.mojo` (writes/reads and file-handle API)
- `src/1_gateway/slot_format.mojo` (slot constants, `SlotHeader`, `serialize_header`, `parse_header_into`)

## Empirical validation & benchmarks

All benchmark claims below reference code in `src/1_gateway/` and verification outputs logged during the local verification run (see `CHANGES_REPORT.md`). Results are environment-dependent; the values below were observed on the verification host and are meant as reproducible observations, not immutable performance guarantees.

| Benchmark Suite | Verified Metric | Architectural Significance |
| :--- | :--- | :--- |
| `stress_test_mmap.mojo` | **100GB Boundary Pass** | Proves the host OS addresses parameter-scale space (100 GB) via sparse files while the process maintains a bounded 4 GB RAM working set (OS page cache usage remains contained in our experiment). |
| `stress_test_1m.mojo` | **1,000,000 Seek Pass** | Confirms repeated deterministic seeks and writes across a large sparse file do not cause linear growth in the process memory footprint or uncontrolled page‑cache bloat in the tested environment. |
| `stress_test_v2.mojo` | **~13,682 ops/sec** | Verifies the V2 structured format handles saturated write loads with CRC32 and fingerprinting active. The test reuses an open file handle and performs 1M writes with bounded linear probing. See `src/1_gateway/stress_test_v2.mojo` and `CHANGES_REPORT.md`. |
| `benchmark_retrieval.mojo` | **~38,896 queries/sec** | Demonstrates true $O(1)$ retrieval: observed latency ~25.7 μs/query, showing retrieval cost is decoupled from the total addressable space size. |

Notes on reproducibility:

- The benchmark harnesses open the store file once for bulk operations (`write_with_handle` / `read_with_handle`) to remove per-op open/close noise (`src/1_gateway/structured_store.mojo`).
- The verification run and its artifacts are recorded in `CHANGES_REPORT.md` and `docs/TESTING.md`. Benchmarks are sensitive to SSD characteristics, filesystem behavior, and host OS page-cache settings; reproduce under similar hardware and OS tuning for comparable numbers.

## Status & Roadmap (validated vs pending)

This project has moved several components from prototype to validated in the V2 work:

| Component | Status |
|---|---|
| 24D phonological hash | Validated (Mojo + Python reference) |
| Deterministic offset formula | Validated (`src/1_gateway/addressing.mojo`) |
| Structured slot wire-format | Validated (`src/1_gateway/slot_format.mojo`, `src/1_gateway/structured_store.mojo`) |
| Collision handling (bounded probing) | Validated (`MAX_PROBE_DEPTH = 64`) |
| Retrieval & write benchmarks | Validated (refer to `CHANGES_REPORT.md`) |
| Explicit mmap API integration | Pending (the current demos use sparse files with `seek/read` semantics; explicit `mmap` use is documented but not relied upon by the core demos) |
| Multi-process write safety / locking | Pending (current implementation assumes single-process access) |
| Full IPC/ingest pipeline (Python ⇄ Mojo) | In progress — next priority: integrate the Python refinery as a producer that atomically writes canonical keys into the Mojo gateway via a small IPC boundary |

## How the 100B / 4GB framing is correct (mathematical note)

It is physically infeasible to store a 100B dense parameter tensor in 4 GB RAM. The GDE instead treats the persistent parameter surface as a disk-backed address space of order 100 GB and achieves constant-time physical routing via deterministic hashing and fixed-slot addressing. The important invariant is that per-operation working memory is bounded (a small header + payload buffer and local model state), so RAM does not scale with the addressable space. This is how the system supports an effectively very large persistent parameter-space under a small RAM envelope.

Formally: the per-operation cost is $O(1)$ with respect to the size of the addressable space; only the disk-backed addressable space grows. The in-process memory usage is bounded by constants (slot header, payload buffer, local model state), not by the address space size.

## Where to look next in the code

- `src/1_gateway/slot_format.mojo` — header layout, `MAX_PROBE_DEPTH`, `PAYLOAD_CAPACITY`.
- `src/1_gateway/structured_store.mojo` — read/write logic and handle-based APIs used by benchmarks.
- `src/1_gateway/stress_test_v2.mojo` — 1M write stress harness and throughput measurement.
- `src/1_gateway/stress_test_1m.mojo` and `stress_test_mmap.mojo` — large sparse-file boundary and seek validation.
- `CHANGES_REPORT.md` — verification run artifacts and measured values recorded during the validation run.

## Operational recommendations

- For multi-process access, add an advisory lock or a small coordinator service; this repo currently assumes single-process writers.
- For higher payloads, implement continuation slot chaining with explicit write-order journaling to support atomic multi-slot writes.
- Add CI to run `tests/run_integrity.mojo` and a smaller-scale structured-store verification to catch low-level regressions.

## Reproducibility & Local Setup

To reproduce the verification runs in a fresh environment, the repository includes a small setup helper and a `requirements.txt` for Python components used by the semantic refinery.

Steps (recommended on Ubuntu / WSL2):

```bash
./setup.sh
# or, if you prefer pip-only:
python3 -m pip install --user -r requirements.txt
```

The repository also provides a small advisory lock coordinator to coordinate multi-process writers:

- `src/tools/lock_coordinator.py` — CLI to `acquire` and `release` a lockfile using atomic file creation (best-effort owner check on release).
- `scripts/run_with_lock.sh` — wrapper that acquires a lock, runs a command, and releases the lock. Use this to run Mojo write-heavy processes when multiple writers may contend.

Example: run a Mojo stress test under the advisory lock

```bash
./scripts/run_with_lock.sh /tmp/gde.store.lock -- pixi run mojo -I src/1_gateway src/1_gateway/stress_test_v2.mojo
```

CI:

- A short GitHub Actions workflow is added at `.github/workflows/ci.yml` that installs Pixi and runs `tests/run_integrity.mojo` and `tests/structured_store_smoke.mojo` as a reduced smoke test. The workflow assumes the runner can install Pixi and the project channels; adjust the steps to suit your CI constraints.

## Built By

Tom Kimingi — Nairobi, Kenya  
RRD Kenya 2026  
https://github.com/tkimingi25-spec/Nairobi_Protocol-GDE-
