#!/usr/bin/env python3
"""Power-on boot of a stock image on the hardware model: mask ROM, BOOT, FIRM. Offline only.

    pip install unicorn
    OPENHUILIAN_MASK_ROM=... python3 -m openhuilian.emu.boot_check "$OPENHUILIAN_STOCK_UP"

Starts at the ROM reset vector with openhuilian.emu.machine + chip and checks the chain the
chip runs: the ROM accepts the flash header through the controller's CRC unit, loads BOOT,
BOOT starts FIRM, FIRM starts the ROM's FreeRTOS scheduler (SVC, PendSV and SysTick are taken
as real exceptions), brings its drivers up and the idle task goes to sleep in WFI with only the
PMU wake-up interrupt enabled. Then wakes it a few times, and checks that a damaged header is
refused. Flash writes must go through the controller, with write-enable, and stay inside PSMP.
Prints what the firmware touched that is not modelled yet.
"""
import argparse
import sys

from openhuilian.emu import chip
from openhuilian.format.upfmt import BODY
from openhuilian.inputs import mask_rom, stock_up

PMU_WAKE_IRQ = 48
STAGE_HEADER_OK, STAGE_HEADER_BAD_CRC = 0x1015, 0x1013
BOOT_STAGES = [8, 9, 0xA, 0xB]


def check(ok, what):
    print(("ok   " if ok else "FAIL ") + what)
    return bool(ok)


def boot(flash, rom, insns):
    m, p = chip.power_on(flash, rom)
    return m, p, m.run(insns)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("image", nargs="?")
    ap.add_argument("--rom")
    ap.add_argument("--insns", type=int, default=150_000_000)
    ap.add_argument("-v", "--verbose", action="store_true", help="list every register touched")
    a = ap.parse_args()
    flash, rom = stock_up(a.image).read_bytes()[BODY:], mask_rom(a.rom).read_bytes()

    m, p, stop = boot(flash, rom, a.insns)
    stages, exc = p["system"].stages, m.exc_counts
    psmp, psmp_len = m.parts["PSMP"]
    writes = m.flash_ops
    good = [
        check(STAGE_HEADER_OK in stages, "ROM accepts the flash header (CRC unit in the flash controller)"),
        check(bytes(p["uart0"].tx) == b"#", "BOOT prints '#' on UART0"),
        check(stages[-len(BOOT_STAGES):] == BOOT_STAGES, "BOOT reports stages 8, 9, 0xA, 0xB and starts FIRM"),
        check(exc[11] == 1 and exc[14] and exc[15],
              f"scheduler runs: SVC {exc[11]}, PendSV {exc[14]}, SysTick {exc[15]}"),
        check(stop == "idle" and not m.fault,
              f"idle task sleeps in WFI after {m.ms} ms ({stop}{': ' + m.fault if m.fault else ''})"),
        check(sorted(m.enabled) == [16 + PMU_WAKE_IRQ] and not m.systick["csr"] & 1,
              "asleep with SysTick off and only the PMU wake-up IRQ enabled"),
        check(not p["flash"].errors, f"flash commands are legal {p['flash'].errors[:3]}"),
        check(writes and all(psmp <= op[1] and op[1] + op[2] <= psmp + psmp_len for op in writes),
              f"{len(writes)} flash writes, all inside PSMP"),
        check(not any("non-erased" in op[0] for op in writes), "no program onto non-erased bytes"),
    ]

    before = exc[16 + PMU_WAKE_IRQ]
    for _ in range(5):
        m.raise_irq(PMU_WAKE_IRQ)
        stop = m.run(20_000_000)
    good.append(check(stop == "idle" and exc[16 + PMU_WAKE_IRQ] == before + 5 and not m.fault,
                      "PMU wake-up IRQ wakes it, the handler runs, it sleeps again"))

    bad = bytearray(flash)
    bad[0x10] ^= 1
    m2, p2, _ = boot(bytes(bad), rom, 12_000_000)
    good.append(check(STAGE_HEADER_BAD_CRC in p2["system"].stages and 8 not in p2["system"].stages,
                      "ROM refuses a header with a bad CRC and never starts BOOT"))

    print(f"\nI2C addresses probed: {sorted({hex(a >> 1) for a, _ in p['i2c'].log})} (none modelled, all NACK)")
    print(f"PMU registers used: {sorted({hex(r) for _, _, _, r, _, _ in p['pmu'].log})}")
    modelled = {q.base for q in m.peripherals}
    pages = {}
    for addr, rec in m.mmio.items():
        if addr & ~0xFFF not in modelled and addr not in m.self_clearing:
            n = pages.setdefault(addr & ~0xFFF, [0, 0, 0])
            n[0] += 1
            n[1] += rec["r"]
            n[2] += rec["w"]
    print("not modelled (reads return the last value written):")
    for page, (regs, r, w) in sorted(pages.items()):
        print(f"  {page:#x}: {regs} registers, {r} reads, {w} writes")
    if a.verbose:
        for addr, rec in sorted(m.mmio.items()):
            print(f"  {addr:#x} r={rec['r']} w={rec['w']} last_w={rec['last_w']} first pc={rec['pc']:#x}")
    print("PASS" if all(good) else "FAIL")
    sys.exit(0 if all(good) else 1)


if __name__ == "__main__":
    main()
