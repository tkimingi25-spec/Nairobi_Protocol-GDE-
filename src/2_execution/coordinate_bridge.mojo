from std.collections import List
from addressing import DEFAULT_ADDRESS_SPACE, default_weights, slot_align, weighted_offset_raw
from phonological import HashVector, universal_geometric_hash, compare

comptime DIMENSIONS = 24

struct CoordinateBridge:
    var base_address: UInt64
    var address_space: UInt64
    var weights: SIMD[DType.float64, 24]

    def __init__(out self, base_address: UInt64, address_space: UInt64):
        self.base_address = base_address
        self.address_space = address_space
        self.weights = default_weights()

    def set_weights(mut self, weights: SIMD[DType.float64, 24]):
        self.weights = weights

    def coordinate_to_offset(self, vector: HashVector) -> UInt64:
        var raw = weighted_offset_raw(vector.data, self.weights, self.address_space)
        return self.base_address + slot_align(raw)

    def word_to_offset(self, word: String) -> UInt64:
        var vector = universal_geometric_hash(word)
        return self.coordinate_to_offset(vector)

    def words_are_close(self, word_a: String, word_b: String, threshold: Float64) -> Bool:
        var dist = compare(word_a, word_b)
        return dist < threshold


def main() raises:
    var address_space = DEFAULT_ADDRESS_SPACE
    var bridge = CoordinateBridge(
        base_address=UInt64(0),
        address_space=address_space
    )

    print("--- GDE Coordinate Bridge ---")
    print("Address Space: 100GB")
    print("")

    print("Word -> Deterministic Offset:")
    var words = List[String]()
    words.append("Neural")
    words.append("Logic")
    words.append("Quantum")
    words.append("Apple")
    words.append("Orbit")
    for i in range(len(words)):
        var word = words[i]
        var offset = bridge.word_to_offset(word)
        print(" ", word, "->", offset, "bytes")

    print("")
    print("Determinism Check (same word, 3 calls):")
    for _ in range(3):
        var offset = bridge.word_to_offset("Quantum")
        print("  Quantum ->", offset)

    print("")
    print("Semantic Proximity Check:")
    var left = List[String]()
    var right = List[String]()
    left.append("Neural")
    right.append("Logic")
    left.append("Apple")
    right.append("Orbit")
    left.append("Sensor")
    right.append("Sensors")
    for i in range(len(left)):
        var a = left[i]
        var b = right[i]
        var close = bridge.words_are_close(a, b, Float64(0.3))
        print(" ", a, "~", b, "->", close)

    print("")
    print("RESULT: Coordinate Bridge operational.")
