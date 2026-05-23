from std.collections import List
from std.time import perf_counter_ns
from structured_store import StructuredStore

def main() raises:
    var file_path = "knowledge_store_v2.bin"
    
    # Initialize the file to avoid empty file seek errors
    with open(file_path, "w") as init_f:
        init_f.write("")
        
    var store = StructuredStore(file_path)

    var keys = List[String]()
    var values = List[String]()

    keys.append("neural network architecture")
    values.append("Neural networks are computational models inspired by the human brain using layers of connected nodes")
    keys.append("quantum computing basics")
    values.append("Quantum computing uses quantum mechanical phenomena such as superposition and entanglement")
    keys.append("mmap memory mapping")
    values.append("Memory mapping allows files to be accessed as if they were in RAM using virtual address space")

    print("--- GDE Structured Store V2 ---")
    print("Writing", len(keys), "knowledge chunks...")

    var t_start = perf_counter_ns()
    
    for i in range(len(keys)):
        var success = store.write(keys[i], values[i])
        if not success:
            print("Failed to write:", keys[i])

    var t_end = perf_counter_ns()
    var write_ms = Float64(t_end - t_start) / 1_000_000.0

    print("Write time:", write_ms, "ms")
    print("")

    print("Verifying all chunks...")
    var verified = 0
    var failed = 0

    for i in range(len(keys)):
        try:
            var result = store.read(keys[i])
            if result == values[i]:
                verified += 1
                print("  OK  key:", keys[i])
            else:
                failed += 1
                print("  FAIL content mismatch key:", keys[i])
        except e:
            failed += 1
            print("  FAIL read error:", e, "key:", keys[i])

    print("")
    print("Verified:", verified, "| Failed:", failed)
    print("RESULT: Structured store complete.")
