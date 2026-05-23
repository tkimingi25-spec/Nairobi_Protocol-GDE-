from integrity import crc32_compute
from fingerprint import fnv1a_64

def main():
    print("-- Integrity Unit Tests --")

    var s = String("123456789")
    var crc = crc32_compute(s, 9)
    var expected = UInt32(0xCBF43926)
    if crc == expected:
        print("CRC32: PASS")
    else:
        print("CRC32: FAIL", crc)

    var a = fnv1a_64(String("test"))
    var b = fnv1a_64(String("test"))
    if a == b:
        print("FNV1A deterministic: PASS", a)
    else:
        print("FNV1A deterministic: FAIL", a, b)
