# Session Checkpoint — 2026-11-11 17:36

## Marker

Work paused by request during the IDE task "Integrate GDE with
Llama 8B for Bounded-Memory Inference". This file is the resume point.

## Where things stand

- Committed + pushed: up to `520c1a9` (env audit, GGUF parser,
  transactional ingestion). Working tree holds the uncommitted
  Phase 3/4 files listed in `git status` (architecture doc, tensor
  service, FUSE/WinFsp adapters, `src/tools/winfsp/GdeFs.cs`,
  tensor-service tests).
- Proven: extent store ingests the real Llama-3-8B Q4_0 GGUF
  (292 extents, reconstruction SHA-256 == original) in
  `C:\tmp\gde_model_extents\` (temp storage, not repo).
- Proven: conventional llama.cpp b12284 baseline on the original
  GGUF — real answer, 5.2 tok/s, peak WS ~7.7 GB.
- Proven: Python GDE tensor service reads the real store at
  200-266 MB/s (warm cache) with bounded cache working.
- Proven: WinFsp adapter mounts and serves small stores (168 B,
  50 MB, and 2.6 GB synthetic stores all read correctly, GGUF magic
  verified through the mount).

## The open fault (resume here)

Through the WinFsp mount, the REAL 4.66 GB store cannot be read by
any application (Python EINVAL on first read, .NET canceled,
llama.cpp dies during load), while <=2.6 GB stores work perfectly.
Adapter code is identical in both cases and never reads the
manifest — only `extents.bin` size/content differs.

Next experiment (cheap, decisive): mount a store whose
`extents.bin` is extended just past 4 GiB (2^32) with only header
bytes written (small physical footprint). Read head bytes via
Python `os.read` in the mount session.
- If it fails: 4 GiB boundary confirmed; hunt the 32-bit
  truncation (WinFsp interop / cache-manager interaction).
- If it works: fault is content-specific to the real store;
  bisect by content (e.g. mount first N GB of the real extents
  via a truncated copy is NOT allowed — disk; use sparse views).

Other uncontrolled variables if size is exonerated: none known —
same build (GdeFs5), same consumer, same mount style.

## Constraints to honour

- Disk C: ~6.7 GB free. NO large writes without checking space.
  Never create the 100 GB sparse store on this disk.
- Mojo cannot run here (no WSL2 distro). Ollama/llama binaries
  live in `C:\tmp\llama-b12284\`. WinFsp is installed; the C#
  adapter compiles with the in-box .NET Framework csc against
  `winfsp-msil.dll` (copies in `C:\tmp\gdefs\`).
- Push requires escalated git with
  `-c credential.helper=manager`.
