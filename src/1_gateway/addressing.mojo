from phonological import HASH_DIM

comptime DEFAULT_ADDRESS_SPACE = UInt64(100) * 1024 * 1024 * 1024
comptime SLOT_SIZE = UInt64(256)

def default_weights() -> SIMD[DType.float64, HASH_DIM]:
    var weights = SIMD[DType.float64, HASH_DIM](0.0)
    for i in range(HASH_DIM):
        weights[i] = Float64((i + 1) * 2654435761)
    return weights

def weighted_offset_raw(
    vector: SIMD[DType.float64, HASH_DIM],
    weights: SIMD[DType.float64, HASH_DIM],
    address_space: UInt64,
) -> UInt64:
    var weighted_sum = Float64(0.0)
    for i in range(HASH_DIM):
        var value = vector[i]
        if value < 0:
            value = -value
        weighted_sum += value * weights[i]
    return UInt64(weighted_sum % Float64(address_space))

def coordinate_to_offset_raw(
    vector: SIMD[DType.float64, HASH_DIM],
    address_space: UInt64 = DEFAULT_ADDRESS_SPACE,
) -> UInt64:
    return weighted_offset_raw(vector, default_weights(), address_space)

def slot_align(
    raw_offset: UInt64,
    slot_size: UInt64 = SLOT_SIZE,
) -> UInt64:
    return (raw_offset // slot_size) * slot_size

def coordinate_to_offset(
    vector: SIMD[DType.float64, HASH_DIM],
    address_space: UInt64 = DEFAULT_ADDRESS_SPACE,
) -> UInt64:
    return slot_align(coordinate_to_offset_raw(vector, address_space))
