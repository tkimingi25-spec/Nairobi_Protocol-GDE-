# Architecture

The Nairobi Protocol GDE is organized as a deterministic retrieval pipeline. Its central contract is simple: the same key should always produce the same address, so retrieval can jump directly to a known slot.

## Runtime Path

```text
String key
  -> phonological signal
  -> 24D normalized hash vector
  -> deterministic weighted offset
  -> 256-byte slot alignment
  -> file seek/read
```

## Layers

### 0_refinery

`src/0_refinery` contains Python semantic tooling. It is separate from the Mojo retrieval hot path.

- `ontology_parser.py` builds a small SQLite-backed ontology graph.
- `contrast_lca.py` computes graph contrast/resonance values.
- `tests/integration_bench.py` benchmarks the Python hash reference plus refinery ingestion.

### 1_gateway

`src/1_gateway` contains the main deterministic addressing and storage components.

- `phonological.mojo`: builds a 24D hash vector from text.
- `addressing.mojo`: maps that vector into the 100GB address space.
- `slot_format.mojo`: defines structured-store slot headers and flags.
- `structured_store.mojo`: implements header-aware read/write with bounded probing.
- `fingerprint.mojo`: FNV-1a 64-bit key fingerprint.
- `integrity.mojo`: CRC32 payload verification.
- `persistence.mojo`: older vector vault used by the seed demo.

### 2_execution

`src/2_execution` contains demonstration execution utilities.

- `coordinate_bridge.mojo`: maps words to offsets and checks proximity.
- `logic_kernels.mojo`: small SIMD helper kernels.
- `atlas_manager.mojo`: atlas/subgraph loading support.

## Hashing

`universal_geometric_hash(text)` lowercases text, reads up to 16 bytes, builds a 32-length signal with byte values and byte deltas, applies a DCT-like projection, and normalizes the first 24 coefficients.

The Python reference in `tests/phonological_seed_reference.py` mirrors the intended behavior and is used for fast verification.

## Addressing

`coordinate_to_offset(vector)` computes:

```text
raw_offset = Sum(abs(vector[i]) * ((i + 1) * 2654435761)) mod 100GB
aligned_offset = floor(raw_offset / 256) * 256
```

The formula is deterministic and independent of corpus size. Collision handling is a storage-layer concern.

## Retrieval Complexity

The simple path is constant-time with respect to corpus size: compute one address and issue one seek/read. In practice, latency is dominated by hash/address computation, page-cache behavior, and collision probing in the structured store.

The latest local retrieval benchmark measured:

```text
Hash + offset + seek: 26.046829635 us/query
Full retrieval:       25.709419067 us/query
Read overhead:        -0.337410568 us/query
```

The negative read overhead in this run is measurement noise between adjacent loops; the important result is that the 256-byte read cost is below the noise floor of the benchmark.

## Limits

- Inputs longer than the hash signal window are truncated.
- Collision probability is reduced by the large address space but not eliminated.
- The structured store uses bounded linear probing with `MAX_PROBE_DEPTH = 64`.
- Multi-process write safety is not implemented.
- The root demos use file `seek/read`, not an explicit mmap API.
