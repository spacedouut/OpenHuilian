#!/usr/bin/env python3
"""Boot the stock image with the boot milestone log patch on the hardware model. Offline only.

    pip install unicorn
    OPENHUILIAN_MASK_ROM=... python3 -m openhuilian.emu.bootlog_check "$OPENHUILIAN_STOCK_UP"

Applies patches/2607061716/debug-monitor.json and boot-log.json with cfw.py into a temporary
directory, powers the result on with openhuilian.emu.machine + chip (mask ROM, BOOT, FIRM) and
runs it until the idle task sleeps, next to a stock boot. Then reads the monitor's log ring back
the way `hl mon log` does, through the real C0 handler (D4 for the ring state, D1 to peek it),
and prints it. Checks: the patched image reaches idle like stock; its flash writes and I2C bus
traffic are the same as stock's, so the patch adds none; the log holds every `task main` init
milestone in order and the three NACKed transfers to I2C address 0x60 that the bus model saw;
boot-log.json without the monitor still boots and logs nothing.
"""
import argparse
import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R12,
                               UC_ARM_REG_SP, UC_ARM_REG_XPSR)

from openhuilian.emu import chip
from openhuilian.emu.boot_check import boot, check
from openhuilian.format.upfmt import BODY
from openhuilian.inputs import mask_rom, stock_up

ROOT = Path(__file__).resolve().parents[2]
MONITOR = ROOT / "patches/2607061716/debug-monitor.json"
BOOTLOG = ROOT / "patches/2607061716/boot-log.json"
HANDLER, REPLY = 0xC69B3C, 0xC69870      # C0 handler, C0 reply post
MON_RAM, MON_LOG = 0x878800, 0x878810    # monitor state: magic, head, wraps, calls, then the ring
MON_MAGIC = 0x4C4D4C48
SENT, STACK, FRAME = 0x7F000, 0x8F8000, 0x8FA000   # return sentinel in ROM, scratch stack and frame
PROBE_ADDR, PROBE_TRIES = 0x60, 3
SAVED = [*range(UC_ARM_REG_R0, UC_ARM_REG_R12 + 1), UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_XPSR]


class Slave:
    """An I2C device that acknowledges everything; keeps each byte it was sent or asked for, with
    the number of the transfer (START) it came in."""
    def __init__(self, bus):
        self.bus, self.seen = bus, []

    def write(self, byte):
        self.seen.append((len(self.bus.log), "w", byte))

    def read(self):
        self.seen.append((len(self.bus.log), "r", 0x5A))
        return 0x5A


def patched(image, tmp, *patches):
    out = Path(tmp) / "patched.up"
    subprocess.run([sys.executable, "-m", "openhuilian.patch.cfw", "apply", str(image), str(out), *map(str, patches)],
                   check=True, stdout=subprocess.DEVNULL)
    return out.read_bytes()[BODY:]


def c0(m, frame):
    """Hand one C0 frame to FIRM's C0 handler on the sleeping machine; returns the replies it posts."""
    uc, replies = m.uc, []

    def on_reply(uc, addr, size, _):
        replies.append(bytes(uc.mem_read(uc.reg_read(UC_ARM_REG_R0), uc.reg_read(UC_ARM_REG_R1) & 0xFFFF)))
        uc.reg_write(UC_ARM_REG_R0, 0)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    saved = [uc.reg_read(r) for r in SAVED]
    hook = uc.hook_add(UC_HOOK_CODE, on_reply, begin=REPLY, end=REPLY)
    uc.mem_write(FRAME, frame)
    uc.reg_write(UC_ARM_REG_R0, FRAME)
    uc.reg_write(UC_ARM_REG_R1, len(frame))
    uc.reg_write(UC_ARM_REG_SP, STACK)
    uc.reg_write(UC_ARM_REG_LR, SENT | 1)
    try:
        uc.emu_start(HANDLER | 1, SENT, count=1_000_000)
    finally:
        uc.hook_del(hook)
        for r, v in zip(SAVED, saved):
            uc.reg_write(r, v)
    return replies


def mon(m, cmd, payload=b""):
    r = c0(m, bytes([0xC0, cmd]) + payload)
    if len(r) != 1 or r[0][:2] != bytes([0xC0, cmd]) or r[0][2] != len(r[0]) - 3 or r[0][3] != 0:
        raise AssertionError(f"C0 {cmd:02X}: {[x.hex() for x in r]}")
    return r[0][4:]


def read_log(m):
    """`hl mon log`: D4 op 0 for the ring state, then D1 peeks of the ring."""
    magic, head, size, wraps, log = struct.unpack("<5I", mon(m, 0xD4, b"\x00"))
    ring = b"".join(mon(m, 0xD1, struct.pack("<IB", log + o, min(200, size - o)))[4:] for o in range(0, size, 200))
    return ring[head % size:] + ring[:head % size] if head > size else ring[:head]


