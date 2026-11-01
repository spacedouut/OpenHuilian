#!/usr/bin/env python3
"""Run the rom-read stub in Unicorn and check both of its paths.

    pip install unicorn
    python3 patches/2607061716/rom-read-selftest.py

Checks that a bit31 address copies raw memory into the destination, and that a
normal address falls through to the stock flash read at 0x0080576c without
copying anything itself.
"""
import json
import os
import sys

from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_MCLASS, UC_MODE_THUMB, Uc
from unicorn.arm_const import (
    UC_ARM_REG_LR,
    UC_ARM_REG_R0,
    UC_ARM_REG_R1,
    UC_ARM_REG_R2,
    UC_ARM_REG_SP,
)

STUB_XIP = 0xC30032
FLASH_READ = 0x0080576C
SENTINEL = 0x00804000
PATCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rom-read.json")


def stub_bytes():
    with open(PATCH) as f:
        ops = json.load(f)["ops"]
    for op in ops:
        if int(op["offset"], 16) == 0x2C032:
            return bytes.fromhex(op["new"])
    raise SystemExit("no stub op in " + PATCH)


def main():
    stub = stub_bytes()
    mu = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
    for base, size in ((0x0, 0x100000), (0x800000, 0x100000), (0xC00000, 0x100000)):
        mu.mem_map(base, size)
    mu.mem_write(STUB_XIP, stub)
    mu.mem_write(FLASH_READ, b"\x70\x47")  # bx lr stands in for the stock reader
    mu.mem_write(SENTINEL, b"\x00\xbf")

    pattern = bytes(i & 0xFF for i in range(0x100))
    mu.mem_write(0x8000, pattern)

    hits = []
    mu.hook_add(
        UC_HOOK_CODE,
        lambda u, a, s, d: hits.append(a),
        begin=FLASH_READ,
        end=FLASH_READ + 2,
    )

    def call(dst, addr, length):
        hits.clear()
        mu.mem_write(dst, b"\x41" * length)
        mu.reg_write(UC_ARM_REG_R0, dst)
        mu.reg_write(UC_ARM_REG_R1, addr)
        mu.reg_write(UC_ARM_REG_R2, length)
        mu.reg_write(UC_ARM_REG_SP, 0x870000)
        mu.reg_write(UC_ARM_REG_LR, SENTINEL | 1)
        mu.emu_start(STUB_XIP | 1, SENTINEL, count=100000)

    fails = []

    call(0x820000, 0x80008000, 0x100)
    if bytes(mu.mem_read(0x820000, 0x100)) != pattern:
        fails.append("bit31 path did not copy the source bytes")
    if hits:
        fails.append("bit31 path fell through to the flash read")

    call(0x820000, 0x4000, 0x100)
    if not hits:
        fails.append("normal path never reached 0x%08x" % FLASH_READ)
    if bytes(mu.mem_read(0x820000, 0x10)) != b"\x41" * 0x10:
        fails.append("normal path copied bytes itself")

    for f in fails:
        print("FAIL: " + f)
    print("rom-read stub: " + ("ok" if not fails else "%d failure(s)" % len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
