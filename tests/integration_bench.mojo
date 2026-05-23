from collections import List, Tuple
from phonological import compare

def main():
    var pairs = List[Tuple[String, String]]()
    pairs.append(("Apple", "Apples"))
    pairs.append(("Apple", "Orbit"))
    pairs.append(("Neural", "Logic"))
    pairs.append(("Sensor", "Sensors"))

    print("Integration benchmark harness")
    for i in range(len(pairs)):
        var a = pairs[i][0]
        var b = pairs[i][1]
        print(a, b, compare(a, b))
