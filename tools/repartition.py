#!/usr/bin/env python3
"""Re-lay the movable partitions of a .up inside the free span between FIRM and OTAP.

Usage: repartition.py <in.up> <out.up> [--tone-len BYTES] [--firm-end ADDR] [TONE_NAME=file.mp3 ...]

Only the index, FIRM's length and SENC, TONE and EQ2P change. FIRM stays at 0x4000 (its code runs
from flash at fixed addresses). OTAP and PSMP keep their index records, since OTAP's erase range
and flag page are derived from them. FIRM finds SENC/TONE/EQ2P through the partition index (all
seven callers of the index lookup at 0x805444 name their partition), not by hardcoded flash
address. See docs/research/memory-map-and-boot.md; tools/emu/repart_check.py checks a layout in
the emulator.

Partitions are placed in stock order (SENC, TONE, EQ2P), each starting on a 4 KiB boundary, so the
default run reproduces the stock layout byte for byte. --tone-len grows or shrinks the declared TONE
length, and NAME=file swaps prompts (same rules as tone_tool.py replace). --firm-end grows the FIRM
partition so it ends at that flash address; the new bytes are zero, for code caves (cfw.py does this
for patches with a "layout" block). Partition CRCs, the index and the CONFIG CRC are recomputed. The
output must pass upfmt.ota_image_problems or nothing is written.

Nothing here touches a bud. Flashing a repartitioned image is untested on hardware.
"""
import struct
import sys
from pathlib import Path

from tone_tool import build_tone, read_dir
from upfmt import BODY, MAGIC, crc16, index_offset, ota_image_problems, parse_index

MOVABLE = [b"SENC", b"TONE", b"EQ2P"]
PAGE = 0x1000


def align(x):
    return (x + PAGE - 1) & ~(PAGE - 1)


def relayout(body, firm_end=None, blobs=None):
    """Grow FIRM to end at `firm_end` (optional) and pack SENC/TONE/EQ2P after it, in place.

    `blobs` replaces partition contents by tag. Rewrites the index records (address, length, CRC)
    of FIRM and the movable partitions. Returns {tag: [addr, len]}. Raises ValueError if the
    layout does not fit before OTAP or would shrink FIRM.
    """
    io = index_offset(body)
    _, entries = parse_index(body, io)
    parts = {tag: [addr, ln] for tag, addr, ln, _ in entries}
    for tag in MOVABLE + [b"FIRM", b"OTAP"]:
        if tag not in parts:
            raise ValueError(f"no {tag.decode()} partition in this image")
    otap = parts[b"OTAP"][0]
    firm_addr, firm_len = parts[b"FIRM"]
    new = {t: bytes(body[parts[t][0]:parts[t][0] + parts[t][1]]) for t in MOVABLE}
    new.update(blobs or {})
    if firm_end is not None:
        if firm_end & (PAGE - 1):
            raise ValueError(f"FIRM end 0x{firm_end:x} is not 4 KiB aligned")
        if firm_end - firm_addr < firm_len:
            raise ValueError(f"FIRM end 0x{firm_end:x} would cut FIRM (it ends at 0x{firm_addr + firm_len:x})")
        new_firm_len = firm_end - firm_addr
    else:
        new_firm_len = firm_len

    cur = align(firm_addr + new_firm_len)
    for tag in MOVABLE:
        parts[tag] = [cur, len(new[tag])]
        cur = align(cur + len(new[tag]))
    used_end = max(parts[t][0] + parts[t][1] for t in MOVABLE)
    if used_end > otap:
        raise ValueError(f"FIRM and SENC/TONE/EQ2P need up to 0x{used_end:x}, past OTAP at 0x{otap:x}")

    body[firm_addr + firm_len:otap] = bytes(otap - firm_addr - firm_len)
    for tag in MOVABLE:
        body[parts[tag][0]:parts[tag][0] + parts[tag][1]] = new[tag]
    parts[b"FIRM"][1] = new_firm_len
    for k, (tag, *_rest) in enumerate(entries):
        if tag in MOVABLE or tag == b"FIRM":
            addr, ln = parts[tag]
            struct.pack_into("<4sIII", body, io + 16 + 16 * k, tag, addr, ln, crc16(bytes(body[addr:addr + ln])))
    return parts


def main():
    args = sys.argv[1:]
    opts = {}
    for flag in ("--tone-len", "--firm-end"):
        if flag in args:
            i = args.index(flag)
            opts[flag] = int(args[i + 1], 0)
            del args[i:i + 2]
    if len(args) < 2:
        sys.exit(__doc__)
    src, out = args[0], args[1]
    swaps = dict(a.split("=", 1) for a in args[2:])
    tone_len = opts.get("--tone-len")

    data = Path(src).read_bytes()
    if data[:6] != MAGIC:
        sys.exit(f"{src}: not a CONFIG/.up container")
    body = bytearray(data[BODY:])
    _, entries = parse_index(body)
    before = {tag: (addr, ln) for tag, addr, ln, _ in entries}

    blobs = {}
    if swaps or tone_len:
        a, n = before[b"TONE"]
        tone = bytes(body[a:a + n])
        t_entries = read_dir(tone)
        names = [e[0] for e in t_entries]
        for nm in swaps:
            if nm not in names:
                sys.exit(f"'{nm}' is not in this TONE (have: {', '.join(names)})")
        prompts = [Path(swaps[nm]).read_bytes() if nm in swaps else tone[off:off + size]
                   for nm, size, off in t_entries]
        blobs[b"TONE"], _ = build_tone(t_entries, prompts, tone_len or len(tone))

    try:
        parts = relayout(body, opts.get("--firm-end"), blobs)
    except ValueError as e:
        sys.exit(f"{e}; shrink TONE or FIRM")

    hdr = bytearray(data[:BODY])
    struct.pack_into("<I", hdr, 0x10, len(body))
    struct.pack_into("<H", hdr, 0x14, crc16(body))
    result = bytes(hdr) + bytes(body)
    bad = ota_image_problems(result)
    if bad:
        sys.exit("refusing to write, layout fails the OTA check:\n  " + "\n  ".join(bad))

    for tag in [b"FIRM"] + MOVABLE:
        (a0, n0), (a1, n1) = before[tag], parts[tag]
        print(f"  {tag.decode()}: 0x{a0:06x} len 0x{n0:05x} -> 0x{a1:06x} len 0x{n1:05x}")
    used_end = max(parts[t][0] + parts[t][1] for t in MOVABLE)
    print(f"  free between last partition and OTAP: {before[b'OTAP'][0] - used_end:,} B")
    Path(out).write_bytes(result)
    print(f"wrote {out}: body {len(body):,} B, container crc 0x{crc16(body):04x}")


if __name__ == "__main__":
    main()
