from structured_store import StructuredStore
from std.collections import List

def main():
    try:
        var store = StructuredStore("smoke_store.bin")
        # Create a small open file and reuse handle
        with open("smoke_store.bin", "rw") as f:
            var keys = List[String]()
            keys.append("alpha")
            keys.append("beta")
            keys.append("gamma")

            for i in range(len(keys)):
                var k = keys[i]
                var v = String("value-") + to_string(i)
                var ok = store.write_with_handle(f, k, v)
                if not ok:
                    print("write failed for", k)
            for i in range(len(keys)):
                var k = keys[i]
                var got = store.read_with_handle(f, k)
                print("read", k, "=>", got)
    except e:
        print("Smoke test error:", e)
