#!/usr/bin/env python3
"""Wrap the H3Pro Max3 FIRM / OTAP / bootloader in ARM ELFs so Ghidra & co. load them at the
right addresses. Offline only, standard library only. Layout is from docs/17.

usage: h3pro_elf.py <h3promax3.up | raw flash dump> [outdir]
writes firm.elf, otap.elf, boot.elf
"""
import os
import struct
import sys
from pathlib import Path

PT_LOAD, R, W, X = 1, 4, 2, 1


def crc16(data, crc=0xFFFF):
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
            crc &= 0xFFFF
    return crc


def write_elf(path, segs, entry):
    """segs: list of (vaddr, data, memsz, flags)."""
    phoff = 52
    off = phoff + 32 * len(segs)
    ph, blob = b"", b""
    for vaddr, data, memsz, flags in segs:
        ph += struct.pack("<8I", PT_LOAD, off + len(blob), vaddr, vaddr, len(data),
                          max(memsz, len(data)), flags, 4)
        blob += data + b"\0" * (-len(data) % 4)
    ident = b"\x7fELF\x01\x01\x01" + b"\0" * 9
    # ET_EXEC, EM_ARM, EABI v5 + hard-float flags, no section headers
    hdr = ident + struct.pack("<HHIIIIIHHHHHH", 2, 40, 1, entry, phoff, 0, 0x05000400,
                              52, 32, len(segs), 0, 0, 0)
    with open(path, "wb") as fh:
        fh.write(hdr + ph + blob)
    print(f"{path}: entry {entry:#x}, " +
          ", ".join(f"{v:#x}+{max(m, len(d)):#x}" for v, d, m, _ in segs))


def partitions(flash):
    idx = struct.unpack_from("<I", flash, 0x20)[0]
    count = struct.unpack_from("<I", flash, idx)[0]
    parts = {}
    for i in range(count):
        tag, addr, length, crc = struct.unpack_from("<4sIII", flash, idx + 16 + 16 * i)
        parts[tag.decode()] = (addr, length, crc & 0xFFFF)
    return parts


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    data = Path(sys.argv[1]).read_bytes()
    out = sys.argv[2] if len(sys.argv) > 2 else "."
    flash = data[0x100:] if data[:6] == b"CONFIG" else data
    if flash[:4] != b"HLKJ":
        sys.exit("no HLKJ header at flash 0")
    parts = partitions(flash)

    for name in ("FIRM", "OTAP"):
        addr, length, crc = parts[name]
        if crc16(flash[addr:addr + length]) != crc:
            sys.exit(f"{name} CRC mismatch, refusing")

    # FIRM: 0x30-byte header, then a 4 KiB block the bootloader copies to RAM 0x804C40,
    # a .data image the startup code copies to 0x805C40, and the whole thing XIP at 0xC00000+addr.
    addr, length, _ = parts["FIRM"]
    firm = flash[addr:addr + length]
    load, entry, blk = struct.unpack_from("<III", firm, 0x10)
    stack = struct.unpack_from("<I", firm, 0x30)[0]
    data_lo, data_hi, delta = 0x805C40, 0x82CA2C, 0x8009F8
    write_elf(os.path.join(out, "firm.elf"), [
        (load, firm[0x470:0x470 + blk], blk, R | X),
        (data_lo, firm[data_lo - delta:data_hi - delta], stack - data_lo, R | W | X),
        (0xC00000 + addr, firm, length, R | X),
    ], entry)

    # OTAP: a single RAM-linked program, OTAP[0x30:] runs at 0x804800.
    addr, length, _ = parts["OTAP"]
    otap = flash[addr:addr + length]
    stack = struct.unpack_from("<I", otap, 0x30)[0]
    entry = struct.unpack_from("<I", otap, 0x14)[0]
    write_elf(os.path.join(out, "otap.elf"),
              [(0x804800, otap[0x30:], stack - 0x804800, R | W | X)], entry)

    # Bootloader: HLKJ header at flash 0 describes it (load, entry, header size, length, crc).
    # Its own vector table sits at the start of the body (SP, reset).
    load, _, hsize, blen, bcrc = struct.unpack_from("<IIIII", flash, 4)
    body = flash[hsize:hsize + blen]
    if crc16(body) != bcrc & 0xFFFF:
        sys.exit("bootloader CRC mismatch, refusing")
    stack, entry = struct.unpack_from("<II", body, 0)
    write_elf(os.path.join(out, "boot.elf"), [(load, body, stack - load, R | W | X)], entry)


if __name__ == "__main__":
    main()
