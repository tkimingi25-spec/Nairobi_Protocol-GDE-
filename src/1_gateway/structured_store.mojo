from phonological import universal_geometric_hash
from addressing import coordinate_to_offset
from slot_format import SlotHeader, SLOT_SIZE, HEADER_SIZE, PAYLOAD_CAPACITY, MAX_PROBE_DEPTH, FLAG_OCCUPIED, FLAG_TOMBSTONE, serialize_header, parse_header, substring
from fingerprint import fnv1a_64
from integrity import crc32_compute

struct StructuredStore:
    var file_path: String

    def __init__(out self, file_path: String):
        self.file_path = file_path

    def write(self, key: String, value: String) raises -> Bool:
        var fingerprint = fnv1a_64(key)
        var vec = universal_geometric_hash(key)
        var base_offset = coordinate_to_offset(vec.data)
        
        var payload_len = value.byte_length()
        if payload_len > PAYLOAD_CAPACITY:
            payload_len = PAYLOAD_CAPACITY
        var payload_str = substring(value, 0, payload_len)
        var crc = crc32_compute(payload_str, payload_len)

        with open(self.file_path, "rw") as f:
            for probe in range(MAX_PROBE_DEPTH):
                var offset = base_offset + UInt64(probe) * SLOT_SIZE
                _ = f.seek(offset)
                var existing = f.read(HEADER_SIZE)

                var header = parse_header(existing)

                if header.is_continuation():
                    continue

                if header.is_empty() or header.is_tombstone() or header.key_fingerprint == fingerprint:
                    var new_header = SlotHeader()
                    new_header.key_fingerprint = fingerprint
                    new_header.payload_length = UInt16(payload_len)
                    new_header.flags = FLAG_OCCUPIED
                    new_header.crc32 = crc
                    
                    _ = f.seek(offset)
                    f.write(serialize_header(new_header))
                    f.write(payload_str)
                    
                    var pad_len = PAYLOAD_CAPACITY - payload_len
                    if pad_len > 0:
                        var pad = String("")
                        for i in range(pad_len):
                            pad += chr(0)
                        f.write(pad)
                    return True

        return False

    def read(self, key: String) raises -> String:
        var fingerprint = fnv1a_64(key)
        var vec = universal_geometric_hash(key)
        var base_offset = coordinate_to_offset(vec.data)

        with open(self.file_path, "rw") as f:
            for probe in range(MAX_PROBE_DEPTH):
                var offset = base_offset + UInt64(probe) * SLOT_SIZE
                _ = f.seek(offset)
                var existing = f.read(HEADER_SIZE)
                var header = parse_header(existing)

                if header.is_continuation():
                    continue

                if header.is_empty():
                    raise Error("Key not found")

                if header.is_tombstone():
                    continue

                if header.key_fingerprint == fingerprint:
                    var payload = f.read(Int(header.payload_length))
                    var check = crc32_compute(payload, Int(header.payload_length))
                    if check != header.crc32:
                        raise Error("CRC mismatch")
                    return payload

        raise Error("Key not found after max probes")
