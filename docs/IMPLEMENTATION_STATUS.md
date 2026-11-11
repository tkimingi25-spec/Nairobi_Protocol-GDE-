# Implementation Status (honest phase tracker)

Last updated from the Windows development machine. Anything marked
PENDING has not been demonstrated; it must not be cited as working.

| Phase | Status | Evidence |
|---|---|---|
| 0. Single authoritative tree | DONE | Local tree fast-forwarded to GitHub `2c9bbda`; slot_format conflict resolved keeping upstream `parse_header_into` plus `TrivialRegisterPassable`. |
| 1. Addressing reliability | DONE (Python gates); Mojo run PENDING | `tests/test_addressing_regression.py` passes: FNV-1a full-key addressing, keys differing after byte 16 get distinct addresses, systematic keys no longer concentrate, short-key distances unchanged (Apple/Apples 0.2097105376047986). Mojo mirror edited (`phonological.mojo` scalar norm/distance + full-key signal folding, `addressing.key_to_offset`, `StructuredStore` rewired, oversize payloads raise). Mojo compile/run still requires WSL2 (not installed on the dev sandbox). |
| 2. Extent model storage | DONE (prototype) | `src/tools/extent_store.py` + `src/tools/gguf_manifest.py`; `tests/test_extent_store.py` passes, including read-only parse of the real Ollama llama3:8b blob (291 tensors, Meta-Llama-3-8B-Instruct) with no tensor data copied. |
| 3. Bounded-RAM streaming | DONE (prototype level) | `stream_extent` yields bounded chunks; test asserts max chunk <= ceiling and byte-identical reassembly. Runtime-level RSS measurement during inference is Phase 4 work. |
| 4. Inference through GDE | PENDING | Blocked on: WSL2 + Mojo build, and llama.cpp integration on the 16 GB target machine. Gate when run: token-identical greedy output vs Ollama/llama.cpp on fixed prompts, peak RSS, first-token latency, tokens/sec. |
| 5. Selective retrieval | PENDING | Knowledge-path Q&A test set not yet built; MoE expert fetching not attempted. |
| 6. 4/8/16 GB + SSD/HDD matrix | PENDING | Requires the target 16 GB no-GPU machine and Phase 4. |
| 7. Interface + CI gates | PARTIAL | CI Mojo/Python steps are now strict (no `|| true` on test steps) and `structured_store_smoke.mojo`'s undefined `to_string` is fixed. User-facing interface not built. |

## Storage safety note

Experiments must not create the 100 GB sparse store on a machine whose
disk cannot afford physical allocation from scattered writes. The
address-space file is logical; scattered slot writes allocate real
4 KB blocks (verified: ~26M scattered slots can physically fill
100 GiB). Use small test files (KB-MB) in temp directories for gates.

## Known remaining risks

- Mojo code edited in Phase 1 is uncompiled until WSL2 is available.
- `consistency_check.mojo` baselines are Python-reference values; the
  next Mojo run must confirm STATUS: VERIFIED, not re-baseline to Mojo.
- Dense 70-100B inference remains bounded by disk bandwidth and CPU
  compute per token; GDE addresses memory, not those limits.
