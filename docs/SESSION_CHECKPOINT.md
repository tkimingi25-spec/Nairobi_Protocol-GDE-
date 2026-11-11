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
llama.cpp dies during load, cmd copy "Incorrect function" after
~9 MB). Adapter code never reads the manifest — only the
`extents.bin` backing file differs between working and failing cases.

Experiments run 2026-11-11 17:38-17:44 (all with same consumer,
Python `os.read`, in the mount session):

| Store | Size | Result |
|---|---|---|
| synthetic tiny | 168 B | OK |
| synthetic mid | 50 MB | OK |
| synthetic zeros | 2.6 GB | OK (correct GGUF head) |
| synthetic past-4GiB (sparse tail) | 4.297 GB | OK (head + tail bytes correct) |
| real store, hardlinked copy | 4.66 GB | FAIL (EINVAL at offset 0) |
| real store | 4.66 GB | FAIL (all consumers) |

Exonerated: file size alone (4 GiB boundary crossed successfully
by synthetic), NTFS file identity (hardlink fails identically),
adapter host flags (aligned to official memfs `Init`, real
security descriptor, unique IndexNumber, volume serial — memfs
itself works perfectly on this machine), stable timestamps,
per-read logging (removed in GdeFs7 — still fails), sector size.

Established facts: WinFsp kernel log shows my `Read` callback IS
dispatched and paging (cache) reads complete `IoStatus=0`; the
application's own read is failed by the I/O/cache layer above the
FSD with INVALID_PARAMETER, after ~5-9 MB of successful readahead.
No exception is ever thrown inside the adapter.

Update 17:48 — minimal repro found, more exonerations:
- Reported-size override (mount real extents, report 2.6 GB):
  STILL FAILS. Reported FileSize value exonerated.
- Store containing ONLY the first 16 MB of the real extents
  (16 MB total): FAILS. Minimal repro is small.
- Same 16 MB XOR-scrambled: FAILS. Not content recognition (AV).
- Backing file read directly (no mount): first 16 MB sequential
  reads perfectly. The data and disk are fine.
- Fresh drive letter K: (no possible mount shadowing): FAILS.
- A zombie GdeFs5 process (PID 4648, owned by another session,
  "Access is denied" on kill) still exists from an early probe.
  It may shadow G: mounts; use a fresh letter and kill it from
  its owning session (or reboot) before trusting any G: result.
  It does NOT explain the fault (K: test above).

So: identical adapter + consumer + mount style; backing files
written by ingest (tiny/mid/2.6 GB) work; a plain 16 MB copy of
the real file's first bytes fails. Remaining uncontrolled
variables vs the working stores: the real data's first ~8 MB is
a dense GGUF header (7.8 MB, 291 tensors, tokenizer tables)
whereas synthetic headers are ~100 bytes — the cache readahead
in failing runs always dies after ~5-9 MB, i.e. around/just past
the header region. Also: real extents.bin is heavily fragmented
(written onto a nearly-full disk); synthetic stores are fresh
contiguous writes.

First bisect step done 17:48: 8 MB of real prefix + 8 MB zeros
(16 MB total) FAILS. Trigger lies within the first 8 MB — the
real GGUF header is 7,835,936 bytes, so plausibly the full
header region is required, or something inside it.

Next hypotheses to test (in order):
1. Continue bisecting: 1/2/4 MB real prefix padded to 16 MB —
   find the failing prefix length, then the failing byte range.
   Especially: does a store fail whose backing is EXACTLY the
   7,835,936-byte header plus one tensor?
2. Defragment/copy test without disk cost: hardlink already
   failed identically, so fragmentation is unlikely; skip.
3. Compare against memfs serving a >4 GB file: memfs is RAM-backed
   (a 4.5 GB memfs file is feasible) — if memfs also fails >4 GB,
   the fault is in WinFsp/Windows large-file handling on
   user-mode FSDs, not GdeFs, and the correct move is the
   WSL2/FUSE path (repo's target platform).
4. Try the FUSE adapter under WSL2 once a distro is installed —
   it bypasses the Windows cache-manager path entirely.

Adapter builds in `C:\tmp\gdefs\`: GdeFs5 (Init-aligned),
GdeFs6 (+ stable timestamps), GdeFs7 (no per-read logging,
current source). Source of truth: `src/tools/winfsp/GdeFs.cs`.

## Constraints to honour

- Disk C: ~6.7 GB free. NO large writes without checking space.
  Never create the 100 GB sparse store on this disk.
- Mojo cannot run here (no WSL2 distro). Ollama/llama binaries
  live in `C:\tmp\llama-b12284\`. WinFsp is installed; the C#
  adapter compiles with the in-box .NET Framework csc against
  `winfsp-msil.dll` (copies in `C:\tmp\gdefs\`).
- Push requires escalated git with
  `-c credential.helper=manager`.
