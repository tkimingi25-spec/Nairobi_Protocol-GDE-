from std.collections import List
from phonological import compare

def main():
    var left = List[String]()
    var right = List[String]()
    left.append("Apple")
    right.append("Apples")
    left.append("Apple")
    right.append("Orbit")
    left.append("Neural")
    right.append("Logic")
    left.append("Sensor")
    right.append("Sensors")

    print("Integration benchmark harness")
    for i in range(len(left)):
        var a = left[i]
        var b = right[i]
        print(a, b, compare(a, b))
