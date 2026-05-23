import math
import time
from nltk.corpus import wordnet as wn

ADDRESS_SPACE = 100 * 1024 * 1024 * 1024
_coord_cache = {}

POS_MAP = {"n": 10000.0, "v": 20000.0, "a": 30000.0, "r": 40000.0, "s": 50000.0}

def get_hypernym_depth(synset):
    paths = synset.hypernym_paths()
    if not paths:
        return 0
    return max(len(path) for path in paths)

def synset_to_coordinate(synset):
    key = synset.name()
    if key in _coord_cache:
        return _coord_cache[key]

    coord = [0.0] * 24

    # Dim 0-7: hypernym path depths
    paths = synset.hypernym_paths()
    if paths:
        path = max(paths, key=len)
        for i, ancestor in enumerate(path[:8]):
            coord[i] = float(get_hypernym_depth(ancestor))

    # Dim 8: synset depth
    coord[8] = float(get_hypernym_depth(synset))

    # Dim 9-11: synset offset spread across 3 dimensions — key uniqueness guarantee
    raw_offset = synset.offset()
    coord[9]  = float(raw_offset % 10000)
    coord[10] = float((raw_offset // 10000) % 10000)
    coord[11] = float(raw_offset // 100000)

    # Dim 12: POS with large separation
    coord[12] = POS_MAP.get(synset.pos(), 0.0)

    # Dim 13-20: lemma characters
    lemma = synset.name().split(".")[0]
    for i, ch in enumerate(lemma[:8]):
        coord[13 + i] = float(ord(ch)) * (i + 1)

    # Dim 21: hyponym count
    coord[21] = float(len(synset.hyponyms()) % 10000)

    # Dim 22: hypernym count
    coord[22] = float(len(synset.hypernyms()))

    # Dim 23: definition word count * pos weight
    coord[23] = float(len(synset.definition().split())) * POS_MAP.get(synset.pos(), 1.0)

    _coord_cache[key] = coord
    return coord


def coordinate_to_offset(coord):
    weighted_sum = 0.0
    for i, v in enumerate(coord):
        weight = (i + 1) * 2654435761
        weighted_sum += abs(v) * weight
    return int(weighted_sum % ADDRESS_SPACE)


def simplified_lesk(word, context_sentence):
    context_words = set(context_sentence.lower().split())
    best_sense = None
    best_score = -1
    for synset in wn.synsets(word):
        signature = set(synset.definition().lower().split())
        for example in synset.examples():
            signature.update(example.lower().split())
        for hypernym in synset.hypernyms():
            signature.update(hypernym.definition().lower().split())
        score = len(context_words.intersection(signature))
        if score > best_score:
            best_score = score
            best_sense = synset
    if best_sense is None and wn.synsets(word):
        best_sense = wn.synsets(word)[0]
    return best_sense


def get_lca_coordinate(synset_a, synset_b):
    if synset_a is None or synset_b is None:
        return None
    depth_a = get_hypernym_depth(synset_a)
    depth_b = get_hypernym_depth(synset_b)
    lca_synsets = synset_a.lowest_common_hypernyms(synset_b)
    lca_depth = get_hypernym_depth(lca_synsets[0]) if lca_synsets else 0
    penalty = abs(depth_a - lca_depth) + abs(depth_b - lca_depth)
    penalty += 0.5 * abs(depth_a - depth_b)
    baseline = depth_a + depth_b + 1.0
    resonance = 1.0 - (penalty / baseline) if baseline > 0 else 0.0
    return {
        "lca_depth": lca_depth,
        "left_depth": depth_a,
        "right_depth": depth_b,
        "contrast_penalty": penalty,
        "geometric_resonance": resonance,
        "wup_similarity": synset_a.wup_similarity(synset_b) or 0.0
    }


def semantic_address(phrase):
    words = phrase.lower().split()
    primary_word = max(words, key=lambda w: len(wn.synsets(w)))
    primary_sense = simplified_lesk(primary_word, phrase)
    if primary_sense is None:
        return None, None, [0.0]*24, {}
    coordinate = synset_to_coordinate(primary_sense)
    offset = coordinate_to_offset(coordinate)
    metadata = {
        "phrase": phrase,
        "primary_word": primary_word,
        "sense": primary_sense.name(),
        "definition": primary_sense.definition(),
        "depth": get_hypernym_depth(primary_sense),
        "offset": offset
    }
    return offset, primary_sense, coordinate, metadata


if __name__ == "__main__":
    print("=== Semantic Pipeline Test ===")
    test_phrases = [
        "screw is loose",
        "screw you",
        "bank by the river",
        "money in the bank",
        "python programming language",
        "python is a snake",
    ]
    for phrase in test_phrases:
        offset, sense, coord, meta = semantic_address(phrase)
        if sense:
            print(f"Phrase:  {phrase}")
            print(f"Sense:   {meta['sense']}")
            print(f"Meaning: {meta['definition'][:60]}...")
            print(f"Offset:  {offset:,}")
            print()
