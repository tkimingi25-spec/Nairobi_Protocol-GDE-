from phonological import universal_geometric_hash
from persistence import GatewayStore
from std.collections import List

def main():
    try:
        var store = GatewayStore("engine_vault.bin")
        var test_words = List[String]()
        test_words.append("Neural")
        test_words.append("Brain")
        test_words.append("Logic")
        test_words.append("Quantum")
        test_words.append("Symmetry")

        print("--- Batch Global Seeding ---")
        for i in range(len(test_words)):
            var word = test_words[i]
            store.save_vector(word, universal_geometric_hash(word))
            print("Indexed & Vaulted: " + word)

        print("--- Precision Retrieval ---")
        var target = String("Quantum")
        var retrieved = store.load_vector_indexed(target)
        print("Success! Jumped to " + target)
        print("Coordinate[0]:", retrieved.data[0])

    except e:
        print("Engine Stress Error: ", e)
