# Deployment Guide

## Target

Generic `x86_64` laptop with `SSE4.2`, `AVX`, and 4 GB RAM.

## Dependencies

Install Pixi:

```bash
curl -fsSL https://pixi.sh/install.sh | sh
```

Install the project environment:

```bash
pixi project channel add https://conda.modular.com/max
pixi install
```

The Pixi environment provides Python, MAX/Mojo, NetworkX, SQLite, and command aliases from `pixi.toml`.

## Verification Path

Before deployment, run:

```bash
pixi run test-smoke
```

For the long structured-store write benchmark:

```bash
pixi run stress-v2
```

## Build Path

Use WSL after reboot and Ubuntu provisioning:

```bash
curl -fsSL https://pixi.sh/install.sh | sh
pixi install
pixi run mojo -I src/1_gateway tests/phonological_seed.mojo
bash build_portable.sh
```

This emits:

- `bin/logic_engine_portable.o`
- `bin/logic_engine_portable.s`

The current Mojo toolchain does not fully link cross-platform executables directly during cross-compilation, so the object file should be linked on the target-compatible toolchain from within WSL or a Linux CI runner.

## Atlas Transfer

Copy these assets together:

- `bin/logic_engine_portable` or the linked final executable
- `data/subgraphs/*.bin`
- `data/global_ontology.db`

Keep the executable and atlas data on SSD storage to preserve the mmap paging assumptions in `atlas_manager.mojo`.

## Thermal / Energy Estimate

These are engineering estimates, not measured hardware telemetry:

- Idle atlas residency with sparse queries: `4 W` to `7 W`
- Sustained SIMD-heavy query bursts: `9 W` to `15 W`
- Expected safe batch size on 4 GB RAM: keep working sets under `512 MB`
- Recommended deployment mode: short burst workloads with SSD-backed paging, not large in-memory graph expansion

## Practical Notes

- Prefer one mmap-backed subgraph family at a time on 4 GB hardware.
- Use the `finance.bin` and `sensors.bin` atlas split to avoid cross-domain cache pollution.
- Benchmark from AC power first, then re-check latency on battery because older mobile CPUs often downclock aggressively.
- Keep generated files such as `knowledge_store.bin`, `knowledge_store_v2.bin`, and `data/global_ontology.db` out of commits.
