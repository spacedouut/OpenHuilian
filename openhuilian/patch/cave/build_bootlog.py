#!/usr/bin/env python3
"""Build the boot milestone log and write patches/2607061716/boot-log.json.

    uv run --with ziglang==0.13.0 --with pyelftools python3 -m openhuilian.patch.cave.build_bootlog

Compiles bootlog.c the way build.py compiles the monitor, links it into the second half of the
monitor's cave page (bootlog.ld), and emits a cfw.py patch: the code, one op per `bl` in `task
main` (FUN_00c4de78) that redirects it to bl_hook, and the two I2C helper exits. The call table
the C code walks (bootlog_sites.h) is generated here from SITES, so the ops and the table cannot
disagree. The checked-in JSON is the build output.
"""
import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from elftools.elf.elffile import ELFFile

from openhuilian.patch.cave.build import CAVE as MON_CAVE, CAVE_LEN as MON_CAVE_LEN, CFLAGS, FIRM_XIP, FIRMWARE, b_w

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "patches/2607061716/boot-log.json"

CAVE, CAVE_LEN = MON_CAVE + 0x800, 0x800   # the monitor's code is under 0x800 bytes
RAM, RAM_LEN = 0x8787F0, 0x10              # just below the monitor's block
# Every bl in FUN_00c4de78 (`task main`), in order: (address of the bl, its stock target).
# The milestone id in the log is the 1-based position in this list.
SITES = [
    (0xC4DE7E, 0xC60554), (0xC4DE82, 0xC6E7A0), (0xC4DE86, 0xC53720), (0xC4DE8A, 0xC6AA8C),
    (0xC4DE8E, 0xC6A360), (0xC4DE92, 0xC4E654), (0xC4DE96, 0xC5A280), (0xC4DE9A, 0xC55880),
    (0xC4DE9E, 0xC54220), (0xC4DEA2, 0xC558DC), (0xC4DEA6, 0xC53480), (0xC4DEAA, 0xC508F4),
    (0xC4DEAE, 0xC52520), (0xC4DEB2, 0xC4EB1C), (0xC4DEB6, 0xC5251C), (0xC4DEBA, 0xC4EB30),
    (0xC4DEC0, 0xC5A298),
]
# Common exit of the I2C helpers: rsbs r0, r5, #0 ; pop.w {r3-r9, pc}
I2C_EXIT_OLD = "6842bde8f883"
I2C_EXITS = [(0xCA0682, "bl_i2c_w", "write helper FUN_00ca0624"),
             (0xCA06F0, "bl_i2c_r", "read helper FUN_00ca0694")]


def bl(src, dst):
    """Thumb-2 BL (T1) at src to dst: B.W with bit 14 of the second halfword set."""
    hw1, hw2 = struct.unpack("<HH", b_w(src, dst))
    return struct.pack("<HH", hw1, hw2 | 0x4000)


def main():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "bootlog_sites.h").write_text(
            "".join(f"{{0x{a + 4:08X}u, 0x{t | 1:08X}u}},\n" for a, t in SITES))
        elf = Path(tmp) / "bootlog.elf"
        cmd = [sys.executable, "-m", "ziglang", "cc", *CFLAGS, f"-I{tmp}", f"-Wl,-T,{HERE / 'bootlog.ld'}",
               "-Wl,--gc-sections", "-Wl,--entry=bl_hook", "-g", "-o", str(elf), str(HERE / "bootlog.c")]
        subprocess.run(cmd, check=True)
        with open(elf, "rb") as f:
            e = ELFFile(f)
            text = e.get_section_by_name(".text")
            code, base = text.data(), text["sh_addr"]
            bss = e.get_section_by_name(".bss")
            symtab = list(e.get_section_by_name(".symtab").iter_symbols())
    syms = {s.name: s["st_value"] for s in symtab}
    undef = [s.name for s in symtab if s["st_shndx"] == "SHN_UNDEF" and s.name]
    if undef:
        sys.exit(f"undefined symbols (cave code can only call FIRM/ROM through fixed addresses): {undef}")
    if base != CAVE or len(code) > CAVE_LEN or CAVE + CAVE_LEN > MON_CAVE + MON_CAVE_LEN:
        sys.exit(f".text at 0x{base:x}+0x{len(code):x} does not fit the cave 0x{CAVE:x}+0x{CAVE_LEN:x}")
    if not bss or bss["sh_addr"] != RAM or bss["sh_size"] > RAM_LEN:
        sys.exit(f".bss does not fit the reserved RAM 0x{RAM:x}+0x{RAM_LEN:x}")
    hook = syms["bl_hook"] & ~1
    ops = [{"offset": hex(CAVE - FIRM_XIP), "old": "00" * len(code), "new": code.hex(),
            "what": f"boot log code at XIP 0x{CAVE:x}, {len(code)} bytes: bl_hook 0x{hook:x}, "
                    f"state at 0x{RAM:x}"}]
    for i, (addr, target) in enumerate(SITES, 1):
        ops.append({"offset": hex(addr - FIRM_XIP), "old": bl(addr, target).hex(), "new": bl(addr, hook).hex(),
                    "what": f"task main 0x{addr:x}: bl FUN_{target:08x} -> bl bl_hook (milestone b{i:02x})"})
    for addr, sym, what in I2C_EXITS:
        ops.append({"offset": hex(addr - FIRM_XIP), "old": I2C_EXIT_OLD,
                    "new": (b_w(addr, syms[sym] & ~1) + b"\x00\xbf").hex(),
                    "what": f"I2C {what} exit 0x{addr:x}: rsbs r0, r5, #0 ; pop.w {{r3-r9, pc}} -> "
                            f"b.w {sym} 0x{syms[sym] & ~1:x} ; nop ({sym} replays both)"})
    patch = {
        "name": "Boot milestone log (task main init calls and I2C transfers, into the monitor log ring)",
        "firmware": FIRMWARE,
        "partition": "FIRM",
        "about": ("Apply together with debug-monitor.json. Logs one text line per init call of "
                  "`task main` (b01..b11) and one per I2C transfer made during init (address, "
                  "direction, status) into the debug monitor's RAM log ring; read it with `hl mon "
                  "log`. RAM only, no flash writes. Uses the second half of the monitor's cave page "
                  "and reserves 16 bytes of heap RAM. Source openhuilian/patch/cave/bootlog.c, built "
                  "by openhuilian/patch/cave/build_bootlog.py; checked in "
                  "openhuilian/emu/bootlog_check.py. See docs/research/boot-log.md."),
        "layout": {"firm_end": hex(MON_CAVE - 0xC00000 + MON_CAVE_LEN),
                   "ram": {"addr": hex(RAM), "len": hex(RAM_LEN)}},
        "ops": ops,
    }
    OUT.write_text(json.dumps(patch, indent=2) + "\n")
    print(f"code {len(code)} B at 0x{base:x}, bl_hook 0x{hook:x}, state 0x{RAM:x}+0x{bss['sh_size']:x}")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
