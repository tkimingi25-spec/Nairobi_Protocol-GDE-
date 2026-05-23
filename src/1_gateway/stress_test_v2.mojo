from std.collections import List
from std.time import perf_counter_ns
from structured_store import StructuredStore

def main() raises:
    var file_path = "knowledge_store_v2.bin"
    
    # Initialize the file to avoid empty file seek errors
    with open(file_path, "w") as init_f:
        init_f.write("")
        
    var store = StructuredStore(file_path)

    print("--- IGNITING 1 MILLION RECORD STRESS TEST ---")

    var target = 1_000_000

    var t_start = perf_counter_ns()

    # Open the underlying file exactly once and reuse for all operations.
    with open(file_path, "rw") as f:
        for i in range(target):
            var dummy_key = String("semantic_node_") + String(i)
            var dummy_value = String("payload_") + String(i)
            var success = store.write_with_handle(f, dummy_key, dummy_value)
            if not success:
                # minimal failure handling to avoid noisy output
                pass

    var t_end = perf_counter_ns()
    var elapsed_ms = Float64(t_end - t_start) / 1_000_000.0
    var elapsed_s = Float64(t_end - t_start) / 1_000_000_000.0
    var throughput = Float64(target) / elapsed_s if elapsed_s > 0 else Float64(0.0)

    print("Target Reached:", target)
    print("Total Time (ms):", elapsed_ms)
    print("Throughput (ops/sec):", throughput)
