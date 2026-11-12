#!/usr/bin/env python3
"""Build offline experimental patches; outputs compiler artifacts only to --out.

Requires an existing arm-none-eabi GCC/binutils (no downloads). Never flashes.
Default patch fixes fusion, retaining stock HID frame/velocity logic.
The *-lab variant additionally bypasses that logic with UNCALIBRATED body-frame data.
"""
import argparse
import json
import os
import struct
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CAVE, RAM = 0xCB0000, 0x878400


def branch(src, dest):
    offset = dest-(src+4)
    if offset & 1 or not -(1<<24) <= offset < 1<<24:
        raise ValueError("BL range")
    s = (offset>>24)&1
    j1 = (~(offset>>23)^s)&1
    j2 = (~(offset>>22)^s)&1
    return struct.pack("<HH", 0xF000 | s<<10 | (offset>>12)&0x3FF,
                       0xD000 | j1<<13 | j2<<11 | (offset>>1)&0x7FF)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--cc", default=os.environ.get("CC", "arm-none-eabi-gcc"))
    a = p.parse_args()
    if not a.out.is_dir():
        p.error("--out must be an existing scratch directory")
    elf, binary = a.out/"filter.elf", a.out/"filter.bin"
    flags = ["-mcpu=cortex-m4", "-mthumb", "-mfpu=fpv4-sp-d16", "-mfloat-abi=hard",
             "-O2", "-ffreestanding", "-fno-builtin", "-fno-tree-loop-distribute-patterns",
             "-nostdlib", "-Wall", "-Wextra", "-Werror", "-g", f"-Wl,-T,{HERE/'filter.ld'}",
             "-Wl,--entry=ht_fusion", f"-Wl,-Map,{a.out/'filter.map'}"]
    subprocess.run([a.cc, *flags, str(HERE/"filter.c"), "-o", str(elf)], check=True)
    prefix = a.cc.rsplit("gcc", 1)[0]
    subprocess.run([prefix+"objcopy", "-O", "binary", "--only-section=.text", str(elf), str(binary)], check=True)
    nm = subprocess.check_output([prefix+"nm", "-S", "--defined-only", str(elf)], text=True)
    syms = {}
    for line in nm.splitlines():
        fields = line.split()
        if len(fields) == 4:
            syms[fields[3]] = int(fields[0], 16)
            if fields[3] == "S" and int(fields[1], 16)>0x300:
                raise ValueError("state exceeds RAM reservation")
    undefined = subprocess.check_output([prefix+"nm", "-u", str(elf)], text=True).strip()
    if undefined:
        raise ValueError(f"undefined symbols: {undefined}")
    code = binary.read_bytes()
    if len(code)>0x2000:
        raise ValueError("filter exceeds flash reservation")
    flash = (ROOT/"firmware/h3promax3/h3promax3_2607061716_live.up").read_bytes()[256:]

    def op(addr, new, what):
        old = flash[addr-0xC00000:addr-0xC00000+len(new)]
        return dict(offset=hex(addr-0xC04000), old=old.hex(), new=new.hex(), what=what)

    ops = [dict(offset=hex(CAVE-0xC04000), old="00"*len(code), new=code.hex(),
                what="Hard-float fusion and optional lab encoder; built from tools/headtrack/filter.c")]
    for site, name in [(0xC68F6C, "ht_bias"), (0xC68D12, "ht_fusion")]:
        ops.append(op(site, branch(site, syms[name]), name))
    ops.append(op(0xCAB550, bytes([20]), "20 ms transmit timer (stock 40 ms)"))
    common = dict(firmware=2607061716, partition="FIRM",
                  layout=dict(firm_end="0xb2000", ram=dict(addr=hex(RAM), len="0x300")),
                  settings=[])
    for lab in (False, True):
        patch = dict(common, name="EXPERIMENTAL head tracking v2"+(" UNCALIBRATED LAB" if lab else " fusion only"),
                     about=("OFFLINE VALIDATED ONLY. 240 Hz dt, stationary-gated bias, quaternion fusion. "
                            "Mode-0 hook only. " +
                            ("LAB: direct quaternion/body-rate payload; physical axes and wire velocity units unverified. DO NOT FLASH."
                             if lab else "Retains stock HID transforms, quantization and velocity artifacts. Hardware untested.")),
                     ops=ops+([op(0xCAB22C, branch(0xCAB22C, syms["ht_send"]), "LAB uncalibrated direct report")] if lab else []))
        dest = ROOT/"patches/2607061716"/("head-tracking-v2-lab.json" if lab else "head-tracking-v2.json")
        dest.write_text(json.dumps(patch, indent=2)+"\n")
    (a.out/"filter-symbols.json").write_text(json.dumps(syms, indent=2))
    print(nm, f"code={len(code)} bytes, cave={CAVE:#x}, RAM={RAM:#x}")


if __name__ == "__main__":
    main()
