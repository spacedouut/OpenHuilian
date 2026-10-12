#!/usr/bin/env python3
"""Rebuild a CONFIG/.up container from a raw flash dump + its partition index.

Usage: build_up.py [--force] <flash.bin> <out.up> [chip_name] [index_flash_addr_hex]

Refuses to write an image whose stored partition CRCs do not verify unless --force is given.

Layout (from catalog images + Shenju flasher source):
  file = 256-byte outer header + body, body[k] == flash[k]
  outer: "CONFIG" @0, u32 0x100 @6, u32 body_len @0x10, u16 crc16 @0x14,
         chip name @0x16, 55 AA @0xFE
  body+0x20 = u32 offset of partition index (normally 0x3000)
"""
import struct
import sys
from pathlib import Path

from upfmt import crc16, index_offset, parse_index


def main():
    args = sys.argv[1:]
    force = "--force" in args
    args = [a for a in args if a != "--force"]
    flash = Path(args[0]).read_bytes()
    out = args[1]
    chip = args[2] if len(args) > 2 else None
    idx_off = int(args[3], 16) if len(args) > 3 else index_offset(flash)

    ver, parts = parse_index(flash, idx_off)
    print(f"index @0x{idx_off:x}  version={ver}  ({ver:#x})")
    ok = True
    end = 0
    for tag, addr, ln, crc in parts:
        tag = tag.decode("ascii", "replace")
        blob = flash[addr:addr + ln]
        c = crc16(blob)
        stored = tag == "PSMP" and crc == 0
        status = "declared-only" if stored else ("OK" if c == crc else f"MISMATCH calc=0x{c:04x}")
        if not stored and c != crc:
            ok = False
        print(f"  {tag} addr 0x{addr:08x} len 0x{ln:08x} ({ln:>9,}) crc 0x{crc:04x}  {status}")
        if tag != "PSMP":
            end = max(end, addr + ln)
    print("all stored partition CRCs valid" if ok else "SOME CRCs INVALID")
    if not ok and not force:
        raise SystemExit(f"refusing to build {out} from a dump with invalid partition CRCs (use --force to override)")

    body = flash[:end]
    hdr = bytearray(0x100)
    hdr[0:6] = b"CONFIG"
    struct.pack_into("<I", hdr, 6, 0x100)
    struct.pack_into("<I", hdr, 0x10, len(body))
    struct.pack_into("<H", hdr, 0x14, crc16(body))
    if chip:
        chip_bytes = chip.encode()
        if len(chip_bytes) > 0xFE - 0x16:
            raise SystemExit("chip name does not fit in the CONFIG header")
        hdr[0x16:0x16 + len(chip_bytes)] = chip_bytes
    hdr[0xFE:0x100] = b"\x55\xaa"
    with open(out, "wb") as fh:
        fh.write(bytes(hdr) + body)
    print(f"wrote {out}: body {len(body):,} bytes, container crc 0x{crc16(body):04x}, chip={chip!r}")


if __name__ == "__main__":
    main()
