from std.collections import List
from std.time import perf_counter_ns
from addressing import coordinate_to_offset
from phonological import universal_geometric_hash

comptime TEST_SIZE = 10000

def main() raises:
    print("--- GDE Mojo Collision Test ---")
    print("Testing", TEST_SIZE, "unique words")
    print("Address space: 100GB (slot-aligned)")
    print("------------------------------")

    var offsets = List[UInt64]()
    var words = List[String]()

    var base_words = List[String]()
    base_words.append("neural"); base_words.append("quantum")
    base_words.append("logic"); base_words.append("orbit")
    base_words.append("signal"); base_words.append("photon")
    base_words.append("atom"); base_words.append("electron")
    base_words.append("proton"); base_words.append("neutron")
    base_words.append("plasma"); base_words.append("fusion")
    base_words.append("fission"); base_words.append("entropy")
    base_words.append("symmetry"); base_words.append("tensor")
    base_words.append("nairobi"); base_words.append("kenya")
    base_words.append("algebra"); base_words.append("calculus")

    var num_base = len(base_words)

    var t_start = perf_counter_ns()

    var collisions = 0
    var generated = 0

    for i in range(TEST_SIZE):
        var base = base_words[i % num_base]
        var word = base + String(i)
        var vec = universal_geometric_hash(word)
        var offset = coordinate_to_offset(vec.data)

        for j in range(len(offsets)):
            if offsets[j] == offset:
                collisions += 1
                break

        offsets.append(offset)
        words.append(word)
        generated += 1

    var t_end = perf_counter_ns()
    var elapsed_ms = Float64(t_end - t_start) / 1_000_000.0

    print("")
    print("RESULTS:")
    print("Words tested:      ", generated)
    print("Collisions found:  ", collisions)
    print("Collision rate:    ", Float64(collisions) / Float64(generated) * 100.0, "%")
    print("Time taken:        ", elapsed_ms, "ms")
    print("")

    print("Sample offsets:")
    for i in range(5):
        print(" ", words[i], "->", offsets[i])

    print("")
    print("RESULT: Mojo collision test complete.")
