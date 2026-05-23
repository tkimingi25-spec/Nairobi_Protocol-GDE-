# Testing

This document records the current test commands and the latest local verification values.

Latest verification date: 2026-05-23.

## Install

```bash
curl -fsSL https://pixi.sh/install.sh | sh
pixi project channel add https://conda.modular.com/max
pixi install
```

## Smoke Suite

```bash
pixi run test-smoke
```

This runs the lightweight checks:

- `seed-ref`
- `bench-refinery`
- `seed-mojo`
- `bench-mojo`
- `integrity`
- `store-write`
- `query`
- `collision`
- `stress-mmap`
- `stress-1m`

It does not run the long structured-store 1M write stress test.

## Individual Commands

```bash
pixi run seed-ref
pixi run bench-refinery
pixi run seed-mojo
pixi run bench-mojo
pixi run integrity
```

Storage setup and direct retrieval:

```bash
truncate -s 100G knowledge_store.bin
pixi run store-write
pixi run query
```

Benchmarks:

```bash
pixi run bench-retrieval
pixi run collision
pixi run consistency
```

Sparse-file stress checks:

```bash
truncate -s 100G stress_test_model.bin
pixi run stress-mmap
pixi run stress-1m
```

Long structured-store write stress:

```bash
pixi run stress-v2
```

## Latest Results

### Python Hash Reference

Command:

```bash
pixi run seed-ref
```

Result:

```json
{
  "Neural_vs_Logic": 0.8740841823795337,
  "Apple_vs_Apples": 0.20971053760479863,
  "Apple_vs_Orbit": 0.9147438005967382,
  "seed_success": true
}
```

Meaning: the hash reference preserves the expected local relation that `Apple` is closer to `Apples` than to `Orbit`.

### Python Refinery Benchmark

Command:

```bash
pixi run bench-refinery
```

Result:

```json
{
  "seed": {
    "Apple_Apples": 0.20971053760479863,
    "Apple_Orbit": 0.9147438005967382,
    "Neural_Logic": 0.8740841823795337,
    "success": true,
    "resonance_ratio": 4.361935318293738,
    "elapsed_seconds_for_5000_rounds": 9.65678703499907
  },
  "refinery": {
    "ingest_seconds": 0.07244391499989433,
    "logic_depth": 0.6666666666666666,
    "geometric_resonance": 0.36666666666666664
  }
}
```

### Mojo Hash Benchmark

Command:

```bash
pixi run bench-mojo
```

Result:

```text
Integration benchmark harness
Apple Apples 0.15300060204779853
Apple Orbit 0.8014419520695584
Neural Logic 0.7830748832838954
Sensor Sensors 0.18809297007552897
```

Meaning: the Mojo benchmark now compiles under the current Mojo toolchain and confirms expected relative distances.

### Integrity

Command:

```bash
pixi run integrity
```

Result:

```text
CRC32: PASS
FNV1A deterministic: PASS 18007334074686647077
```

### Knowledge Store

Commands:

```bash
truncate -s 100G knowledge_store.bin
pixi run store-write
pixi run query
```

Results:

```text
Write time: 1.229461 ms
Verified: 10 | Failed: 0
Average query latency: 82.0573 us
```

### Retrieval Benchmark

Command:

```bash
pixi run bench-retrieval
```

Result:

```text
Phase 1 (addressing only): 26.046829635 us/query
Phase 2 (full retrieval):  25.709419067 us/query
Queries/sec:               38896.25033509902
Read overhead:             -0.337410568 us/query
Complexity:                O(1)
Exact:                     Yes
```

Meaning: read overhead is below this benchmark's noise floor; hash/address computation dominates.

### Collision Benchmark

Command:

```bash
pixi run collision
```

Result:

```text
Words tested:     10000
Collisions found: 0
Collision rate:   0.0%
Time taken:       271.322693 ms
```

### Consistency Baseline

Command:

```bash
pixi run consistency
```

Result:

```text
Distance Result: 0.36952140243502
neural0 raw/aligned:  88169886449 / 88169886208
quantum1 raw/aligned: 87171484462 / 87171484416
STATUS: VERIFIED - deterministic outputs match baseline
```

### Sparse-File Stress

Commands:

```bash
truncate -s 100G stress_test_model.bin
pixi run stress-mmap
pixi run stress-1m
```

Results:

```text
100GB boundary jump: PASS
1,000,000 seeks:     PASS
Data at 0GB:         A
Data at 100GB:       Z
```

### Structured Store Stress

Command:

```bash
pixi run stress-v2
```

Result:

```text
Target Reached: 1000000
Total Time (ms): 73086.115428
Throughput (ops/sec): 13682.48940505176
```

This is a long benchmark. It should not be part of the default smoke suite.

## Known Environment Messages

In this sandbox, Mojo prints:

```text
Failed to initialize Crashpad. Crash reporting will not be available.
```

The programs still run. This is an environment crash-reporting limitation, not a GDE test failure.
