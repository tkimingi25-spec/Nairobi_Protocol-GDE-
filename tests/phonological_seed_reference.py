from __future__ import annotations

import json
import math
from typing import Iterable


SIGNAL_LEN = 32
HASH_DIM = 24


def _signal(text: str) -> list[float]:
    lowered = text.lower().encode("utf-8")[: SIGNAL_LEN // 2]
    signal = [0.0] * SIGNAL_LEN
    previous = 0
    for index, value in enumerate(lowered):
        signal[index * 2] = float(value)
        signal[index * 2 + 1] = float((value - previous) % 256)
        previous = value
    if len(lowered) < SIGNAL_LEN:
        signal[min(SIGNAL_LEN - 1, len(lowered) * 2)] = float(len(lowered) * 17)
    return signal


def _dct(signal: Iterable[float]) -> list[float]:
    source = list(signal)
    out: list[float] = []
    scale0 = math.sqrt(1.0 / SIGNAL_LEN)
    scale = math.sqrt(2.0 / SIGNAL_LEN)
    for k in range(HASH_DIM):
        acc = 0.0
        for n, value in enumerate(source):
            angle = math.pi / SIGNAL_LEN * (n + 0.5) * k
            acc += value * math.cos(angle)
        out.append(acc * (scale0 if k == 0 else scale))
    norm = math.sqrt(sum(value * value for value in out)) or 1.0
    return [value / norm for value in out]


def universal_geometric_hash(text: str) -> list[float]:
    return _dct(_signal(text))


def distance(left: str, right: str) -> float:
    lv = universal_geometric_hash(left)
    rv = universal_geometric_hash(right)
    return math.sqrt(sum((l - r) ** 2 for l, r in zip(lv, rv, strict=True)))


def main() -> None:
    report = {
        "Neural_vs_Logic": distance("Neural", "Logic"),
        "Apple_vs_Apples": distance("Apple", "Apples"),
        "Apple_vs_Orbit": distance("Apple", "Orbit"),
    }
    report["seed_success"] = report["Apple_vs_Apples"] < report["Apple_vs_Orbit"]
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
