#!/usr/bin/env python3
"""Run the A2DP music path from decoder output to the mixer's output ring, and measure it.

    pip install unicorn numpy pyelftools
    python3 tools/h3pro_elf.py firmware/h3promax3/h3promax3_2607061716_live.up /some/dir
    python3 tools/emu/a2dp_path.py firmware/h3promax3/rom/mask_rom_0x00000-0x5ffff.bin /some/dir/firm.elf

The SBC decoder hands over int16 (ROM synthesis at 0x1A0F4 rounds, saturates, strh; the A2DP
context keeps bytes/sample at ctx+0x180 = 2 for SBC). This feeds int16 PCM through the code the
firmware runs for a type-2 (A2DP) stream, all in Unicorn:

  ROM  0x128A    converter 2 ch int16 -> 1 ch int32, (L<<15)+(R<<15) (FUN_00c70784 key 0x04010202)
  ROM  0x13B4    converter 1 ch int16 -> 1 ch int32, x<<16 (key 0x04010201), with --mono
  FIRM 0x8124D0  mixer accumulate, int32 qadd
  FIRM 0x812084  mixer master ramp apply on mixer+0x68, 64 frames per call (mixer task),
                 set up with ROM 0xBA0C(1.0, ramp, 48000, 1, 4) and 0xBA48(target)

It compares the int32 the mixer writes to its output ring with an ideal float multiply, then
shows what the same samples would keep if a later stage cut them to 24 or 16 bits (>> 8 / >> 16,
truncating). Offline only.
"""
import argparse
import struct
from pathlib import Path

import numpy as np
from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_MODE_MCLASS, UC_MODE_THUMB, Uc
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_S0,
                               UC_ARM_REG_SP, UC_CPU_ARM_CORTEX_M4)

CONV2CH, CONV16_32, MIX32, RAMP_APPLY = 0x128A, 0x13B4, 0x8124D0, 0x812084
RAMP_INIT, RAMP_TARGET = 0xBA0C, 0xBA48
RAMP, SRC, ACC, STACK, SENT = 0x8A0000, 0x8A1000, 0x8A2000, 0x8F0000, 0x7F000
BLOCK = 64                                    # mixer task block, frames (FUN_0080ce36)
CURVE = [(100, 0), (50, -15), (25, -26), (10, -32), (5, -35)]


def f2u(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


class Path_:
    def __init__(self, rom, elf, mono=False):
        self.mono = mono
        uc = self.uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        uc.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M4)
        uc.mem_map(0, 0x100000)
        uc.mem_write(0, rom)
        uc.mem_map(0x800000, 0x100000)
        uc.mem_map(0xC00000, 0x100000)
        for s in ELFFile(open(elf, "rb")).iter_segments():
            uc.mem_write(s["p_vaddr"], s.data())
        uc.mem_map(0xE000E000, 0x1000)
        uc.mem_write(0xE000ED88, struct.pack("<I", 0x00F00000))   # CPACR: FPU on
        self.call(RAMP_INIT, [RAMP, 48000, 1, 4], 1.0)

    def call(self, fn, regs, s0=None):
        uc = self.uc
        for i, v in enumerate(regs):
            uc.reg_write(UC_ARM_REG_R0 + i, v)
        if s0 is not None:
            uc.reg_write(UC_ARM_REG_S0, f2u(s0))
        uc.reg_write(UC_ARM_REG_SP, STACK)
        uc.reg_write(UC_ARM_REG_LR, SENT | 1)
        uc.emu_start(fn | 1, SENT, count=5_000_000)
        assert uc.reg_read(UC_ARM_REG_PC) == SENT

    def run(self, gain, x16):
        """x16: int16 decoder output (both channels when stereo). Returns the int32 block the mixer hands its sink."""
        self.call(RAMP_TARGET, [RAMP], gain)
        out = np.empty(len(x16), np.int64)
        for i in range(0, len(x16), BLOCK):
            blk = x16[i:i + BLOCK]
            n = len(blk)
            if self.mono:
                self.uc.mem_write(SRC + 0x400, blk.astype("<i2").tobytes())
                self.call(CONV16_32, [SRC, SRC + 0x400, n])
            else:                                                  # L = R = blk
                self.uc.mem_write(SRC + 0x400, np.repeat(blk, 2).astype("<i2").tobytes())
                self.call(CONV2CH, [SRC, SRC + 0x400, n])
            self.uc.mem_write(ACC, bytes(4 * n))
            self.call(MIX32, [ACC, SRC, n])
            self.call(RAMP_APPLY, [RAMP, ACC, n])
            out[i:i + n] = np.frombuffer(bytes(self.uc.mem_read(ACC, 4 * n)), "<i4")
        return out


def db(x):
    return 20 * np.log10(max(x, 1e-12))


def snr(y, ideal):
    err = np.sqrt(np.mean((y - ideal) ** 2))
    return f"{db(np.sqrt(np.mean(ideal ** 2)) / err):6.1f} dB" if err else "   exact"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("rom")
    ap.add_argument("firm_elf")
    ap.add_argument("--mono", action="store_true", help="1-channel stream (converter 0x13B4)")
    a = ap.parse_args()
    rom = Path(a.rom).read_bytes()
    fs = 48000
    t = np.arange(fs) / fs
    x16 = np.round(10 ** (-40 / 20) * np.sin(2 * np.pi * 1000 * t) * 32767).astype(np.int64)

    print(f"A2DP path, 48 kHz, {'mono' if a.mono else 'stereo'} int16 decoder output, -40 dBFS 1 kHz sine")
    print("SNR vs an ideal float gain on the int16 input; zeroed = share of nonzero-ideal samples output as 0")
    print(f"{'vol %':>5} {'dB':>6} | {'mixer out (int32)':>22} | {'cut to 24-bit':>22} | {'cut to 16-bit':>22}")
    for pct, gdb in CURVE:
        g = 10 ** (gdb / 20)
        p = Path_(rom, a.firm_elf, a.mono)
        for _ in range(40):                                        # let the ramp snap to target
            p.run(g, x16[: fs // 10])
            if abs(struct.unpack("<f", p.uc.mem_read(RAMP, 4))[0] - g) < 1e-6:
                break
        y = p.run(g, x16).astype(np.float64)
        ideal = x16 * 65536.0 * g
        cells = []
        for shift in (0, 8, 16):
            yq = np.floor(y / 2 ** shift) * 2 ** shift if shift else y   # asr: floor
            zeros = np.mean((yq == 0) & (np.abs(ideal) >= 2 ** shift / 2))
            cells.append(f"{snr(yq, ideal)}, {100 * zeros:4.1f}% zeroed")
        print(f"{pct:>5} {gdb:>6} | " + " | ".join(f"{c:>22}" for c in cells))


if __name__ == "__main__":
    main()
