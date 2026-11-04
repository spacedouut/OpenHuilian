#!/usr/bin/env python3
"""Run FIRM's voice-path noise suppressor (FUN_00c780a4) in Unicorn on test signals.

    pip install unicorn numpy
    python3 tools/emu/voice_ns.py <h3promax3.up> [more.up ...]

Builds the module the way FUN_00c64860 does (FUN_00c77bdc + FUN_00c782d8(0xA900) from the
config block at FIRM 0xC33D9C, 16 kHz, 256-sample frames), then feeds frames through
FUN_00c78228. Everything is FIRM code except these, which are stood in for in Python: the mask-ROM
malloc, memcpy/memmove/memset, expf and forward/inverse real FFT (numpy rfft/irfft, so
absolute FFT scaling is ours, not the ROM's), and FIRM's cosf/sinf wrappers
(FUN_00814b6c/FUN_00814bac, which fall into unread ROM). Offline only.
"""
import struct
import sys
from pathlib import Path

import numpy as np
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_MCLASS, UC_MODE_THUMB, Uc
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
                               UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_S0, UC_ARM_REG_SP,
                               UC_CPU_ARM_CORTEX_M4)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from upfmt import parse_index  # noqa: E402

RATE, FRAME = 16000, 256
CFG_BLOCK = 0xC33D9C
DATA_LO, DATA_HI, DELTA = 0x805C40, 0x82CA2C, 0x8009F8
HEAP, SCRATCH, STACK, SENT = 0x880000, 0x8F0000, 0x870000, 0x7F000
CREATE, SETPARAM, PROCESS = 0xC77BDC, 0xC782D8, 0xC78228


def f2u(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


def u2f(x):
    return struct.unpack("<f", struct.pack("<I", x & 0xFFFFFFFF))[0]


class NS:
    def __init__(self, image):
        data = Path(image).read_bytes()
        flash = data[0x100:] if data[:6] == b"CONFIG" else data
        parts = {t.decode(): (a, n) for t, a, n, _ in parse_index(flash)[1]}
        a, n = parts["FIRM"]
        firm = flash[a:a + n]
        self.base = 0xC00000 + a
        self.flags = struct.unpack_from("<H", firm, CFG_BLOCK + 2 - self.base)[0]
        uc = self.uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        uc.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M4)
        uc.mem_map(0, 0x100000)
        uc.mem_write(0, b"\x70\x47" * 0x80000)
        uc.mem_map(0x800000, 0x100000)
        uc.mem_map(0xC00000, 0x100000)
        uc.mem_write(0xC00000, flash[:0x100000])
        load, _, blk = struct.unpack_from("<III", firm, 0x10)
        uc.mem_write(load, firm[0x470:0x470 + blk])
        uc.mem_write(DATA_LO, firm[DATA_LO - DELTA:DATA_HI - DELTA])
        uc.mem_map(0xE000E000, 0x1000)
        uc.mem_write(0xE000ED88, struct.pack("<I", 0x00F00000))  # CPACR: FPU on
        self.heap = HEAP
        self.unknown = {}
        uc.hook_add(UC_HOOK_CODE, self.rom, begin=0, end=0xFFFFF)
        for addr, fn in ((0x814B6C, np.cos), (0x814BAC, np.sin)):
            uc.hook_add(UC_HOOK_CODE, self.math(fn), begin=addr, end=addr)

    def math(self, fn):
        def hook(uc, addr, size, _):
            x = u2f(self.r(UC_ARM_REG_S0))
            uc.reg_write(UC_ARM_REG_S0, f2u(float(np.float32(fn(np.float32(x))))))
            uc.reg_write(UC_ARM_REG_PC, self.r(UC_ARM_REG_LR))
        return hook

    def r(self, reg):
        return self.uc.reg_read(reg)

    def rom(self, uc, addr, size, _):
        r0, r1, r2 = self.r(UC_ARM_REG_R0), self.r(UC_ARM_REG_R1), self.r(UC_ARM_REG_R2)
        if addr in (0x4B29C, 0x11044, 0xC70):                       # malloc
            p, self.heap = self.heap, (self.heap + r0 + 7) & ~7
            uc.mem_write(p, b"\0" * r0)
            uc.reg_write(UC_ARM_REG_R0, p)
        elif addr in (0xB2A, 0xC1E):                                 # memcpy / memmove
            if r2:
                uc.mem_write(r0, bytes(uc.mem_read(r1, r2)))
        elif addr == 0xBAA:                                          # memset
            if r2:
                uc.mem_write(r0, bytes([r1 & 0xFF]) * r2)
        elif addr == 0x48268:                                        # expf(s0)
            x = u2f(self.r(UC_ARM_REG_S0))
            uc.reg_write(UC_ARM_REG_S0, f2u(float(np.exp(np.float32(min(x, 88.0))))))
        elif addr == 0x4919A:                                        # rfft in place
            n = self.n
            x = np.frombuffer(bytes(uc.mem_read(r0, 4 * n)), "<f4")
            X = np.fft.rfft(x.astype(np.float64))
            out = np.empty(n + 2, "<f4")
            out[0::2], out[1::2] = X.real, X.imag
            uc.mem_write(r0, out.tobytes())
        elif addr == 0x48FAC:                                        # irfft in place
            n = self.n
            v = np.frombuffer(bytes(uc.mem_read(r0, 4 * (n + 2))), "<f4").astype(np.float64)
            x = np.fft.irfft(v[0::2] + 1j * v[1::2], n).astype("<f4")
            uc.mem_write(r0, x.tobytes())
        elif addr != 0:
            self.unknown[addr] = self.unknown.get(addr, 0) + 1

    def call(self, fn, *args):
        uc = self.uc
        for i, v in enumerate(args):
            uc.reg_write(UC_ARM_REG_R0 + i, v)
        uc.reg_write(UC_ARM_REG_SP, STACK)
        uc.reg_write(UC_ARM_REG_LR, SENT | 1)
        uc.emu_start(fn | 1, SENT, count=50_000_000)
        if self.r(UC_ARM_REG_PC) != SENT:
            raise SystemExit(f"call {fn:#x} did not return (pc={self.r(UC_ARM_REG_PC):#x})")
        return self.r(UC_ARM_REG_R0)

    def setup(self):
        uc = self.uc
        blk = bytes(uc.mem_read(CFG_BLOCK, 0x40))
        create = struct.pack("<HHH", RATE, FRAME, struct.unpack_from("<H", blk, 0)[0])
        uc.mem_write(SCRATCH, create.ljust(16, b"\0"))
        self.mod = self.call(CREATE, SCRATCH)
        if not self.mod:
            raise SystemExit("FUN_00c77bdc returned NULL")
        self.n = struct.unpack("<H", uc.mem_read(self.mod + 4, 2))[0]
        # FUN_00c64860 builds this from the block (cfg offset <- block offset)
        cfg = bytearray(0x40)
        cfg[0:2] = blk[2:4]
        cfg[2] = blk[4]
        for dst, src in ((0x04, 0x2C), (0x08, 0x08), (0x0C, 0x0C), (0x10, 0x10), (0x14, 0x14),
                         (0x18, 0x18), (0x1C, 0x24), (0x20, 0x38), (0x24, 0x3C), (0x28, 0x1C),
                         (0x2C, 0x20), (0x30, 0x28), (0x34, 0x30), (0x38, 0x34)):
            cfg[dst:dst + 4] = blk[src:src + 4]
        uc.mem_write(SCRATCH + 0x100, bytes(cfg))
        self.call(SETPARAM, self.mod, 0xA900, SCRATCH + 0x100)
        self.buf = SCRATCH + 0x1000
        for _ in range(2):
            uc.mem_write(self.buf, b"\0" * FRAME * 2)
            self.call(PROCESS, self.mod, self.buf, self.buf)
        self.call(SETPARAM, self.mod, 0xA903, 0)

    def run(self, pcm):
        out = np.zeros_like(pcm)
        for i in range(0, len(pcm) - FRAME + 1, FRAME):
            self.uc.mem_write(self.buf, pcm[i:i + FRAME].astype("<i2").tobytes())
            self.call(PROCESS, self.mod, self.buf, self.buf)
            out[i:i + FRAME] = np.frombuffer(bytes(self.uc.mem_read(self.buf, FRAME * 2)), "<i2")
        return out


