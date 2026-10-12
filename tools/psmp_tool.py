#!/usr/bin/env python3
"""Read, verify and edit a Smartlink PSMP (NV key/value) partition.

Usage:
  psmp_tool.py <flash_dump.bin | psmp.bin> [--all]
  psmp_tool.py verify <flash_dump.bin | psmp.bin>
  psmp_tool.py set <flash_dump.bin | psmp.bin> key=value [...] -o <out.bin>

Accepts either a bare PSMP blob or a raw HLKJ flash dump (PSMP is located via the
partition table pointer at HLKJ+0x20).  Listing prints live records by default; --all also
shows superseded (flag 0xFE) records in log order.  `verify` recomputes every record check.
`set` appends records the way the firmware does (old record flagged 0xFE, new one appended)
and writes a new file; values are text, `@file` for raw bytes, or `:hex`.

Record layout (see docs/09-psmp-nvds.md):
  55 AA | flag (FF live / FE stale) | u32 check | u16 value_len | u16 key_id | u8 key_len |
  key | value

The check is CRC32 (reflected, poly 0xEDB88320, init 0, no final xor) taken over the key, then
the value, then the 12-byte header with flag = FF and the check field = FF FF FF FF.
Never writes to a device: output always goes to a file.
"""
import struct, sys
from pathlib import Path

from upfmt import parse_index

HDR = 12
MARKER = b"\x55\xaa"
LIVE, STALE = 0xFF, 0xFE
MAX_KEY_ID = 0x200

_TAB = []
for _i in range(256):
    _c = _i
    for _ in range(8):
        _c = (_c >> 1) ^ (0xEDB88320 if _c & 1 else 0)
    _TAB.append(_c)


def crc32_nvds(data: bytes, crc: int = 0) -> int:
    """Reflected CRC32 as the firmware's table loop computes it (no init/final xor)."""
    for b in data:
        crc = _TAB[(b ^ crc) & 0xFF] ^ (crc >> 8)
    return crc


def record_check(key: bytes, val: bytes, key_id: int) -> int:
    """The u32 check field of a record: key, then value, then the masked header."""
    hdr = bytearray(MARKER + bytes([LIVE]) + b"\xff" * 4 + b"\0" * 5)
    struct.pack_into("<HH", hdr, 7, len(val), key_id)
    hdr[11] = len(key)
    return crc32_nvds(bytes(hdr), crc32_nvds(val, crc32_nvds(key)))


def find_psmp(data):
    """(psmp_bytes, offset) - offset is 0 for a bare partition."""
    if data[:4] != b"HLKJ":
        return data, 0
    for tag, addr, ln, _ in parse_index(data)[1]:
        if tag == b"PSMP":
            return data[addr:addr + ln], addr
    sys.exit("no PSMP partition in table")

def parse(p):
    o, recs = 0, []
    while o + HDR <= len(p) and p[o:o + 2] == MARKER:
        flag = p[o + 2]
        chk = struct.unpack_from("<I", p, o + 3)[0]
        vl, kid = struct.unpack_from("<HH", p, o + 7)
        kl = p[o + 11]
        end = o + HDR + kl + vl
        if end > len(p):
            raise ValueError(f"record at 0x{o:x} runs past end of partition")
        key = p[o + HDR:o + HDR + kl]
        val = p[o + HDR + kl:end]
        recs.append((o, flag, chk, kid, key, val))
        o = end
    return recs, o


def cmd_verify(path):
    p, _ = find_psmp(Path(path).read_bytes())
    recs, end = parse(p)
    bad = 0
    for o, flag, chk, kid, key, val in recs:
        want = record_check(key, val, kid)
        if want != chk:
            bad += 1
            print(f"  0x{o:04x} {key.decode(errors='replace')}: check {chk:08x}, expected {want:08x}")
    print(f"{len(recs)} records, log ends at 0x{end:x} of 0x{len(p):x}, {bad} bad check(s)")
    return 1 if bad else 0


def parse_value(spec: str) -> bytes:
    if spec.startswith("@"):
        return Path(spec[1:]).read_bytes()
    if spec.startswith(":"):
        return bytes.fromhex(spec[1:])
    return spec.encode()


def cmd_set(path, pairs, out):
    data = bytearray(Path(path).read_bytes())
    p, base = find_psmp(bytes(data))
    p = bytearray(p)
    recs, end = parse(p)
    if any(b != 0xFF for b in p[end:]):
        sys.exit(f"log end 0x{end:x} is not followed by erased (0xFF) flash")
    for pair in pairs:
        if "=" not in pair:
            sys.exit(f"expected key=value, got {pair!r}")
        name, spec = pair.split("=", 1)
        key, val = name.encode(), parse_value(spec)
        if not 0 < len(key) < 256 or len(val) > 0xFFFE:
            sys.exit(f"{name}: key or value length out of range")
        prev = [r for r in recs if r[4] == key and r[1] == LIVE]
        ids = {r[3] for r in recs}
        kid = prev[-1][3] if prev else (max(ids) + 1 if ids else 1)
        if kid >= MAX_KEY_ID:
            sys.exit(f"{name}: key id {kid} is past the firmware's limit")
        rec = bytearray(MARKER + bytes([LIVE]) + struct.pack("<IHHB", record_check(key, val, kid),
                                                             len(val), kid, len(key)))
        rec += key + val
        if end + len(rec) > len(p):
            sys.exit(f"{name}: no room left in the 0x{len(p):x}-byte partition (needs a format)")
        p[end:end + len(rec)] = rec
        for o, flag, chk, rkid, rkey, rval in prev:
            p[o + 2] = STALE
        recs, end = parse(p)
        print(f"  set {name} id={kid} {len(val)} byte(s) at 0x{end - len(rec):04x}")
    data[base:base + len(p)] = p
    Path(out).write_bytes(bytes(data))
    print(f"wrote {out} ({len(data)} bytes)")
    return 0


def cmd_list(path, show_all):
    p, _ = find_psmp(Path(path).read_bytes())
    recs, end = parse(p)
    print(f"{len(recs)} records, log ends at 0x{end:x} of 0x{len(p):x}")
    live = {}
    for o, flag, chk, kid, key, val in recs:
        if show_all:
            print(f"  0x{o:04x} {'live ' if flag == LIVE else 'stale'} id={kid:<3} chk={chk:08x} {key.decode(errors='replace'):<14} {val.hex()}")
        if flag == LIVE:
            live[key] = (kid, val)
    if not show_all:
        for key, (kid, val) in live.items():
            txt = val.decode() if all(32 <= b < 127 for b in val) and val else ""
            print(f"  id={kid:<3} {key.decode(errors='replace'):<14} {val.hex()}  {txt}")
    return 0

def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    if args[0] == "verify":
        if len(args) != 2:
            sys.exit(__doc__)
        return cmd_verify(args[1])
    if args[0] == "set":
        if "-o" not in args or len(args) < 4:
            sys.exit(__doc__)
        o = args.index("-o")
        return cmd_set(args[1], args[2:o], args[o + 1])
    return cmd_list(args[0], "--all" in args)

if __name__ == "__main__":
    sys.exit(main())
