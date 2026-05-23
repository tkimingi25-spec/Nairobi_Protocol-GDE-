from std.math import sqrt, cos

comptime SIGNAL_LEN = 32
comptime HASH_DIM = 24
comptime PI = 3.141592653589793

struct HashVector(Copyable, Movable):
    var data: SIMD[DType.float64, 24]

    def __init__(out self):
        self.data = SIMD[DType.float64, 24](0)

    def distance(self, other: HashVector) -> Float64:
        var diff = self.data - other.data
        return sqrt((diff * diff).reduce_add())

def universal_geometric_hash(text: String) -> HashVector:
    var hash_obj = HashVector()
    var lowered = text.lower()
    var signal = SIMD[DType.float64, 32](0)
    var length = lowered.byte_length()
    if length > SIGNAL_LEN // 2:
        length = SIGNAL_LEN // 2
    var previous = Int(0)
    for i in range(length):
        var char_val = Int(lowered.as_bytes()[i])
        signal[i * 2] = Float64(char_val)
        signal[i * 2 + 1] = Float64((char_val - previous + 256) % 256)
        previous = char_val
    if length * 2 < SIGNAL_LEN:
        signal[length * 2] = Float64(length * 17)
    var scale0 = sqrt(1.0 / Float64(SIGNAL_LEN))
    var scale = sqrt(2.0 / Float64(SIGNAL_LEN))
    for k in range(HASH_DIM):
        var sum_val = 0.0
        for n in range(SIGNAL_LEN):
            sum_val += signal[n] * cos(PI * Float64(k) * (Float64(n) + 0.5) / Float64(SIGNAL_LEN))
        hash_obj.data[k] = (scale0 if k == 0 else scale) * sum_val
    var norm = sqrt((hash_obj.data * hash_obj.data).reduce_add())
    if norm > 0:
        hash_obj.data = hash_obj.data / norm
    return hash_obj^

def compare(left: String, right: String) -> Float64:
    var h1 = universal_geometric_hash(left)
    var h2 = universal_geometric_hash(right)
    return h1.distance(h2)
