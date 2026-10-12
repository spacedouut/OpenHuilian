#!/usr/bin/env python3
"""List the records of a Smartlink PSMP (NV key/value) partition.

Usage:
  psmp_tool.py <flash_dump.bin | psmp.bin> [--all]

Accepts either a bare PSMP blob or a raw HLKJ flash dump (PSMP is located via the
partition table pointer at HLKJ+0x20).  Prints live records by default; --all also
shows superseded (flag 0xFE) records in log order.

Record layout (derived from the OpenPod SL6801 dump, see docs/09-psmp-nvds.md):
  55 AA | flag (FF live / FE stale) | u32 check (algorithm unknown) |
  u16 value_len | u16 key_id | u8 key_len | key | value
Read-only: the 4-byte check is not yet reproduced, so this tool does not rebuild PSMP.
"""
import struct, sys
from pathlib import Path

from upfmt import parse_index

def find_psmp(data):
    if data[:4] != b"HLKJ":
        return data
    for tag, addr, ln, _ in parse_index(data)[1]:
        if tag == b"PSMP":
            return data[addr:addr + ln]
    sys.exit("no PSMP partition in table")

def parse(p):
    o, recs = 0, []
    while o + 12 <= len(p) and p[o:o + 2] == b"\x55\xaa":
        flag = p[o + 2]
        chk = struct.unpack_from("<I", p, o + 3)[0]
        vl, kid = struct.unpack_from("<HH", p, o + 7)
        kl = p[o + 11]
        end = o + 12 + kl + vl
        if end > len(p):
            raise ValueError(f"record at 0x{o:x} runs past end of partition")
        key = p[o + 12:o + 12 + kl]
        val = p[o + 12 + kl:end]
        recs.append((o, flag, chk, kid, key, val))
        o = end
    return recs, o

def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    data = Path(sys.argv[1]).read_bytes()
    p = find_psmp(data)
    recs, end = parse(p)
    show_all = "--all" in sys.argv
    print(f"{len(recs)} records, log ends at 0x{end:x} of 0x{len(p):x}")
    live = {}
    for o, flag, chk, kid, key, val in recs:
        if show_all:
            print(f"  0x{o:04x} {'live ' if flag == 0xff else 'stale'} id={kid:<3} chk={chk:08x} {key.decode(errors='replace'):<14} {val.hex()}")
        if flag == 0xff:
            live[key] = (kid, val)
    if not show_all:
        for key, (kid, val) in live.items():
            txt = val.decode() if all(32 <= b < 127 for b in val) and val else ""
            print(f"  id={kid:<3} {key.decode(errors='replace'):<14} {val.hex()}  {txt}")

if __name__ == "__main__":
    main()
