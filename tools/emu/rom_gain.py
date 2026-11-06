#!/usr/bin/env python3
"""Run the mask-ROM volume gain stage on test signals and measure what it does to quiet audio.

    pip install unicorn numpy
    python3 tools/emu/rom_gain.py <rom.bin (0x0-0x5FFFF)> [--bps 2|4] [--rate 48000]

The music volume from FIRM (engine message 0x1A, FUN_00810d24 case 0xC) lands in a ROM gain
ramp: 0xBA0C init(s0=gain, r0=ramp, r1=rate, r2=channels, r3=bytes/sample), 0xBA48
set target(s0, r0=ramp), 0xBA50 apply(r0=ramp, r1=pcm, r2=frames). This calls those three
ROM routines in Unicorn on the A2DP volume curve (docs/research/low-volume-noise.md) and compares the output with an
ideal float multiply ("round" = the best any undithered integer output could do). Offline only.
"""
import argparse
import struct
from pathlib import Path

import numpy as np
from unicorn import UC_ARCH_ARM, UC_MODE_MCLASS, UC_MODE_THUMB, Uc
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_S0,
                               UC_ARM_REG_SP, UC_CPU_ARM_CORTEX_M4)

INIT, TARGET, APPLY = 0xBA0C, 0xBA48, 0xBA50
RAMP, PCM, STACK, SENT = 0x800000, 0x810000, 0x870000, 0x7F000
CURVE = [(100, 0), (90, -2), (85, -4), (80, -6), (75, -8), (65, -10), (60, -11), (55, -13),
         (50, -15), (40, -17), (35, -20.5), (30, -23), (25, -26), (15, -29), (10, -32), (5, -35)]


def f2u(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


class Gain:
    def __init__(self, rom, rate, ch, bps):
        uc = self.uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        uc.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M4)
        uc.mem_map(0, 0x100000)
        uc.mem_write(0, rom)
        uc.mem_map(0x800000, 0x100000)
        uc.mem_map(0xE000E000, 0x1000)
        uc.mem_write(0xE000ED88, struct.pack("<I", 0x00F00000))
        self.ch, self.bps = ch, bps
        self.call(INIT, [RAMP, rate, ch, bps], 1.0)

    def call(self, fn, regs, s0=None):
        uc = self.uc
        for i, v in enumerate(regs):
            uc.reg_write(UC_ARM_REG_R0 + i, v)
        if s0 is not None:
            uc.reg_write(UC_ARM_REG_S0, f2u(s0))
        uc.reg_write(UC_ARM_REG_SP, STACK)
        uc.reg_write(UC_ARM_REG_LR, SENT | 1)
        uc.emu_start(fn | 1, SENT, count=20_000_000)
        assert uc.reg_read(UC_ARM_REG_PC) == SENT

    def apply(self, gain, x, block=128):
        """x: int array (frames*ch,), interleaved. Returns the ROM's output."""
        self.call(TARGET, [RAMP], gain)
        fmt = "<i2" if self.bps == 2 else "<i4"
        out = np.empty_like(x)
        step = block * self.ch
        for i in range(0, len(x), step):
            blk = x[i:i + step]
            self.uc.mem_write(PCM, blk.astype(fmt).tobytes())
            self.call(APPLY, [RAMP, PCM, len(blk) // self.ch])
            out[i:i + step] = np.frombuffer(bytes(self.uc.mem_read(PCM, len(blk) * self.bps)), fmt)
        return out


def db(x):
    return 20 * np.log10(max(x, 1e-12))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("rom")
    ap.add_argument("--rate", type=int, default=48000)
    ap.add_argument("--bps", type=int, default=2, choices=[2, 4])
    a = ap.parse_args()
    rom = Path(a.rom).read_bytes()
    fs, n = a.rate, a.rate * 2
    t = np.arange(n) / fs
    full = 32767 if a.bps == 2 else 2 ** 31 - 1
    tests = {
        "1 kHz sine, -20 dBFS": 10 ** (-20 / 20) * np.sin(2 * np.pi * 1000 * t),
        "1 kHz sine, -40 dBFS (quiet passage)": 10 ** (-40 / 20) * np.sin(2 * np.pi * 1000 * t),
    }
    print(f"ROM gain stage, {a.rate} Hz, {a.bps * 8}-bit PCM, stereo; error = ROM output - ideal float")
    print(f"{'vol %':>5} {'dB':>6} | " + " | ".join(f"{k:>40}" for k in tests))
    for pct, gdb in CURVE:
        g = 10 ** (gdb / 20)
        cells = []
        for name, sig in tests.items():
            x = np.round(sig * full).astype(np.int64)
            st = np.repeat(x, 2)
            dev = Gain(rom, a.rate, 2, a.bps)
            for _ in range(40):                                    # ramp tau ~83 ms; wait for the snap
                dev.apply(g, st[: 2 * fs // 10])
                cur = struct.unpack("<f", dev.uc.mem_read(RAMP, 4))[0]
                if abs(cur - g) < 1e-6:
                    break
            y = dev.apply(g, st)[0::2].astype(np.float64)
            ideal = x * g
            sig_rms = np.sqrt(np.mean(ideal ** 2))
            err = y - ideal
            err_rms = np.sqrt(np.mean(err ** 2))
            best = np.sqrt(np.mean((np.round(ideal) - ideal) ** 2))
            zeros = np.mean((y == 0) & (np.abs(ideal) >= 0.5))
            cells.append(f"SNR {db(sig_rms / err_rms):5.1f} (round {db(sig_rms / best):5.1f}) dB, "
                         f"{100 * zeros:4.1f}% zeroed")
        print(f"{pct:>5} {gdb:>6} | " + " | ".join(f"{c:>40}" for c in cells))


if __name__ == "__main__":
    main()
