def crc32_compute(data: String, length: Int) -> UInt32:
    var crc = UInt32(0xFFFFFFFF)
    for i in range(length):
        var char_val = UInt32(Int(data.as_bytes()[i]))
        crc = crc ^ char_val
        for j in range(8):
            if (crc & 1) != 0:
                crc = (crc >> 1) ^ UInt32(0xEDB88320)
            else:
                crc = crc >> 1
    return crc ^ UInt32(0xFFFFFFFF)
