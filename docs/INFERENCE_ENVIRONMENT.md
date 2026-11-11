# Inference Environment Audit (Phase 1)

Measured on the development/build laptop, 2026-11-11. Values were read
from the OS and the model file itself, not assumed.

## Hardware

| Item | Actual |
|---|---|
| OS | Microsoft Windows 10 Pro 10.0.19045 |
| CPU | AMD Ryzen 7 PRO 2700U (Zen 1), 4 cores / 8 threads, 2.2 GHz, AVX2/FMA/F16C (no AVX-512) |
| GPU | AMD Radeon Vega 10 integrated, 1 GB shared — treated as **no GPU** |
| RAM | 14.9 GB visible (~16 GB nominal); only ~6 GB free at audit time |
| Disk | SK hynix SC313 **SATA** 256 GB SSD; **11.6 GB free** at audit time |
| Target for later phases | 16 GB RAM, CPU-only (this class of machine) |

Disk space is a hard constraint: the full extent-store copy of the model
needs ~4.7 GB, leaving little headroom. Large artifacts go to the temp
directory and must be accounted for, never into the repo.

## Model (exact)

Source: Ollama blob store, `llama3:8b`
(`~/.ollama/models/blobs/sha256-6a0746a1...`).

| Property | Value |
|---|---|
| Architecture | `llama` — Meta-Llama-3-8B-Instruct |
| Parameters | ~8.03 B (sum of tensor element counts) |
| File size | 4,661,211,424 bytes (~4.34 GiB) |
| Quantization | GGUF file_type 2 = **Q4_0** (not Q4_K_M; the existing download is used as-is) |
| Tensors | 291 total: 225 × Q4_0, 65 × F32, 1 × Q6_K (`output.weight`) |
| Header/metadata | 7,835,936 bytes (includes tokenizer) |
| Tensor bytes | 4,653,375,488 — exactly fills the data region, no gaps, no overlapping extents, last tensor ends exactly at EOF |
| Largest tensors | `output.weight` 430,940,160 B; `token_embd.weight` 295,501,824 B |

## Software / runtimes

| Item | Status |
|---|---|
| Python | 3.13.7 (system) |
| Ollama | client 0.40.11 installed; server was not running at audit time |
| llama.cpp | **not installed**; no `llama-cli` binary on PATH |
| Compilers | **none**: no MSVC, CMake, MinGW, or gcc — llama.cpp cannot be built from source here |
| Mojo | pinned 0.26.2 via pixi (`linux-64` only); cannot run on this Windows host, and no WSL2 distribution is installed |
| FUSE/WinFsp | not installed (relevant to Phase 3 integration options) |

## Consequences for the design

1. CPU-only baseline first (Ryzen 2700U, SATA SSD): expect single-digit
   tokens/sec for 8B Q4_0; the disk is SATA (~0.5 GB/s), not NVMe.
2. The inference runtime must come from a prebuilt binary or Ollama;
   building llama.cpp from source is not possible on this machine.
3. GDE-controlled reads during inference need either a filesystem-layer
   integration (FUSE on WSL2/Linux, WinFsp on Windows) or a runtime
   with a pluggable file backend — Ollama's binary has neither exposed.
   See `docs/GDE_INFERENCE_ARCHITECTURE.md` for the evaluated options.
