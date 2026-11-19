#!/usr/bin/env python3
"""Build the debug monitor and write patches/2607061716/debug-monitor.json.

    uv run --with ziglang==0.13.0 --with pyelftools python3 tools/cave/build.py

Compiles monitor.c with zig's clang for Cortex-M4 Thumb, links it at the cave address
(monitor.ld), and emits a cfw.py patch: a "layout" block that grows FIRM and reserves the RAM,
the code as one op over the zeroed cave, and the hook that turns the first instruction of the C0
handler FUN_00c69b3c into a b.w to mon_entry. The checked-in JSON is the build output, so
applying the patch needs neither zig nor this script.
"""
import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from elftools.elf.elffile import ELFFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = ROOT / "patches/2607061716/debug-monitor.json"

FIRMWARE = 2607061716
FIRM_XIP = 0xC04000                      # FIRM partition offset 0 in the XIP window
CAVE, CAVE_LEN = 0xCAE000, 0x1000        # flash 0xAE000, the first page after stock FIRM
RAM, RAM_LEN = 0x878800, 0x400           # below the 2 KiB stack and a 1 KiB guard gap
HOOK, HOOK_OLD = 0xC69B3C, "2de9f041"    # FUN_00c69b3c: push.w {r4-r8, lr}
CFLAGS = ["-target", "thumb-freestanding-eabi", "-mcpu=cortex_m4", "-Os", "-ffreestanding",
          "-fno-builtin", "-fno-pic", "-ffunction-sections", "-nostdlib", "-Wall", "-Werror"]


def b_w(src, dst):
    """Thumb-2 B.W (T4) at src to dst."""
    off = dst - (src + 4)
    if off & 1 or not -(1 << 24) <= off < 1 << 24:
        raise ValueError("branch out of range")
    s = (off >> 24) & 1
    j1 = (~(off >> 23) ^ s) & 1
    j2 = (~(off >> 22) ^ s) & 1
    hw1 = 0xF000 | s << 10 | (off >> 12) & 0x3FF
    hw2 = 0x9000 | j1 << 13 | j2 << 11 | (off >> 1) & 0x7FF
    return struct.pack("<HH", hw1, hw2)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        elf = Path(tmp) / "monitor.elf"
        cmd = [sys.executable, "-m", "ziglang", "cc", *CFLAGS, f"-Wl,-T,{HERE / 'monitor.ld'}",
               "-Wl,--gc-sections", "-Wl,--entry=mon_entry", "-g", "-o", str(elf), str(HERE / "monitor.c")]
        subprocess.run(cmd, check=True)
        with open(elf, "rb") as f:
            e = ELFFile(f)
            text = e.get_section_by_name(".text")
            code, base = text.data(), text["sh_addr"]
            bss = e.get_section_by_name(".bss")
            syms = {s.name: s["st_value"] for s in e.get_section_by_name(".symtab").iter_symbols()}
            undef = [s.name for s in e.get_section_by_name(".symtab").iter_symbols()
                     if s["st_shndx"] == "SHN_UNDEF" and s.name]
    if undef:
        sys.exit(f"undefined symbols (cave code can only call FIRM/ROM through fixed addresses): {undef}")
    if base != CAVE or len(code) > CAVE_LEN:
        sys.exit(f".text at 0x{base:x}+0x{len(code):x} does not fit the cave 0x{CAVE:x}+0x{CAVE_LEN:x}")
    if bss and bss["sh_size"] > RAM_LEN:
        sys.exit(f".bss is 0x{bss['sh_size']:x} bytes, reserved 0x{RAM_LEN:x}")
    entry = syms["mon_entry"] & ~1
    hook = b_w(HOOK, entry)
    patch = {
        "name": "Debug monitor (C0 D0-D4: info, peek, poke, call, log)",
        "firmware": FIRMWARE,
        "partition": "FIRM",
        "about": ("Adds C0 D0 info, D1 peek, D2 poke, D3 call and D4 log ring to the SPP command "
                  "channel, in new code after the end of stock FIRM. Poke and call answer only after "
                  "the C0 01/02 handshake (hl auth). Use with `hl mon`. Grows FIRM by one page "
                  "(SENC/TONE/EQ2P move up 4 KiB) and reserves 1 KiB of heap RAM. Source "
                  "tools/cave/monitor.c, built by tools/cave/build.py; checked in "
                  "tools/emu/monitor_check.py. See docs/research/debug-monitor.md."),
        "layout": {"firm_end": hex(CAVE - 0xC00000 + CAVE_LEN),
                   "ram": {"addr": hex(RAM), "len": hex(RAM_LEN)}},
        "ops": [
            {"offset": hex(CAVE - FIRM_XIP), "old": "00" * len(code), "new": code.hex(),
             "what": f"monitor code at XIP 0x{CAVE:x}, {len(code)} bytes: header, mon_entry "
                     f"0x{entry:x}, mon_log 0x{syms['mon_log'] & ~1:x}, state at 0x{syms['M']:x}"},
            {"offset": hex(HOOK - FIRM_XIP), "old": HOOK_OLD, "new": hook.hex(),
             "what": f"C0 handler FUN_00c69b3c entry: push.w {{r4-r8,lr}} -> b.w mon_entry 0x{entry:x} "
                     "(mon_entry replays the push for non-Dx frames)"},
        ],
    }
    OUT.write_text(json.dumps(patch, indent=2) + "\n")
    print(f"code {len(code)} B at 0x{base:x}, mon_entry 0x{entry:x}, mon_log 0x{syms['mon_log']:x}, "
          f"state 0x{syms['M']:x}+0x{bss['sh_size'] if bss else 0:x}")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
