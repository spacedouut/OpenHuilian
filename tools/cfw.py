#!/usr/bin/env python3
"""Apply OpenHuilian patch files to your own firmware dump and write a flashable .up.

Usage:
  cfw.py info  <in.up>
  cfw.py apply <in.up> <out.up> <patch.json>... [--set name=value]... [--chip NAME]

Works on the .up the StarFun app (or tools/flashdump.py) pulls off the buds. Every patch
file names the firmware version it was written for and the bytes it expects to find, so a
patch for another build is refused instead of applied. After patching, the partition CRCs,
the 0x30-byte FIRM/OTAP header CRC and the CONFIG container CRC are recomputed.

Patch file (JSON):
  {
    "name": "...", "firmware": 2607061716, "partition": "FIRM",
    "ops":      [{"offset": "0xa7550", "old": "2820", "new": "1420", "what": "..."}],
    "settings": [{"name": "tx_ms", "offset": "0xa7551", "type": "u8", "stock": 40,
                  "default": 20, "min": 10, "max": 100, "what": "..."}]
  }
Offsets are relative to the start of the partition. `ops` are always applied, `settings`
are applied with their default unless overridden with --set name=value.
Types: u8, u16, u32 (little endian), f32, bytes (hex string).

Nothing here talks to the buds. Flash the result with the app's local-file path or
tools/flashota.py, and read docs/19-cfw-patching.md first.
"""
import json
import struct
import sys
from pathlib import Path

from upfmt import BODY, MAGIC, crc16, index_offset, parse_index

TYPES = {"u8": "<B", "u16": "<H", "u32": "<I", "f32": "<f"}


def load(path):
    data = Path(path).read_bytes()
    if data[:6] != MAGIC:
        sys.exit(f"{path}: not a CONFIG/.up container")
    flash = bytearray(data[BODY:])
    length, crc = struct.unpack_from("<IH", data, 0x10)
    if length != len(flash) or crc16(flash) != crc:
        sys.exit(f"{path}: CONFIG header length/CRC does not match the body, refusing a damaged dump")
    ver, parts = parse_index(flash)
    return data[:BODY], flash, ver, parts


def in_part(patch, pname, plen, off, n, where):
    if off < 0 or off + n > plen:
        sys.exit(f"{patch['name']}: {where} at {pname}+{off:#x} ({n} bytes) is outside the partition")


def part_table(parts):
    return {tag.decode("ascii", "replace"): (addr, ln, crc) for tag, addr, ln, crc in parts}


def check_crcs(flash, parts, strict=True):
    ok = True
    for tag, addr, ln, crc in parts:
        name = tag.decode("ascii", "replace")
        if name == "PSMP" and crc == 0:
            continue
        if crc16(flash[addr:addr + ln]) != crc:
            ok = False
            print(f"  {name}: stored CRC 0x{crc:04x} does not match")
    if strict and not ok:
        sys.exit("partition CRCs do not verify, refusing to patch this image")
    return ok


def encode(typ, value, stock=None):
    if typ == "bytes":
        return bytes.fromhex(value)
    if typ not in TYPES:
        sys.exit(f"unknown setting type {typ}")
    if isinstance(value, str):
        value = float(value) if typ == "f32" else int(value, 0)
    return struct.pack(TYPES[typ], value)


def decode(typ, raw):
    if typ == "bytes":
        return raw.hex()
    return struct.unpack(TYPES[typ], raw)[0]


