"""Shared .up container / HLKJ flash format helpers (layout: docs/reference/up-format.md)."""
import struct

MAGIC = b"CONFIG"
BODY = 0x100


def crc16(data: bytes, crc: int = 0xFFFF) -> int:
    """CRC16/CCITT-FALSE (poly 0x1021, init 0xFFFF) - matches the firmware."""
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def index_offset(flash) -> int:
    return struct.unpack_from("<I", flash, 0x20)[0]


def parse_index(flash, idx_off=None):
    """Partition index of a flash image (= .up body): (version, [(tag, addr, length, crc)]).

    Tags are the raw 4 bytes; entry i sits at idx_off + 16 + 16 * i.
    """
    if idx_off is None:
        idx_off = index_offset(flash)
    count, version = struct.unpack_from("<II", flash, idx_off)
    return version, [struct.unpack_from("<4sIII", flash, idx_off + 16 + 16 * i)
                     for i in range(count)]