def parse(log):
    """Log text -> [("b", id, ms)] and [("i2c", addr, dir, status, ms)] in order."""
    out = []
    for line in log.decode("latin1").splitlines():
        f = line.split()
        if len(f) == 2 and f[0][0] == "b":
            out.append(("b", int(f[0][1:], 16), int(f[1], 16)))
        elif len(f) == 5 and f[0] == "i2c":
            out.append(("i2c", int(f[1], 16), f[2], int(f[3], 16), int(f[4], 16)))
        else:
            out.append(("?", line))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("image", nargs="?")
    ap.add_argument("--rom")
    ap.add_argument("--insns", type=int, default=150_000_000)
    a = ap.parse_args()
    image, rom = stock_up(a.image), mask_rom(a.rom).read_bytes()
    with tempfile.TemporaryDirectory() as tmp:   # patched images never leave the temporary directory
        both = patched(image, tmp, MONITOR, BOOTLOG)
        alone = patched(image, tmp, BOOTLOG)
    sites = sum("milestone" in op["what"] for op in json.loads(BOOTLOG.read_text())["ops"])

    stock = image.read_bytes()[BODY:]
    s, sp, s_stop = boot(stock, rom, a.insns)
    m, p, stop = boot(both, rom, a.insns)
    ops = lambda mach: [op[:3] for op in mach.flash_ops]
    psmp, psmp_len = m.parts["PSMP"]

    def outside(mach, flash):
        """Offsets outside PSMP where the flash no longer holds the image it was loaded with."""
        want = bytes(flash).ljust(len(mach.flash), b"\xff")
        return [i for i in range(len(mach.flash)) if not psmp <= i < psmp + psmp_len and mach.flash[i] != want[i]]

    good = [
        check(s_stop == "idle" and not s.fault, f"stock: idle task sleeps in WFI after {s.ms} ms"),
        check(stop == "idle" and not m.fault,
              f"patched: idle task sleeps in WFI after {m.ms} ms ({stop}{': ' + m.fault if m.fault else ''})"),
        check(sorted(m.enabled) == sorted(s.enabled) and not m.systick["csr"] & 1,
              "patched: asleep like stock, SysTick off and the same single IRQ enabled"),
        check(not p["flash"].errors and ops(m) == ops(s)
              and all(psmp <= o[1] and o[1] + o[2] <= psmp + psmp_len for o in m.flash_ops),
              f"patched: the same {len(m.flash_ops)} flash writes as stock, all inside PSMP (the patch adds none)"),
        check(m.flash[psmp:psmp + psmp_len] == s.flash[psmp:psmp + psmp_len] and not outside(m, both),
              "patched: PSMP ends with the same bytes as stock, the rest of the flash is as it was written"),
        check(p["i2c"].log == sp["i2c"].log, f"patched: the same I2C bus traffic as stock {p['i2c'].log}"),
    ]

    log = read_log(m)
    magic, head, wraps = struct.unpack("<3I", m.uc.mem_read(MON_RAM, 12))
    good.append(check(magic == MON_MAGIC and wraps == 0 and log == bytes(m.uc.mem_read(MON_LOG, head)),
                      f"log read back through C0 D4 + D1: {len(log)} bytes, same as the ring in RAM"))
    print("\n" + "".join(f"    {line}\n" for line in log.decode("latin1").splitlines()))

    recs = parse(log)
    marks = [r for r in recs if r[0] == "b"]
    i2c = [r for r in recs if r[0] == "i2c"]
    times = [r[-1] for r in recs if r[0] != "?"]
    bus = [(addr >> 1, "r" if addr & 1 else "w", acked) for addr, acked in p["i2c"].log]
    good += [
        check(not any(r[0] == "?" for r in recs), "every log line is a milestone or an I2C record"),
        check([r[1] for r in marks] == list(range(1, sites + 1)),
              f"milestones b01..b{sites:02x}, once each, in order"),
        check(times == sorted(times) and times and 0 < times[0] and times[-1] <= m.ms,
              f"timestamps rise from {times[0] if times else '?'} ms to {times[-1] if times else '?'} ms, before idle"),
        check(len(i2c) == PROBE_TRIES and all(r[1] == PROBE_ADDR and r[3] != 0 for r in i2c),
              f"I2C probe result: address 0x{PROBE_ADDR:x} tried {len(i2c)} times, every transfer failed (NACK)"),
        check([(r[1], r[2], r[3] == 0) for r in i2c] == bus,
              f"I2C records match the bus model: {' '.join(d for _, d, _ in bus)}"),
        check(recs and recs[-1][:2] == ("b", sites) and all(recs.index(r) < len(recs) - 1 for r in i2c),
              "the probe happens during init, before the last milestone"),
    ]

    # The same boot with a device answering at the probed address: the transfers succeed and say so.
    runs = []
    for flash in (stock, both):
        mach, per = chip.power_on(flash, rom)
        dev = per["i2c"].devices[PROBE_ADDR] = Slave(per["i2c"])
        runs.append((mach, per["i2c"].log, dev, mach.run(a.insns)))
    (s3, s3_bus, s3_dev, s3_stop), (m3, m3_bus, m3_dev, m3_stop) = runs
    i2c3 = [r for r in parse(read_log(m3)) if r[0] == "i2c"]
    good += [
        check(m3_stop == s3_stop == "idle" and not m3.fault and m3_bus == s3_bus and all(ok for _, ok in m3_bus)
              and m3_dev.seen == s3_dev.seen and ops(m3) == ops(s3),
              f"with a device at 0x{PROBE_ADDR:x}: idle after {m3.ms} ms, the device sees the same bytes in the same "
              f"transfers as under stock: " + " ".join(f"{n}{d}{b:02x}" for n, d, b in m3_dev.seen)),
        check([(r[1], r[2], r[3]) for r in i2c3] == [(a7 >> 1, "r" if a7 & 1 else "w", 0) for a7, _ in m3_bus]
              and len(i2c3) == PROBE_TRIES,
              f"with a device at 0x{PROBE_ADDR:x}: {len(i2c3)} I2C records, all status 00: "
              + " ".join(r[2] for r in i2c3)),
    ]

    m2, _, stop2 = boot(alone, rom, a.insns)
    good.append(check(stop2 == "idle" and not m2.fault and ops(m2) == ops(s)
                      and struct.unpack("<I", m2.uc.mem_read(MON_RAM, 4))[0] != MON_MAGIC,
                      f"boot-log.json without the monitor: idle after {m2.ms} ms, same flash writes, no ring written"))
    print("PASS" if all(good) else "FAIL")
    sys.exit(0 if all(good) else 1)


if __name__ == "__main__":
    main()
