from addressing import coordinate_to_offset, coordinate_to_offset_raw
from phonological import compare, universal_geometric_hash

def main() raises:
    var semantic_left = String("Quantum")
    var semantic_right = String("Symmetry")
    var exact_left = String("neural0")
    var exact_right = String("quantum1")

    var dist = compare(semantic_left, semantic_right)
    var neural_hash = universal_geometric_hash(exact_left)
    var quantum_hash = universal_geometric_hash(exact_right)
    var neural_raw = coordinate_to_offset_raw(neural_hash.data)
    var quantum_raw = coordinate_to_offset_raw(quantum_hash.data)
    var neural_aligned = coordinate_to_offset(neural_hash.data)
    var quantum_aligned = coordinate_to_offset(quantum_hash.data)

    print("--- GDE Cross-Hardware Consistency Check ---")
    print("Comparing:", semantic_left, "vs", semantic_right)
    print("Distance Result:", dist)
    print("")
    print("Raw offsets:")
    print(" ", exact_left, "->", neural_raw)
    print(" ", exact_right, "->", quantum_raw)
    print("Aligned offsets:")
    print(" ", exact_left, "->", neural_aligned)
    print(" ", exact_right, "->", quantum_aligned)

    var expected_distance = Float64(0.36952140243502)
    var expected_neural_raw = UInt64(88169886449)
    var expected_quantum_raw = UInt64(87171484462)
    var expected_neural_aligned = UInt64(88169886208)
    var expected_quantum_aligned = UInt64(87171484416)
    var tolerance = Float64(0.000000001)
    var diff = dist - expected_distance
    if diff < 0:
        diff = -diff

    if (
        diff < tolerance
        and neural_raw == expected_neural_raw
        and quantum_raw == expected_quantum_raw
        and neural_aligned == expected_neural_aligned
        and quantum_aligned == expected_quantum_aligned
    ):
        print("STATUS: VERIFIED - deterministic outputs match baseline")
    else:
        print("STATUS: VARIANCE DETECTED")
        print("Distance diff:", diff)
