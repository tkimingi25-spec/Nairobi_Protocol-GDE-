comptime FNV_OFFSET_BASIS = UInt64(14695981039346656037)
comptime FNV_PRIME = UInt64(1099511628211)

def fnv1a_64(key: String) -> UInt64:
    var hash_val = FNV_OFFSET_BASIS
    var length = key.byte_length()
    for i in range(length):
        var char_val = UInt64(Int(key.as_bytes()[i]))
        hash_val = hash_val ^ char_val
        hash_val = hash_val * FNV_PRIME
    return hash_val
