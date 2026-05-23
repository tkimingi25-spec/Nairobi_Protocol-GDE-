from collections import List
from std.time import perf_counter_ns
from addressing import SLOT_SIZE, coordinate_to_offset
from phonological import universal_geometric_hash

def main() raises:
    var file_path = "knowledge_store.bin"

    var queries = List[String]()
    queries.append("neural network architecture")
    queries.append("quantum computing basics")
    queries.append("mmap memory mapping")
    queries.append("retrieval augmented generation")
    queries.append("geometric determinism engine")
    queries.append("nairobi kenya technology")
    queries.append("offline artificial intelligence")
    queries.append("transformer attention mechanism")
    queries.append("sparse file mmap storage")
    queries.append("deterministic addressing system")

    print("--- GDE Query Engine ---")
    print("Querying knowledge store...")
    print("")

    with open(file_path, "rw") as f:
        var total_us = Float64(0.0)

        for i in range(len(queries)):
            var t_start = perf_counter_ns()
            var vec     = universal_geometric_hash(queries[i])
            var offset  = coordinate_to_offset(vec.data)
            _ = f.seek(offset)
            var result  = f.read(Int(SLOT_SIZE))
            var t_end   = perf_counter_ns()

            var latency_us = Float64(t_end - t_start) / 1000.0
            total_us += latency_us

            print("Query:   ", queries[i])
            print("Offset:  ", offset)
            print("Result:  ", result)
            print("Latency: ", latency_us, "us")
            print("")

        var avg_us = total_us / Float64(len(queries))
        print("Average latency:", avg_us, "us")
        print("Average latency:", avg_us / 1000.0, "ms")
        print("")
        print("RESULT: Query engine complete.")
