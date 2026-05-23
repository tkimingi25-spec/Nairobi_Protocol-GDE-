comptime SLOT_SIZE = UInt64(256)
comptime HEADER_SIZE = Int(32)
comptime PAYLOAD_CAPACITY = Int(224)
comptime MAX_PROBE_DEPTH = Int(64)
comptime FORMAT_VERSION = UInt8(0x01)

comptime FLAG_OCCUPIED = UInt8(1)
comptime FLAG_CONTINUATION = UInt8(2)
comptime FLAG_COMPRESSED = UInt8(4)
comptime FLAG_TOMBSTONE = UInt8(8)

struct SlotHeader:
    var key_fingerprint: UInt64
    var payload_length: UInt16
    var flags: UInt8
    var version: UInt8
    var crc32: UInt32

    def __init__(out self):
        self.key_fingerprint = 0
        self.payload_length = 0
        self.flags = 0
        self.version = FORMAT_VERSION
        self.crc32 = 0

    def is_occupied(self) -> Bool:
        return (self.flags & FLAG_OCCUPIED) != 0

    def is_tombstone(self) -> Bool:
        return (self.flags & FLAG_TOMBSTONE) != 0

    def is_continuation(self) -> Bool:
        return (self.flags & FLAG_CONTINUATION) != 0

    def is_empty(self) -> Bool:
        return not self.is_occupied() and not self.is_tombstone()

def to_hex(val: UInt64, width: Int) -> String:
    var res = String("")
    var chars = "0123456789ABCDEF"
    for i in range(width):
        var shift = UInt64((width - 1 - i) * 4)
        var idx = Int((val >> shift) & UInt64(0xF))
        res += chr(Int(chars.as_bytes()[idx]))
    return res

def parse_hex_sub(s: String, start: Int, length: Int) -> UInt64:
    var res = UInt64(0)
    for i in range(length):
        if start + i >= s.byte_length():
            break
        var c = Int(s.as_bytes()[start + i])
        var val = 0
        if c >= 48 and c <= 57:
            val = c - 48
        elif c >= 65 and c <= 70:
            val = c - 65 + 10
        elif c >= 97 and c <= 102:
            val = c - 97 + 10
        res = (res << 4) | UInt64(val)
    return res

def serialize_header(header: SlotHeader) -> String:
    var fp = to_hex(header.key_fingerprint, 16)
    var pl = to_hex(UInt64(header.payload_length), 4)
    var fl = to_hex(UInt64(header.flags), 2)
    var vr = to_hex(UInt64(header.version), 2)
    var cr = to_hex(UInt64(header.crc32), 8)
    return fp + pl + fl + vr + cr

def parse_header(data: String) -> SlotHeader:
    var h = SlotHeader()
    if data.byte_length() < HEADER_SIZE:
        return h
    h.key_fingerprint = parse_hex_sub(data, 0, 16)
    h.payload_length = UInt16(parse_hex_sub(data, 16, 4))
    h.flags = UInt8(parse_hex_sub(data, 20, 2))
    h.version = UInt8(parse_hex_sub(data, 22, 2))
    h.crc32 = UInt32(parse_hex_sub(data, 24, 8))
    return h

def substring(s: String, start: Int, length: Int) -> String:
    var res = String("")
    var end = start + length
    if end > s.byte_length():
        end = s.byte_length()
    for i in range(start, end):
        res += chr(Int(s.as_bytes()[i]))
    return res