def dbfs(x):
    rms = np.sqrt(np.mean(np.square(x.astype(np.float64)))) if len(x) else 0.0
    return 20 * np.log10(max(rms, 1e-3) / 32768)


def signals(seconds=3):
    rng = np.random.default_rng(1)
    t = np.arange(RATE * seconds) / RATE
    gate = (np.floor(t / 0.25) % 2 == 0)                        # 250 ms on / off
    tone = 32768 * 10 ** (-40 / 20) * np.sqrt(2) * np.sin(2 * np.pi * 1000 * t) * gate
    hiss = rng.normal(0, 32768 * 10 ** (-70 / 20), len(t))
    return {
        "digital silence": (np.zeros(len(t)), None),
        "-60 dBFS white noise": (rng.normal(0, 32768 * 10 ** (-60 / 20), len(t)), None),
        "-40 dBFS 1 kHz bursts + -70 dBFS hiss": (tone + hiss, gate),
    }


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sig = signals()
    for image in sys.argv[1:]:
        print(f"{image}")
        for name, (x, gate) in sig.items():
            ns = NS(image)
            ns.setup()
            pcm = np.clip(np.round(x), -32768, 32767).astype(np.int16)
            y = ns.run(pcm).astype(np.float64)
            skip = RATE                                          # let the noise estimate settle
            line = f"  flags={ns.flags}  {name:40s} in {dbfs(pcm[skip:]):7.1f}  out {dbfs(y[skip:]):7.1f} dBFS"
            if gate is not None:
                ref = pcm.astype(np.float64) * gate
                lag = max(range(0, 4 * FRAME), key=lambda k: float(np.dot(y[k:k + RATE], ref[:RATE])))
                g = np.concatenate([np.ones(lag, bool), gate[:len(gate) - lag]])
                margin = int(0.04 * RATE)
                quiet = np.convolve((~g.astype(bool)).astype(int), np.ones(2 * margin + 1), "same") == 2 * margin + 1
                quiet_in = np.convolve((~gate.astype(bool)).astype(int), np.ones(2 * margin + 1), "same") == 2 * margin + 1
                line += (f"   | gaps: in {dbfs(pcm[skip:][quiet_in[skip:]]):7.1f}"
                         f"  out {dbfs(y[skip:][quiet[skip:]]):7.1f}  (latency {lag} samples)")
            print(line)
            if ns.unknown:
                print("    unhandled ROM calls:", {hex(k): v for k, v in ns.unknown.items()})


if __name__ == "__main__":
    main()