def apply_patch(flash, ver, parts, patch, overrides):
    fw = int(patch["firmware"])
    if fw != ver:
        sys.exit(f"{patch['name']}: written for firmware {fw}, this image is {ver}")
    table = part_table(parts)
    pname = patch["partition"]
    if pname not in table:
        sys.exit(f"{patch['name']}: partition {pname} not in this image")
    base, plen, _ = table[pname]
    changed = 0
    for op in patch.get("ops", []):
        off = int(op["offset"], 0)
        old, new = bytes.fromhex(op["old"]), bytes.fromhex(op["new"])
        if len(old) != len(new):
            sys.exit(f"{patch['name']}: op at {op['offset']} changes length")
        in_part(patch, pname, plen, off, len(old), "op")
        cur = bytes(flash[base + off:base + off + len(old)])
        if cur == new:
            print(f"  = {op.get('what', op['offset'])} (already applied)")
            continue
        if cur != old:
            sys.exit(f"{patch['name']}: at {pname}+{op['offset']} expected {old.hex()} found {cur.hex()}")
        flash[base + off:base + off + len(new)] = new
        changed += 1
        print(f"  + {op.get('what', op['offset'])}: {old.hex()} -> {new.hex()}")
    for st in patch.get("settings", []):
        typ = st["type"]
        off = int(st["offset"], 0)
        stock = encode(typ, st["stock"])
        value = overrides.get(st["name"], st["default"])
        if typ != "bytes":
            v = float(value) if typ == "f32" else int(str(value), 0)
            if "min" in st and v < st["min"] or "max" in st and v > st["max"]:
                sys.exit(f"{st['name']}={value} outside {st.get('min')}..{st.get('max')}")
            value = v
        new = encode(typ, value)
        if len(new) != len(stock):
            sys.exit(f"{patch['name']}: setting {st['name']} value is {len(new)} bytes, stock is {len(stock)}")
        in_part(patch, pname, plen, off, len(stock), f"setting {st['name']}")
        cur = bytes(flash[base + off:base + off + len(stock)])
        if cur != stock and cur != new:
            sys.exit(f"{patch['name']}: setting {st['name']} at {pname}+{st['offset']} expected "
                     f"{stock.hex()} found {cur.hex()}")
        if cur != new:
            flash[base + off:base + off + len(new)] = new
            changed += 1
        print(f"  * {st['name']} = {value} ({st.get('what', '')})")
    return changed


def fix_crcs(flash, parts):
    idx = index_offset(flash)
    for i, (tag, addr, ln, crc) in enumerate(parts):
        name = tag.decode("ascii", "replace")
        if name == "PSMP" and crc == 0:
            continue
        if name in ("FIRM", "OTAP") and flash[addr] == 0x30:
            blk = struct.unpack_from("<I", flash, addr + 0x18)[0]
            struct.pack_into("<H", flash, addr + 0x1C, crc16(flash[addr + 0x30:addr + 0x30 + blk]))
        struct.pack_into("<H", flash, idx + 16 + 16 * i + 12, crc16(flash[addr:addr + ln]))


def write_up(out, hdr, flash, chip=None):
    hdr = bytearray(hdr)
    struct.pack_into("<I", hdr, 0x10, len(flash))
    struct.pack_into("<H", hdr, 0x14, crc16(flash))
    if chip:
        name = chip.encode()
        if len(name) > 0xFE - 0x16:
            sys.exit("chip name does not fit in the CONFIG header")
        hdr[0x16:0xFE] = name + b"\0" * (0xFE - 0x16 - len(name))
    Path(out).write_bytes(bytes(hdr) + bytes(flash))


def main():
    args = sys.argv[1:]
    if not args or args[0] not in ("info", "apply"):
        sys.exit(__doc__)
    if args[0] == "info":
        hdr, flash, ver, parts = load(args[1])
        chip = hdr[0x16:0xFE].split(b"\0")[0].decode(errors="replace")
        print(f"firmware {ver}  chip {chip!r}  body {len(flash):,} bytes")
        for tag, addr, ln, crc in parts:
            print(f"  {tag.decode(errors='replace')} addr 0x{addr:06x} len {ln:>8,} crc 0x{crc:04x}")
        print("CRCs ok" if check_crcs(flash, parts, strict=False) else "CRCs BAD")
        return
    overrides, chip, files = {}, None, []
    it = iter(args[3:])
    for a in it:
        if a == "--set":
            k, _, v = next(it).partition("=")
            overrides[k] = v
        elif a == "--chip":
            chip = next(it)
        else:
            files.append(a)
    if not files:
        sys.exit("no patch files given")
    hdr, flash, ver, parts = load(args[1])
    print(f"firmware {ver}")
    check_crcs(flash, parts)
    total = 0
    for f in files:
        patch = json.loads(Path(f).read_text())
        print(f"{patch['name']} ({f})")
        total += apply_patch(flash, ver, parts, patch, overrides)
    fix_crcs(flash, parts)
    ver2, parts2 = parse_index(flash)
    check_crcs(flash, parts2)
    write_up(args[2], hdr, flash, chip)
    print(f"wrote {args[2]}: {total} change(s), CRCs fixed")


if __name__ == "__main__":
    main()
