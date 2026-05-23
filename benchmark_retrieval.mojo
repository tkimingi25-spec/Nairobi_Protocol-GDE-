from std.collections import List
from std.time import perf_counter_ns
from addressing import SLOT_SIZE, coordinate_to_offset
from phonological import universal_geometric_hash

comptime NUM_QUERIES   = 1_000_000

def main() raises:
    var file_path = "knowledge_store.bin"

    var keys = List[String]()
    keys.append("neural network architecture")
    keys.append("quantum computing basics")
    keys.append("mmap memory mapping")
    keys.append("retrieval augmented generation")
    keys.append("geometric determinism engine")
    keys.append("nairobi kenya technology")
    keys.append("offline artificial intelligence")
    keys.append("transformer attention mechanism")
    keys.append("sparse file mmap storage")
    keys.append("deterministic addressing system")
    var num_keys = len(keys)

    print("--- GDE Retrieval Benchmark ---")
    print("Pipeline: text -> hash -> offset -> seek -> read")
    print("Queries:", NUM_QUERIES)
    print("File: WSL native ext4 filesystem")
    print("")

    with open(file_path, "rw") as f:

        print("Warming up (1000 queries)...")
        for i in range(1000):
            var vec    = universal_geometric_hash(keys[i % num_keys])
            var offset = coordinate_to_offset(vec.data)
            _ = f.seek(offset)
            _ = f.read(Int(SLOT_SIZE))
        print("Warmup done.")
        print("")

        # Phase 1: address computation only — hash + offset + seek, no read
        print("Phase 1: Hash + offset + seek (no read) x", NUM_QUERIES)
        var t0 = perf_counter_ns()
        for i in range(NUM_QUERIES):
            var vec    = universal_geometric_hash(keys[i % num_keys])
            var offset = coordinate_to_offset(vec.data)
            _ = f.seek(offset)
        var t1 = perf_counter_ns()

        var p1_ms    = Float64(t1 - t0) / 1_000_000.0
        var p1_pq_us = (p1_ms / Float64(NUM_QUERIES)) * 1000.0
        print("  Total:       ", p1_ms, "ms")
        print("  Per query:   ", p1_pq_us, "us")
        print("  Queries/sec: ", Float64(NUM_QUERIES) / (p1_ms / 1000.0))
        print("")

        # Phase 2: full retrieval — hash + offset + seek + read
        print("Phase 2: Full retrieval (hash + seek + read) x", NUM_QUERIES)
        var t2 = perf_counter_ns()
        for i in range(NUM_QUERIES):
            var vec    = universal_geometric_hash(keys[i % num_keys])
            var offset = coordinate_to_offset(vec.data)
            _ = f.seek(offset)
            _ = f.read(Int(SLOT_SIZE))
        var t3 = perf_counter_ns()

        var p2_ms    = Float64(t3 - t2) / 1_000_000.0
        var p2_pq_us = (p2_ms / Float64(NUM_QUERIES)) * 1000.0
        print("  Total:       ", p2_ms, "ms")
        print("  Per query:   ", p2_pq_us, "us")
        print("  Queries/sec: ", Float64(NUM_QUERIES) / (p2_ms / 1000.0))
        print("")

        print("Summary")
        print("  Phase 1 (addressing only): ", p1_pq_us, "us per query")
        print("  Phase 2 (full retrieval):  ", p2_pq_us, "us per query")
        print("  Read overhead per query:   ", p2_pq_us - p1_pq_us, "us")
        print("  Complexity: O(1)")
        print("  Exact:      Yes")
        print("")
        print("RESULT: GDE Retrieval Benchmark complete.")
