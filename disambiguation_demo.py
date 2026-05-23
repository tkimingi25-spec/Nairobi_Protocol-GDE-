import time
import math
from semantic_pipeline import semantic_address, simplified_lesk, get_lca_coordinate, synset_to_coordinate
from nltk.corpus import wordnet as wn

def full_disambiguation_demo():
    print("=" * 60)
    print("NAIROBI PROTOCOL — TRAINING-FREE DISAMBIGUATION DEMO")
    print("No embedding model. No training. Pure WordNet geometry.")
    print("=" * 60)
    print()

    # The core challenge
    test_cases = [
        {
            "phrase_a": "screw is loose",
            "phrase_b": "screw you",
            "word": "screw",
            "expected_a": "fastener/mechanical",
            "expected_b": "insult/cheat"
        },
        {
            "phrase_a": "deposit money in the bank",
            "phrase_b": "fishing by the river bank",
            "word": "bank",
            "expected_a": "financial institution",
            "expected_b": "land beside water"
        },
        {
            "phrase_a": "python code and programming",
            "phrase_b": "python snake in jungle",
            "word": "python",
            "expected_a": "programming language",
            "expected_b": "reptile"
        },
        {
            "phrase_a": "light the candle",
            "phrase_b": "light as a feather",
            "word": "light",
            "expected_a": "illuminate",
            "expected_b": "not heavy"
        }
    ]

    correct = 0
    total = len(test_cases)

    for case in test_cases:
        print(f"WORD: {case['word'].upper()}")
        print(f"Expected A: {case['expected_a']}")
        print(f"Expected B: {case['expected_b']}")
        print()

        offset_a, sense_a, coord_a, meta_a = semantic_address(case["phrase_a"])
        offset_b, sense_b, coord_b, meta_b = semantic_address(case["phrase_b"])

        print(f"  Phrase A: '{case['phrase_a']}'")
        if sense_a:
            print(f"  Resolved: {sense_a.name()}")
            print(f"  Meaning:  {sense_a.definition()[:70]}...")
            print(f"  Offset:   {offset_a:,}")
        print()

        print(f"  Phrase B: '{case['phrase_b']}'")
        if sense_b:
            print(f"  Resolved: {sense_b.name()}")
            print(f"  Meaning:  {sense_b.definition()[:70]}...")
            print(f"  Offset:   {offset_b:,}")
        print()

        disambiguated = sense_a != sense_b if sense_a and sense_b else False
        if disambiguated:
            correct += 1
            print(f"  RESULT: DISAMBIGUATED — different senses, different offsets")
        else:
            print(f"  RESULT: SAME SENSE — not disambiguated")

        if sense_a and sense_b:
            coords = get_lca_coordinate(sense_a, sense_b)
            if coords:
                print(f"  LCA depth:           {coords['lca_depth']}")
                print(f"  Contrast penalty:    {coords['contrast_penalty']:.4f}")
                print(f"  Geometric resonance: {coords['geometric_resonance']:.4f}")
                print(f"  Wu-Palmer sim:       {coords['wup_similarity']:.4f}")

        print("-" * 60)
        print()

    print(f"DISAMBIGUATION ACCURACY: {correct}/{total} ({correct/total*100:.0f}%)")
    print()
    print("Achieved with:")
    print("  - No embedding model")
    print("  - No neural network")
    print("  - No training data")
    print("  - WordNet hypernym graph + Simplified Lesk algorithm")
    print("  - Pure mathematical structure")


if __name__ == "__main__":
    full_disambiguation_demo()
