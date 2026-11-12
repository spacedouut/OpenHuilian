#!/usr/bin/env python3
"""Offline motion rehost. Real FIRM + mask ROM; only OS/BT/I2C boundaries shimmed.

Run with cached dependencies:
uv run --offline --with unicorn==2.1.1 --with capstone==5.0.3 --with numpy \
    python tools/emu/headtrack.py --out /absolute/scratch/directory
"""
import argparse
import json
import math
import struct
import sys
from pathlib import Path

import numpy as np
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_MCLASS, UC_MODE_THUMB, Uc
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_S0,
    UC_ARM_REG_SP, UC_CPU_ARM_CORTEX_M4,
)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"tools/headtrack"))
from reference import Filter

IMAGE = ROOT / "firmware/h3promax3/h3promax3_2607061716_live.up"
ROM = ROOT / "firmware/h3promax3/rom/mask_rom_0x00000-0x5ffff.bin"
STACK, SENT, INPUT, OUTPUT = 0x870000, 0x7F000, 0x8F0000, 0x8F0100
POSE, REPORT, CTX = 0x833D1C, 0x836287, 0x82DB10


def fbits(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


def qmul(a, b):
    w, x, y, z = a
    W, X, Y, Z = b
    return np.array([w*W-x*X-y*Y-z*Z, w*X+x*W+y*Z-z*Y,
                     w*Y-x*Z+y*W+z*X, w*Z+x*Y-y*X+z*W])


def qconj(q):
    return q * [1, -1, -1, -1]


def qerror(a, b):
    a, b = np.asarray(a), np.asarray(b)
    dot = np.sum(a*b, axis=-1) / (np.linalg.norm(a, axis=-1)*np.linalg.norm(b, axis=-1))
    return np.degrees(2*np.arccos(np.clip(np.abs(dot), 0, 1)))


def qexp(rotation):
    v = np.asarray(rotation)
    angle = np.linalg.norm(v)
    return np.r_[math.cos(angle/2), v*(math.sin(angle/2)/angle if angle else .5)]


def qlog(q):
    q = np.asarray(q)/np.linalg.norm(q)
    if q[0] < 0:
        q = -q
    n = np.linalg.norm(q[1:])
    return q[1:]*(2*math.atan2(n, q[0])/n if n else 2)


def gravity(q):
    return qmul(qmul(qconj(q), [0, 0, 0, -1]), q)[1:]


def scenarios(name, rate=240):
    duration = 122 if name in ("still", "bias") else 22 if name.startswith("sine_") else 12
    rng = np.random.default_rng(377)
    q = np.array([1., 0, 0, 0])
    for i in range(round(duration*rate)):
        t = (i+1)/rate
        w = np.zeros(3)
        if name == "slow_yaw" and 2 < t <= 10:
            w[2] = 10
        elif name in ("fast_yaw", "nod", "roll"):
            axis = {"fast_yaw": 2, "nod": 1, "roll": 0}[name]
            w[axis] = 180 if 2 < t <= 2.5 else -180 if 5 < t <= 5.5 else 0
        elif name in ("wrap", "wrap_negative") and 2 < t <= 8:
            w[2] = -45 if name == "wrap_negative" else 45
        elif name == "gimbal":
            w[1] = 45 if 2 < t <= 4 else -45 if 8 < t <= 10 else 0
            w[2] = 60 if 4 < t <= 6 else 0
        elif name == "combined" and 2 < t <= 8:
            w = np.array([40*math.sin(2*t), 30*math.cos(1.7*t), 25.])
        elif name.startswith("sine_") and 2 < t <= 20:
            hz = float(name.split("_")[1])
            w[2] = 10*2*math.pi*hz*math.cos(2*math.pi*hz*(t-2))
        q = qmul(q, qexp(np.radians(w)/rate))
        q /= np.linalg.norm(q)
        a = gravity(q)
        measured = w + (np.array([.1, -.15, .3]) if name == "bias" else 0)
        if name == "noise":
            a += rng.normal(0, .02, 3)
            measured += rng.normal(0, .15, 3)
        yield t, q.copy(), measured, a


class Motion:
    """No full boot: same .data/hot-code load as the bootloader and motion task init."""

    def __init__(self, variant="stock", side=0, mode=None, image=None):
        flash = bytearray((Path(image) if image else IMAGE).read_bytes()[256:])
        if variant == "old" and image is None:
            for off, fmt, value in [(0xAB550, "<B", 20), (0x68A1A, "<B", 1),
                                    (0x68C74, "<f", 0.3)]:
                struct.pack_into(fmt, flash, off, value)
        if variant in ("v2", "lab") and image is None:
            name = "head-tracking-v2-lab.json" if variant == "lab" else "head-tracking-v2.json"
            patch = json.loads((ROOT/"patches/2607061716"/name).read_text())
            for op in patch["ops"]:
                offset = 0x4000+int(op["offset"], 0)
                blob = bytes.fromhex(op["new"])
                flash[offset:offset+len(blob)] = blob
        self.uc = uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        uc.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M4)
        uc.mem_map(0, 0x100000)
        uc.mem_write(0, ROM.read_bytes())
        uc.mem_map(0x800000, 0x100000)
        uc.mem_map(0xC00000, 0x100000)
        uc.mem_write(0xC00000, bytes(flash))
        firm = flash[0x4000:]
        uc.mem_write(0x804C40, bytes(firm[0x470:0x1470]))
        lo, hi = 0x805C40, 0x82CA2C
        uc.mem_write(lo, bytes(firm[lo-0x8009F8:hi-0x8009F8]))
        uc.mem_map(0xE000E000, 0x1000)
        uc.mem_write(0xE000ED88, struct.pack("<I", 0xF00000))
        self.side, self.time, self.heap = side, 0., 0x880000
        self.captures, self.fifo = [], []
        self.hooks = {}
        for addr, value in [(0x824B18, side), (0x824AF4, 1), (0xCA92D8, 1),
                            (0xCA7B60, 1), (0xC8B402, 0), (0xC9197C, 0),
                            (0xCA9160, 0), (0x80A868, 0), (0xCA90D0, 3),
                            (0xCA7B6C, 0)]:
            self.stub(addr, lambda *_, value=value: value)
        self.stub(0x827564, lambda r0, r1, r2, r3: side if r2 == 9 else 0)
        self.stub(0x82950E, self.calloc)
        self.stub(0x81CB44, self.connection)
        self.stub(0x80A864, lambda *_: round(self.time * 1000))
        self.stub(0x825934, lambda *_: int(self.time * 1e6) // 625)
        self.stub(0x825938, lambda *_: 0)
        self.stub(0x824ADC, lambda *_: int(self.time * 1e6) % 625)
        self.stub(0x825940, lambda *_: 0)
        self.stub(0xCA761C, self.capture)
        self.stub(0xC589AE, self.i2c)
        self.stub(0xC58A50, self.fifo_data)
        self.stub(0x80C308, lambda *_: 0)
        self.call(0xC68580, 0)
        cfg = self.read(0x82B7A4, "<4fB")
        self.call(0xC683A8, cfg[4] if mode is None else mode, floats=cfg[:4])
        self.call(0xC684D0, 0xC32130)
        self.call(0xCAA554)
        self.write(0x836326, "<B", 1)
        self.variant = variant
        if variant == "dt":
            self.write(CTX+12, "<f", 1e6/240)
        if variant == "no_bias":
            self.stub(0xC68284, self.python_bias)
        if variant == "python":
            self.filter = Filter()
            self.stub(0xC68284, self.python_bias)
            self.stub(0xC74F7C, self.python_fusion)

    def python_bias(self, accel, gyro, bias, *_):
        self.write(bias, "<3f", 0, 0, 0)

    def python_fusion(self, *_):
        f = [struct.unpack("<f", struct.pack("<I", self.uc.reg_read(UC_ARM_REG_S0+i)))[0]
             for i in range(6)]
        q = self.filter.update(f[:3], f[3:])
        for address, value in zip((0x82B89C, 0x82EC68, 0x82EC6C, 0x82EC70), q):
            self.write(address, "<f", value)
        self.write(0x833D68, "<H", 1)

    def stub(self, addr, fn):
        self.hooks[addr] = fn

        def hook(uc, _addr, _size, _):
            regs = [uc.reg_read(UC_ARM_REG_R0+i) for i in range(4)]
            value = fn(*regs)
            if value is not None:
                uc.reg_write(UC_ARM_REG_R0, int(value) & 0xFFFFFFFF)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        self.uc.hook_add(UC_HOOK_CODE, hook, begin=addr, end=addr)

    def calloc(self, n, size, *_):
        p = self.heap
        self.heap = (p+n*size+7) & ~7
        self.uc.mem_write(p, bytes(n*size))
        return p

    def connection(self, r0, r1, r2, r3):
        for p, v in [(r0, 0), (r1, 0), (r2, 2), (r3, 0)]:
            self.write(p, "<B", v)

    def capture(self, *_):
        p = self.read(0x833494, "<I")[0]
        self.captures.append(bytes(self.uc.mem_read(p, 0x60)))

    def i2c(self, reg, dest, count, *_):
        if reg == 0x1B:
            self.write(dest, "<H", len(self.fifo))
        elif reg == 0x78:
            self.write(dest, "<B", self.fifo[0][0] << 3)
        else:
            raise RuntimeError(f"unexpected I2C register {reg:#x}")

    def fifo_data(self, dest, *_):
        _, xyz = self.fifo.pop(0)
        self.write(dest, "<3h", *xyz)

    def read(self, addr, fmt):
        return struct.unpack(fmt, self.uc.mem_read(addr, struct.calcsize(fmt)))

    def write(self, addr, fmt, *values):
        self.uc.mem_write(addr, struct.pack(fmt, *values))

    def call(self, addr, *regs, floats=()):
        uc = self.uc
        uc.reg_write(UC_ARM_REG_SP, STACK)
        uc.reg_write(UC_ARM_REG_LR, SENT | 1)
        for i, x in enumerate(regs[:4]):
            uc.reg_write(UC_ARM_REG_R0+i, int(x))
        for i, x in enumerate(regs[4:]):
            self.write(STACK+4*i, "<I", int(x))
        for i, x in enumerate(floats):
            uc.reg_write(UC_ARM_REG_S0+i, fbits(x))
        try:
            uc.emu_start(addr | 1, SENT, count=500000)
        except Exception as exc:
            raise RuntimeError(f"{addr:#x} fault PC={uc.reg_read(UC_ARM_REG_PC):#x}: {exc}") from exc
        if uc.reg_read(UC_ARM_REG_PC) != SENT:
            raise RuntimeError(f"{addr:#x} failed to return PC={uc.reg_read(UC_ARM_REG_PC):#x}")
        return uc.reg_read(UC_ARM_REG_R0)

    def step(self, gyro, accel, through_fifo=False):
        """gyro dps, accel g in algorithm/body frame. FIFO includes driver's ZYX accel swap."""
        if through_fifo:
            # Datasheet 500 dps sensitivity .0175 dps/LSB, 2 g .061 mg/LSB.
            g = np.clip(np.rint(np.asarray(gyro)/.0175), -32767, 32767).astype(int)
            a = np.clip(np.rint(np.asarray(accel)[::-1]/.000061), -32767, 32767).astype(int)
            self.fifo = [(1, g), (2, a)]
            self.call(0xC58A5C, INPUT, INPUT+8, INPUT+16, INPUT+24, INPUT+32, INPUT+40, 1)
            gyro_raw = [self.read(INPUT+x, "<h")[0] for x in (24, 32, 40)]
            accel_raw = [self.read(INPUT+x, "<h")[0] for x in (0, 8, 16)]
        else:
            gyro_raw = np.clip(np.trunc(np.asarray(gyro)*32768/500), -32767, 32767).astype(int)
            accel_raw = np.clip(np.trunc(np.asarray(accel)*32768/2), -32767, 32767).astype(int)
        self.write(INPUT, "<6h", *gyro_raw, *accel_raw)
        self.call(0xC68924, INPUT, INPUT+6)
        return np.array(self.read(POSE, "<3h"))

    def fusion_q(self):
        return np.array([self.read(a, "<f")[0] for a in (0x82B89C, 0x82EC68, 0x82EC6C, 0x82EC70)])

    def report(self):
        self.write(0x8343D5, "<B", 1)
        self.call(0xCAAAB0)
        if not self.captures:
            raise RuntimeError("HID callback did not send")
        b = self.captures[-1]
        v = np.array(struct.unpack_from("<3h", b, 0x29))/32768
        q = np.array([-math.sqrt(max(0, 1-v@v)), v[1], v[0], v[2]])
        return q, np.array(struct.unpack_from("<3h", b, 0x2F)), b.hex()


def run_scenario(name, variant, out, rate=240, fifo=False):
    e = Motion(variant)
    period = .02 if variant in ("old", "v2", "lab", "python") else .04
    next_tx = period
    records = []
    for t, truth, gyro, accel in scenarios(name, rate):
        e.time = t
        pose = e.step(gyro, accel, through_fifo=fifo)
        fusion = e.fusion_q()
        if t+1e-9 < next_tx:
            continue
        next_tx += period
        q, vel, raw = e.report()
        records.append(dict(t=t, truth=truth.tolist(), fusion=fusion.tolist(),
                            pose=pose.tolist(), q=q.tolist(), velocity=vel.tolist(), raw=raw))
    ts = np.array([r["t"] for r in records])
    truth = np.array([r["truth"] for r in records])
    fused = np.array([r["fusion"] for r in records])
    err = qerror(truth, fused)
    active = ts >= 2
    vel = np.array([r["velocity"] for r in records])
    poses = np.array([r["pose"] for r in records])
    peak = 2.5 if name in ("fast_yaw", "nod", "roll") else 10 if name == "slow_yaw" else 8
    idx = np.argmin(abs(ts-peak))
    quiet = (ts>1)&(ts<2)
    result = dict(rate=rate, reports=len(records), fusion_rmse_deg=float(np.sqrt(np.mean(err[active]**2))),
                  fusion_max_deg=float(np.max(err[active])), fusion_final_deg=float(err[-1]),
                  fusion_peak_deg=float(qerror(truth[idx], fused[idx])),
                  stationary_velocity_rms_counts=float(np.sqrt(np.mean(vel[quiet]**2))),
                  stationary_velocity_max_counts=int(abs(vel[quiet]).max()),
                  pose_steps_deg=np.unique(np.abs(np.diff(poses, axis=0))).tolist()[:15])
    if name in ("slow_yaw", "fast_yaw", "wrap", "wrap_negative"):
        true_yaw = np.degrees(np.unwrap([qlog(q)[2] for q in truth]))
        fused_yaw = np.degrees(np.unwrap([qlog(q)[2] for q in fused]))
        result.update(truth_peak_yaw_deg=float(true_yaw[idx]), fused_peak_yaw_deg=float(fused_yaw[idx]),
                      fused_final_yaw_deg=float(fused_yaw[-1]))
        if name == "fast_yaw":
            result["overshoot_deg"] = float(max(fused_yaw[(ts>=2)&(ts<5)])-90)
            for label, ys in [("truth", true_yaw), ("fusion", fused_yaw)]:
                hits = ts[(ts>=2)&(ts<5)&(ys>=45)]
                result[label+"_half_time_s"] = float(hits[0]) if len(hits) else None
    if name.startswith("sine_"):
        hz = float(name.split("_")[1])
        use = (ts>6)&(ts<20)
        basis = np.c_[np.sin(2*np.pi*hz*ts[use]), np.cos(2*np.pi*hz*ts[use]), ts[use], np.ones(use.sum())]
        coeffs = []
        for qs in (truth, fused):
            ys = np.degrees(np.array([qlog(q)[2] for q in qs]))
            coeffs.append(np.linalg.lstsq(basis, ys[use], rcond=None)[0])
        a, b = coeffs
        phase = math.atan2(b[1], b[0])-math.atan2(a[1], a[0])
        phase = (phase+math.pi) % (2*math.pi)-math.pi
        result.update(sine_gain=float(np.linalg.norm(b[:2])/np.linalg.norm(a[:2])),
                      sine_phase_deg=math.degrees(phase),
                      equivalent_phase_delay_ms=-1000*phase/(2*math.pi*hz))
    (out/f"{name}-{variant}-{rate}.json").write_text(json.dumps(records, separators=(",", ":")))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--scenarios", nargs="+", default=["still", "slow_yaw", "fast_yaw", "nod",
                        "roll", "combined", "bias", "noise", "wrap", "gimbal"])
    parser.add_argument("--variants", nargs="+", default=["stock", "old"])
    parser.add_argument("--rate", type=int, default=240)
    parser.add_argument("--fifo", action="store_true")
    args = parser.parse_args()
    if not args.out.is_dir():
        parser.error("--out must be an existing scratch directory")
    if args.probe:
        e = Motion()
        print("startup", e.read(CTX, "<6fB"), "mapping", e.read(0x82C5A0, "<9b"))
        for i in range(20):
            e.time = (i+1)/240
            angles = e.step([0, 0, 0], [0, 0, -1], through_fifo=True)
        print("stationary", angles, e.fusion_q(), e.report())
        return
    metrics = args.out/f"metrics-{args.rate}.json"
    results = json.loads(metrics.read_text()) if metrics.exists() else {}
    for name in args.scenarios:
        for variant in args.variants:
            result = run_scenario(name, variant, args.out, args.rate, args.fifo)
            results[f"{name}/{variant}"] = result
            print(name, variant, json.dumps(result), flush=True)
            metrics.write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
