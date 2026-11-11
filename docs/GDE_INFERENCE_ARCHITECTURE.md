# GDE-to-Inference Integration Architecture (Phase 3)

## How llama.cpp actually loads a GGUF (investigated, not assumed)

- Default path is **memory-mapped**: the GGUF file is mmap'd and tensor
  data is accessed through the mapping; the OS page cache decides what
  is resident. There is no per-tensor read callback to hook in-process.
- With `--no-mmap`, tensors are read through ordinary file reads **at
  load time** into allocated buffers — still no runtime read control,
  and RAM grows to hold the weights.
- Ollama (installed here) is a closed binary using the same GGUF/mmap
  family of loading; it exposes no pluggable file backend.

Consequence: **no in-process API exists** in the available runtimes for
"call GDE whenever a tensor is needed." Any design pretending otherwise
would be fiction. Control must be exercised at or below the file layer.

## Approaches evaluated

### 1. GDE-backed virtual file (filesystem layer) — SELECTED
A read-only virtual `model.gguf` is mounted (FUSE on Linux/WSL2 — the
repo's target platform; WinFsp on Windows). Every `read(offset, size)`
callback is served by the GDE extent service: extents are located via
the manifest, read in bounded chunks, optionally cached in a bounded
LRU, and **logged**. llama.cpp (unmodified, prebuilt) opens the virtual
file, with or without mmap; either way, page faults and reads traverse
the GDE path. This demonstrates actual GDE-controlled tensor retrieval
during inference, with byte counts to prove it.

Trade-offs: depends on a filesystem driver (built into Linux; WinFsp is
an extra install on Windows); FUSE read granularity interacts with
mmap paging; cannot reduce llama.cpp's own compute/KV memory.

### 2. Patched llama.cpp with a GDE tensor provider — REJECTED (for now)
Cleanest control, but: no compiler exists on the build laptop
(audited), it forks an upstream codebase we would have to maintain,
and its results would not be comparable to stock llama.cpp baselines.
Revisit only if the filesystem layer measurably fails.

### 3. Bounded temporary reconstruction — COMPATIBILITY ONLY
Rebuild a normal GGUF from extents and load it conventionally. This
was already proven byte-identical in Phase 2 (reconstruction SHA-256
equals the original GGUF). It validates storage integrity and model
compatibility. It is **not** GDE-backed inference and will never be
reported as such.

## Selected design

```
llama.cpp (unmodified)          GDE side
  open/read/pread  ───────────►  virtual file adapter (FUSE / WinFsp)
                                      │  read_at(file_offset, len)
                                      ▼
                                 GDE tensor service
                                   - manifest lookup (extent map)
                                   - bounded-chunk disk reads (configurable)
                                   - bounded LRU cache (configurable, off by default)
                                   - per-read logging + counters
                                   - optional sampled SHA-256 verification
                                      │
                                      ▼
                                 extents.bin (Phase 2 store)
```

Rules:
- Start synchronous and correct. Async prefetch is a separate,
  measured change; it ships only if benchmarks improve.
- Cache capacity is a hard byte budget; the whole model is never cached.
- Chunk size and cache budget are configuration, benchmarked at
  64 KB / 256 KB / 1 MB / 4 MB.
- Every read is countable: total bytes, per-tensor bytes, read count.
  "GDE participated" is a number from the log, not a claim.
- Missing/corrupt extents surface as read errors to the runtime,
  never as zero-filled silent data.

## Platform status

- The tensor service and read-path proof harness are implemented and
  tested in Python (`src/tools/gde_tensor_service.py`).
- The FUSE adapter targets WSL2/Linux (repo's declared platform) and
  the WinFsp adapter targets Windows; neither filesystem driver is
  installed on the current laptop, so the mounted-inference run is
  gated on that installation (or on moving to the WSL2 environment the
  project already targets). Until then, inference results are reported
  as baseline-only and the integration as partial — see
  `docs/IMPLEMENTATION_STATUS.md`.
