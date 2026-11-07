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


# OTAP (docs/research/updater-otap.md) erases 0x4000..0x3000+total on 82, writes 83 frames at any address with no
# bounds check, and CRCs flash[0x3000:0x3000+total]. Both are fixed at 0x3000, and its OTAP/PSMP
# records are pinned, so an image is only safe to stream if its layout matches that.
OTA_INDEX_ADDR = 0x3000
OTA_FIRM_ADDR = 0x4000
OTA_INDEX_MAX = 0x80
# OTAP 82 erases 0x4000..0x10000, then 64 KiB blocks for (total - 0xD000) unsigned, then 4 KiB
# sectors rounded up: erase end = 0x3000 + total rounded up to 4 KiB, or the whole chip if total < 0xD000.
OTA_MIN_OTAP = 0x10000


def ota_image_problems(data):
    """Reasons a .up must not be streamed over 55AA OTA (empty list = ok)."""
    if data[:6] != MAGIC:
        return ["not a .up (missing CONFIG magic)"]
    body = data[BODY:]
    length, outer = struct.unpack_from("<IH", data, 0x10)
    bad = []
    if length != len(body) or crc16(body) != outer:
        bad.append("CONFIG header length/CRC does not match the body")
    io = index_offset(body)
    if io != OTA_INDEX_ADDR:
        return bad + [f"index at 0x{io:x}; OTAP only handles an index at 0x{OTA_INDEX_ADDR:x}"]
    _, entries = parse_index(body, io)
    parts = {tag: (addr, ln, crc) for tag, addr, ln, crc in entries}
    index_len = (len(entries) + 1) * 16
    if index_len > OTA_INDEX_MAX:
        bad.append(f"index is {index_len} bytes, OTAP only buffers {OTA_INDEX_MAX}")
    if b"OTAP" not in parts or b"FIRM" not in parts:
        return bad + ["index has no OTAP or FIRM entry"]
    if parts[b"FIRM"][0] != OTA_FIRM_ADDR:
        bad.append(f"FIRM at 0x{parts[b'FIRM'][0]:x}, expected 0x{OTA_FIRM_ADDR:x}")
    otap = parts[b"OTAP"][0]
    if otap > len(body):
        bad.append(f"OTAP at 0x{otap:x} is past the end of the image")
    if otap < OTA_MIN_OTAP or otap & 0xFFF:
        bad.append(f"OTAP at 0x{otap:x}; 82's erase only stops short of it for a 4 KiB-aligned "
                   f"OTAP at >= 0x{OTA_MIN_OTAP:x} (lower wraps and erases the whole chip)")
    for tag, addr, ln, crc in entries:
        if tag in (b"OTAP", b"PSMP"):
            continue
        name = tag.decode("latin1")
        if addr < OTA_FIRM_ADDR or addr + ln > otap:
            bad.append(f"{name} 0x{addr:x}+0x{ln:x} is outside 0x{OTA_FIRM_ADDR:x}..0x{otap:x}")
        elif crc16(body[addr:addr + ln]) != crc:
            bad.append(f"{name} CRC mismatch")
    if any(body[io + index_len:OTA_FIRM_ADDR]):
        bad.append("index page padding is not all zero")
    return bad


def live_index_problems(raw, entries):
    """Compare a bud's index (C0 83 read at 0x3000) with an image's {tag: (addr, len, crc)}."""
    if len(raw) < 16:
        return ["live index read came back short"]
    count = struct.unpack_from("<I", raw, 0)[0]
    if not 1 <= count <= OTA_INDEX_MAX // 16 - 1 or len(raw) < (count + 1) * 16:
        return [f"live index has an implausible count ({count})"]
    live = {t: (a, n, c) for t, a, n, c in
            (struct.unpack_from("<4sIII", raw, 16 + 16 * i) for i in range(count))}
    bad = []
    for tag in (b"OTAP", b"PSMP"):
        if live.get(tag) != entries.get(tag):
            bad.append(f"live {tag.decode()} entry {live.get(tag)} != image {entries.get(tag)}")
    if live.get(b"FIRM", (None,))[0] != OTA_FIRM_ADDR:
        bad.append(f"live FIRM is not at 0x{OTA_FIRM_ADDR:x}")
    return bad
