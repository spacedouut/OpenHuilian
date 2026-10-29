#!/usr/bin/env python3
"""Generic .up partition lister / extractor / FIRM strings dumper.

The missing generic tool from tools/README.md. Works on any CONFIG-wrapped .up or
raw HLKJ flash dump, any chip generation (SL6801, SL6806, 377H3, ...).

usage: upparts.py <image.up | flash.bin> [outdir] [--strings N]

With outdir: writes <tag>.bin for every stored partition plus index.txt (the parsed
index with CRC check results) and firm_strings.txt (printable ASCII runs >= N from FIRM).
Without outdir: just prints the index summary.
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from upfmt import BODY, MAGIC, crc16, index_offset, parse_index


def hlkj_fields(flash):
    """Best-effort decode of the HLKJ header at flash 0 (layout: docs/17)."""
    f = {}
    if flash[:4] != b"HLKJ":
        return f
    f["magic"] = "HLKJ"
    u32 = lambda o: struct.unpack_from("<I", flash, o)[0]
    u16 = lambda o: struct.unpack_from("<H", flash, o)[0]
    f["u32@04 (load addr?)"] = hex(u32(0x04))
    f["u32@08"] = hex(u32(0x08))
    f["u32@0C (hdr size?)"] = hex(u32(0x0C))
    f["u32@10 (len?)"] = hex(u32(0x10))
    f["u16@14 (crc16?)"] = hex(u16(0x14))
    f["u32@20 (index off)"] = hex(u32(0x20))
    boot_sp, boot_rst = struct.unpack_from("<II", flash, 0x60)
    f["boot vectors @60: SP"] = hex(boot_sp)
    f["boot vectors @60: reset"] = hex(boot_rst)
    return f


def strings(data, min_len=6):
    out = []
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % min_len, data):
        out.append((m.start(), m.group().decode("ascii")))
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
    min_len = 6
    if "--strings" in sys.argv:
        min_len = int(sys.argv[sys.argv.index("--strings") + 1])

    data = open(path, "rb").read()
    chip = ""
    if data[:6] == MAGIC:
        body_len = struct.unpack_from("<I", data, 0x10)[0]
        stored_crc = struct.unpack_from("<H", data, 0x14)[0]
        chip = data[0x16:0x26].split(b"\0")[0].decode("ascii", "replace")
        body = data[BODY:BODY + body_len]
        ok = crc16(body) == stored_crc
        print(f"container: CONFIG body={body_len} crc=0x{stored_crc:04X} {'OK' if ok else 'MISMATCH'} chip={chip!r}")
        flash = body
    else:
        flash = data
        print("container: raw flash dump (no CONFIG header)")

    for k, v in hlkj_fields(flash).items():
        print(f"  HLKJ {k}: {v}")

    idx_off = index_offset(flash)
    version, parts = parse_index(flash, idx_off)
    print(f"index @ flash 0x{idx_off:X}: count={len(parts)} version={version}")

    rows = []
    for tag, addr, length, crc in parts:
        tag = tag.decode("ascii", "replace")
        stored = crc & 0xFFFF
        blob = flash[addr:addr + length]
        ok = "OK" if blob and crc16(blob) == stored else ("n/a" if not blob else "MISMATCH")
        rows.append((tag, addr, length, stored, ok))
        print(f"  {tag:5s} addr=0x{addr:06X} len=0x{length:06X} crc=0x{stored:04X} {ok}")

    if not outdir:
        return
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "index.txt"), "w") as f:
        f.write(f"image: {os.path.basename(path)}\nchip: {chip}\nversion: {version}\n\n")
        f.write("tag   addr      len       crc     check\n")
        for tag, addr, length, stored, ok in rows:
            f.write(f"{tag:5s} 0x{addr:06X} 0x{length:06X} 0x{stored:04X} {ok}\n")
    for tag, addr, length, _, _ in rows:
        blob = flash[addr:addr + length]
        if blob:
            with open(os.path.join(outdir, f"{tag}.bin"), "wb") as f:
                f.write(blob)
    firm = next((flash[a:a + l] for t, a, l, _, _ in rows if t == "FIRM" and l), None)
    if firm:
        with open(os.path.join(outdir, "firm_strings.txt"), "w") as f:
            for off, s in strings(firm, min_len):
                f.write(f"0x{off:06X}\t{s}\n")
    print(f"extracted -> {outdir}")


if __name__ == "__main__":
    main()
