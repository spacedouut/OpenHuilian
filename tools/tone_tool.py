#!/usr/bin/env python3
"""
TONE partition tool for Huilian/SmartLink .up firmware containers.

  list    <fw.up>                       show the TONE directory
  extract <fw.up> <outdir>              dump every prompt bit-exact
  replace <fw.up> <name=file.mp3> ... -o out.up
                                        swap one or more prompts and rebuild
                                        all CRCs (partition CRC16 + container)

Container recap (verified across 24 catalog images):
  file[0x00:0x06]  = b"CONFIG"
  file[0x14:0x16]  = CRC16/CCITT-FALSE over file[0x100:]
  body             = file[0x100:]
  index_off        = u32 @ body+0x20            (0x3000 in every image)
  index: u32 count, u32 version, then count * 16 bytes:
         tag[4], addr u32, length u32, crc16 u32
  payload of a partition lives at file[addr + 0x100]

TONE layout:
  [0x000 .. 0x400)  directory: repeated [u32 size][name NUL-terminated]
  [0x400 .. )       raw audio payloads, concatenated in directory order
"""
import struct
import sys
import os
from pathlib import Path

from upfmt import BODY, MAGIC, crc16, index_offset, parse_index

TONE_DATA_START = 0x400


def parse(data: bytes):
    assert data[:6] == MAGIC, "not a .up (missing CONFIG magic)"
    body = data[BODY:]
    index_off = index_offset(body)
    version, entries = parse_index(body, index_off)
    parts = [{"tag": tag.decode("latin1"), "addr": addr, "length": length, "crc": crc,
              "index_entry": BODY + index_off + 16 * k}
             for k, (tag, addr, length, crc) in enumerate(entries, 1)]
    return {"version": version, "index_off": index_off, "partitions": parts}


def get_part(info, tag):
    for p in info["partitions"]:
        if p["tag"] == tag:
            return p
    raise SystemExit(f"no {tag} partition in this image")


def read_dir(tone: bytes):
    """Parse the TONE directory into [(name, size, data_offset)]."""
    entries = []
    pos = 0
    data_off = TONE_DATA_START
    while pos < TONE_DATA_START - 4:
        size = struct.unpack_from("<I", tone, pos)[0]
        if size == 0 or size == 0xFFFFFFFF:
            break
        end = tone.index(b"\0", pos + 4)
        name = tone[pos + 4:end].decode("latin1")
        if not name:
            break
        entries.append((name, size, data_off))
        data_off += size
        pos = end + 1
    return entries


def build_tone(entries, blobs, total_len):
    """Rebuild a TONE partition from [(name, data)] preserving declared length."""
    directory = b""
    for name, blob in zip([e[0] for e in entries], blobs):
        directory += struct.pack("<I", len(blob)) + name.encode("latin1") + b"\0"
    if len(directory) > TONE_DATA_START:
        raise SystemExit(f"directory too big: {len(directory)} > {TONE_DATA_START}")
    out = directory + b"\0" * (TONE_DATA_START - len(directory)) + b"".join(blobs)
    if len(out) > total_len:
        raise SystemExit(
            f"TONE would be {len(out)} B but partition only declares {total_len} B "
            f"(over by {len(out) - total_len}); shrink the audio")
    return out + b"\0" * (total_len - len(out)), len(out)


def load_tone(path):
    data = Path(path).read_bytes()
    info = parse(data)
    p = get_part(info, "TONE")
    return data, info, p, data[p["addr"] + BODY: p["addr"] + BODY + p["length"]]


def cmd_list(path):
    _, info, p, tone = load_tone(path)
    entries = read_dir(tone)
    print(f"{path}  version={info['version']}")
    print(f"TONE @ 0x{p['addr']:06x} len={p['length']} crc=0x{p['crc']:04x} "
          f"(recomputed 0x{crc16(tone):04x})")
    used = TONE_DATA_START
    for name, size, off in entries:
        print(f"  {name:<22} {size:>8} B  @0x{off:05x}")
        used += size
    print(f"  {len(entries)} files, {used} / {p['length']} B used")


def cmd_extract(path, outdir):
    _, _, p, tone = load_tone(path)
    os.makedirs(outdir, exist_ok=True)
    root = os.path.realpath(outdir)
    for name, size, off in read_dir(tone):
        dest = os.path.realpath(os.path.join(root, name))
        if os.path.commonpath([root, dest]) != root:
            sys.exit(f"refusing to write outside {outdir}: {name!r}")
        with open(dest, "wb") as fh:
            fh.write(tone[off:off + size])
        print(f"  wrote {name} ({size} B)")


def cmd_replace(path, swaps, outpath):
    data, _, p, tone = load_tone(path)
    data = bytearray(data)
    start = p["addr"] + BODY
    entries = read_dir(tone)
    names = [e[0] for e in entries]

    blobs = []
    for name, size, off in entries:
        if name in swaps:
            blob = Path(swaps[name]).read_bytes()
            print(f"  {name}: {size} B -> {len(blob)} B  ({swaps[name]})")
        else:
            blob = tone[off:off + size]
        blobs.append(blob)
    for name in swaps:
        if name not in names:
            raise SystemExit(f"'{name}' is not in this TONE (have: {', '.join(names)})")

    new_tone, used = build_tone(entries, blobs, p["length"])
    data[start:start + p["length"]] = new_tone

    # partition CRC16 in the index entry
    new_crc = crc16(new_tone)
    struct.pack_into("<I", data, p["index_entry"] + 12, new_crc)
    print(f"  TONE crc 0x{p['crc']:04x} -> 0x{new_crc:04x}   ({used}/{p['length']} B used)")

    # outer container checksum over body
    outer = crc16(data[BODY:])
    old_outer = struct.unpack_from("<H", data, 0x14)[0]
    struct.pack_into("<H", data, 0x14, outer)
    print(f"  container crc 0x{old_outer:04x} -> 0x{outer:04x}")

    Path(outpath).write_bytes(data)
    print(f"  wrote {outpath} ({len(data)} B)")


def cmd_verify(path):
    """Independently re-validate every CRC in an image."""
    data = Path(path).read_bytes()
    info = parse(data)
    ok = True
    outer = struct.unpack_from("<H", data, 0x14)[0]
    calc = crc16(data[BODY:])
    print(f"container: stored 0x{outer:04x} calc 0x{calc:04x} "
          f"{'OK' if outer == calc else 'MISMATCH'}")
    ok &= outer == calc
    for p in info["partitions"]:
        s, e = p["addr"] + BODY, p["addr"] + BODY + p["length"]
        if e > len(data):
            print(f"{p['tag']}: not stored in file (runtime region), skipped")
            continue
        c = crc16(data[s:e])
        good = c == p["crc"]
        ok &= good
        print(f"{p['tag']}: stored 0x{p['crc']:04x} calc 0x{c:04x} "
              f"{'OK' if good else 'MISMATCH'}")
    print("ALL CRCs VALID" if ok else "VALIDATION FAILED")
    return ok


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    cmd = sys.argv[1]
    if cmd == "list":
        cmd_list(sys.argv[2])
    elif cmd == "extract":
        cmd_extract(sys.argv[2], sys.argv[3])
    elif cmd == "verify":
        raise SystemExit(0 if cmd_verify(sys.argv[2]) else 1)
    elif cmd == "replace":
        args = sys.argv[3:]
        out = args[args.index("-o") + 1]
        swaps = dict(a.split("=", 1) for a in args[:args.index("-o")])
        cmd_replace(sys.argv[2], swaps, out)
    else:
        print(__doc__)
        raise SystemExit(1)
