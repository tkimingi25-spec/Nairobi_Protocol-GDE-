from std.collections import List
from std.time import perf_counter_ns
from addressing import SLOT_SIZE, coordinate_to_offset
from phonological import universal_geometric_hash

def main() raises:
    var file_path = "knowledge_store.bin"

    var keys = List[String]()
    var values = List[String]()

    keys.append("neural network architecture")
    values.append("Neural networks are computational models inspired by the human brain using layers of connected nodes")
    keys.append("quantum computing basics")
    values.append("Quantum computing uses quantum mechanical phenomena such as superposition and entanglement")
    keys.append("mmap memory mapping")
    values.append("Memory mapping allows files to be accessed as if they were in RAM using virtual address space")
    keys.append("retrieval augmented generation")
    values.append("RAG combines language models with external knowledge retrieval to produce accurate responses")
    keys.append("geometric determinism engine")
    values.append("GDE uses deterministic coordinate mapping to achieve O1 retrieval without scanning knowledge")
    keys.append("nairobi kenya technology")
    values.append("Nairobi is the technology hub of East Africa with a growing ecosystem of software engineers")
    keys.append("offline artificial intelligence")
    values.append("Offline AI runs on local hardware without internet connectivity preserving privacy and cost")
    keys.append("transformer attention mechanism")
    values.append("Transformers use self-attention to weigh importance of different tokens when generating output")
    keys.append("sparse file mmap storage")
    values.append("Sparse files allocate disk space only for written regions allowing 100GB files on 4GB RAM")
    keys.append("deterministic addressing system")
    values.append("Deterministic addressing maps any input to a fixed unique memory location using mathematics")

    print("--- GDE Knowledge Store ---")
    print("Writing", len(keys), "knowledge chunks to mmap file...")
    print("File:", file_path)
    print("")

    with open(file_path, "rw") as f:
        var t_start = perf_counter_ns()

        for i in range(len(keys)):
            var vec = universal_geometric_hash(keys[i])
            var offset = coordinate_to_offset(vec.data)
            _ = f.seek(offset)
            f.write(values[i])
            f.write("\n")

        var t_end = perf_counter_ns()
        var write_ms = Float64(t_end - t_start) / 1_000_000.0

        print("Write complete:", len(keys), "chunks")
        print("Write time:   ", write_ms, "ms")
        print("")

        print("Verifying all chunks...")
        var verified = 0
        var failed   = 0

        for i in range(len(keys)):
            var vec    = universal_geometric_hash(keys[i])
            var offset = coordinate_to_offset(vec.data)
            _ = f.seek(offset)
            var result = f.read(Int(SLOT_SIZE))
            if len(result) > 0:
                verified += 1
                print("  OK  offset:", offset, "key:", keys[i])
            else:
                failed += 1
                print("  FAIL offset:", offset, "key:", keys[i])

        print("")
        print("Verified:", verified, "| Failed:", failed)
        print("RESULT: Knowledge store complete.")
