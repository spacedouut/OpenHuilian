#!/usr/bin/env python3
"""First-steps rehost of the H3Pro Max3 FIRM in Unicorn. Offline only; never touches a bud.

Memory map is from docs/17. The mask ROM is NOT available, so every ROM address is filled with a
Thumb `bx lr` and a code hook logs each call; the few ROM routines whose job is known
(memcpy/memset/memcmp/malloc/free/flash read) are emulated. Anything outside RAM/flash/ROM is
treated as a peripheral: pages are mapped on first touch and every register access is recorded.

usage: h3emu.py <h3promax3.up | raw flash> [--max-insns N] [--unstick] [--set ADDR=VAL]...
"""
import argparse
import collections
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from capstone import CS_ARCH_ARM, CS_MODE_THUMB, Cs
from unicorn import (UC_ARCH_ARM, UC_HOOK_BLOCK, UC_HOOK_CODE, UC_HOOK_MEM_READ,
                     UC_HOOK_MEM_READ_UNMAPPED, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_WRITE_PROT,
                     UC_HOOK_MEM_WRITE_UNMAPPED, UC_HOOK_MEM_FETCH_UNMAPPED, UC_MEM_FETCH_UNMAPPED,
                     UC_MODE_MCLASS, UC_MODE_THUMB, UC_PROT_ALL, UC_PROT_EXEC, UC_PROT_READ, Uc,
                     UcError)
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
                               UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_XPSR,
                               UC_CPU_ARM_CORTEX_M4, UC_CPU_ARM_CORTEX_M7)

from upfmt import parse_index

SRAM, SRAM_SZ = 0x800000, 0x100000
FLASH, FLASH_SZ = 0xC00000, 0x100000
ROM_RANGES = [(0x0, 0x100000), (0x400000, 0x80000)]
HEAP, HEAP_END = 0x880000, 0x8F0000
MMIO_HOOKS = [(0x480000, 0x7FFFFF), (0xD00000, 0xFFFFFFFF)]

ROM_NAMES = {
    0xB2A: "memcpy", 0xBAA: "memset", 0xC54: "memcmp", 0xC70: "malloc", 0xC74: "free",
    0xB6D8: "crit_enter", 0xB6C4: "crit_exit", 0xB78C: "sleep_ms", 0x83B4: "flash_read",
    0xB534: "flash_read_wrap", 0xB514: "flash_write_wrap", 0x48268: "flash_helper",
    0x1A90: "queue_post", 0x2A7C: "timer_queue_helper", 0x4B29C: "bt_stack_helper",
    0x11044: "malloc(bt)", 0x110C0: "bt_host_helper2", 0x9E3C: "rtos_helper", 0x8CA4: "sched_start(ROM)", 0xB4F4: "SVC_handler(ROM)",
    0xB5A8: "PendSV_handler(ROM)",
}
FIRM_NAMES = {
    0x829850: "xTaskCreate?", 0x829A00: "vTaskStartScheduler?", 0xC4FBC0: "event_dispatcher",
    0xC6AD1C: "set_ota_flag",
}


class Emu:
    def __init__(self, flash, args):
        self.args, self.flash = args, flash
        parts = {t.decode(): (a, n) for t, a, n, _ in parse_index(flash)[1]}
        a, n = parts["FIRM"]
        self.firm = flash[a:a + n]
        self.firm_addr = a
        self.load, self.entry, self.blk = struct.unpack_from("<III", self.firm, 0x10)
        self.sp = struct.unpack_from("<I", self.firm, 0x30)[0]
        self.rom_calls = collections.Counter()
        self.rom_first_caller = {}
        self.mmio = {}
        self.mmio_pages = []
        self.reads = collections.Counter()
        self.blocks = collections.deque(maxlen=24)
        self.block_hist = collections.Counter()
        self.heap = HEAP
        self.setvals = dict(args.set)
        self.events = []
        self.tasks = []
        self.cs = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
        self.build()

    def build(self):
        uc = self.uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        uc.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M7 if self.args.cpu == "m7" else UC_CPU_ARM_CORTEX_M4)
        uc.mem_map(SRAM, SRAM_SZ)
        for lo, sz in ROM_RANGES:
            uc.mem_map(lo, sz)
            uc.mem_write(lo, b"\x70\x47" * (sz // 2))
        uc.mem_map(FLASH, FLASH_SZ, UC_PROT_READ | UC_PROT_EXEC)
        img = self.flash[:FLASH_SZ].ljust(FLASH_SZ, b"\xff")
        uc.mem_protect(FLASH, FLASH_SZ, UC_PROT_ALL)
        uc.mem_write(FLASH, img)
        uc.mem_protect(FLASH, FLASH_SZ, UC_PROT_READ | UC_PROT_EXEC)
        # what the bootloader does: copy the first 4 KiB block to RAM and jump to the entry
        uc.mem_write(self.load, self.firm[0x470:0x470 + self.blk])
        uc.reg_write(UC_ARM_REG_SP, self.sp)

        uc.hook_add(UC_HOOK_MEM_READ_UNMAPPED | UC_HOOK_MEM_WRITE_UNMAPPED |
                    UC_HOOK_MEM_FETCH_UNMAPPED, self.on_unmapped)
        uc.hook_add(UC_HOOK_MEM_WRITE_PROT, self.on_prot)
        uc.hook_add(UC_HOOK_BLOCK, self.on_block)
        for lo, sz in ROM_RANGES:
            uc.hook_add(UC_HOOK_CODE, self.on_rom, begin=lo, end=lo + sz - 1)
        for lo, hi in MMIO_HOOKS:
            uc.hook_add(UC_HOOK_MEM_READ, self.on_mmio_read, begin=lo, end=hi)
            uc.hook_add(UC_HOOK_MEM_WRITE, self.on_mmio_write, begin=lo, end=hi)
        for addr in list(FIRM_NAMES) + list(self.args.watch):
            uc.hook_add(UC_HOOK_CODE, self.on_watch, begin=addr, end=addr)

    def cstr(self, addr, n=40):
        try:
            b = bytes(self.uc.mem_read(addr, n)).split(b"\0")[0]
        except UcError:
            return None
        return b.decode("ascii") if b and all(32 <= c < 127 for c in b) else None

    def note(self, msg):
        self.events.append((self.count(), msg))
        if self.args.verbose:
            print(f"  [{self.count():>9}] {msg}")

    def count(self):
        return sum(self.block_hist.values())

    def r(self, reg):
        return self.uc.reg_read(reg)

    def on_block(self, uc, addr, size, _):
        self.blocks.append(addr)
        self.block_hist[addr] += 1

    def on_watch(self, uc, addr, size, _):
        regs = [self.r(x) for x in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)]
        strs = [f"{x:#x}" + (f'="{self.cstr(x)}"' if self.cstr(x) else "") for x in regs]
        if addr == 0x829850:
            self.tasks.append((regs[0], self.cstr(regs[2]) or "?", regs[1], regs[3]))
        self.note(f"{FIRM_NAMES.get(addr, 'watch')}@{addr:#x} lr={self.r(UC_ARM_REG_LR):#x} "
                  + " ".join(strs))

    def on_rom(self, uc, addr, size, _):
        self.rom_calls[addr] += 1
        self.rom_first_caller.setdefault(addr, self.r(UC_ARM_REG_LR))
        r0, r1, r2 = (self.r(x) for x in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
        name = ROM_NAMES.get(addr)
        if name == "sched_start(ROM)" and self.args.run_task:
            return self.start_task(uc)
        if name == "memcpy" and r2 < 0x100000:
            uc.mem_write(r0, bytes(uc.mem_read(r1, r2))) if r2 else None
        elif name == "memset" and r2 < 0x100000:
            uc.mem_write(r0, bytes([r1 & 0xFF]) * r2) if r2 else None
        elif name == "memcmp" and r2 < 0x100000:
            a, b = bytes(uc.mem_read(r0, r2)), bytes(uc.mem_read(r1, r2))
            uc.reg_write(UC_ARM_REG_R0, (a > b) - (a < b) & 0xFFFFFFFF)
        elif name == "flash_read":
            off = r1 & 0xFFFFFF
            off = off - FLASH if off >= FLASH else off
            uc.mem_write(r0, self.flash[off:off + r2].ljust(r2, b"\xff"))
            uc.reg_write(UC_ARM_REG_R0, 0)
        elif name in ("malloc", "malloc(bt)"):
            p, self.heap = self.heap, (self.heap + r0 + 7) & ~7
            uc.reg_write(UC_ARM_REG_R0, p if self.heap < HEAP_END else 0)

    def start_task(self, uc):
        t = next((t for t in self.tasks if t[1] == self.args.run_task), None)
        if not t:
            return self.note(f"scheduler: no task named {self.args.run_task!r}, have {[x[1] for x in self.tasks]}")
        self.note(f"scheduler shim: jumping into task {t[1]!r} entry={t[0]:#x} arg={t[2]:#x}")
        uc.reg_write(UC_ARM_REG_SP, 0x870000)
        uc.reg_write(UC_ARM_REG_R0, t[2])
        uc.reg_write(UC_ARM_REG_LR, 0)
        uc.reg_write(UC_ARM_REG_PC, t[0] | 1)

    def on_unmapped(self, uc, access, addr, size, value, _):
        pc = self.r(UC_ARM_REG_PC)
        if access == UC_MEM_FETCH_UNMAPPED:
            self.note(f"FETCH from unmapped {addr:#x} (pc={pc:#x})")
            return False
        page = addr & ~0xFFF
        uc.mem_map(page, 0x1000)
        self.mmio_pages.append(page)
        self.note(f"new peripheral page {page:#x} first touched at pc={pc:#x}")
        return True

    def on_prot(self, uc, access, addr, size, value, _):
        self.note(f"write to read-only {addr:#x} <- {value:#x} (pc={self.r(UC_ARM_REG_PC):#x})")
        return False

    def reg(self, addr):
        return self.mmio.setdefault(addr, {"r": 0, "w": 0, "last_w": None, "pc": None})

    def on_mmio_read(self, uc, access, addr, size, value, _):
        rec = self.reg(addr)
        rec["r"] += 1
        rec["pc"] = rec["pc"] or self.r(UC_ARM_REG_PC)
        n = rec["r"]
        if addr in self.setvals:
            uc.mem_write(addr, struct.pack("<I", self.setvals[addr])[:size])
        elif self.args.unstick and n > 64:
            uc.mem_write(addr, (b"\xff" if (n // 64) % 2 else b"\x00") * size)

    def on_mmio_write(self, uc, access, addr, size, value, _):
        rec = self.reg(addr)
        rec["w"] += 1
        rec["last_w"] = value & 0xFFFFFFFF
        rec["pc"] = rec["pc"] or self.r(UC_ARM_REG_PC)

    def disasm(self, pc, n=4):
        try:
            code = bytes(self.uc.mem_read(pc & ~1, 16))
        except UcError:
            return []
        return [f"{i.address:#x}: {i.mnemonic} {i.op_str}" for i in self.cs.disasm(code, pc & ~1)][:n]

    def call(self):
        a, uc = self.args, self.uc
        data_lo, data_hi, delta = 0x805C40, 0x82CA2C, 0x8009F8
        uc.mem_write(data_lo, self.firm[data_lo - delta:data_hi - delta])
        uc.mem_map(0xE000E000, 0x1000)
        uc.mem_write(0xE000ED88, struct.pack("<I", 0x0F00000))
        for addr, blob in a.poke:
            try:
                uc.mem_write(addr, blob)
            except UcError:
                for page in range(addr & ~0xFFF, addr + len(blob), 0x1000):
                    try:
                        uc.mem_map(page, 0x1000)
                    except UcError:
                        pass
                uc.mem_write(addr, blob)
        for i in range(13):
            uc.reg_write(UC_ARM_REG_R0 + i, 0)
        for reg, val in a.reg:
            uc.reg_write(UC_ARM_REG_R0 + reg, val)
        sent = 0x7F000
        uc.reg_write(UC_ARM_REG_SP, 0x870000)
        uc.reg_write(UC_ARM_REG_LR, sent | 1)
        stop = "returned cleanly"
        try:
            uc.emu_start(a.call | 1, sent, count=a.max_insns)
            if self.r(UC_ARM_REG_PC) != sent:
                stop = "instruction budget reached"
        except UcError as e:
            stop = f"CPU fault: {e}"
        print(f"call {a.call:#x}: {stop}   r0={self.r(UC_ARM_REG_R0):#x}  pc={self.r(UC_ARM_REG_PC):#x}  "
              f"blocks={self.count()}  sp={self.r(UC_ARM_REG_SP):#x}")
        for lo, n in a.peek:
            print(f"peek {lo:#x}+{n}: {bytes(uc.mem_read(lo, n)).hex()}")
        print(f"ROM calls: {dict((hex(k), v) for k, v in self.rom_calls.items())}  peripheral pages: "
              f"{[hex(x) for x in self.mmio_pages]}")
        return stop == "returned cleanly"

    def run(self):
        if self.args.call is not None:
            sys.exit(0 if self.call() else 1)
        stop = "instruction budget reached"
        try:
            self.uc.emu_start(self.entry | 1, 0, count=self.args.max_insns)
        except UcError as e:
            stop = f"CPU fault: {e}"
        self.report(stop)

    def report(self, stop):
        pc = self.r(UC_ARM_REG_PC)
        print(f"\n== stop: {stop}")
        print(f"blocks executed: {self.count():,}   pc={pc:#x}  sp={self.r(UC_ARM_REG_SP):#x}  "
              f"lr={self.r(UC_ARM_REG_LR):#x}")
        for line in self.disasm(pc):
            print("   ", line)
        print("last blocks:", " ".join(f"{b:#x}" for b in list(self.blocks)[-12:]))
        print("\n== events (first 40)")
        for n, m in self.events[:40]:
            print(f"  [{n:>9}] {m}")
        print(f"\n== ROM calls ({sum(self.rom_calls.values()):,} total, {len(self.rom_calls)} distinct)")
        for a, c in self.rom_calls.most_common(25):
            tag = ROM_NAMES.get(a, "?")
            print(f"  {a:#9x} x{c:<6} {tag:<18} first lr={self.rom_first_caller[a]:#x}")
        print(f"\n== peripheral pages: {', '.join(f'{p:#x}' for p in self.mmio_pages) or 'none'}")
        print(f"== registers touched: {len(self.mmio)}")
        runs = []
        for a in sorted(self.mmio):
            m = self.mmio[a]
            key = (m["r"], m["w"], m["last_w"], m["pc"])
            if runs and runs[-1][2] == key and runs[-1][1] + 1 == a:
                runs[-1][1] = a
            else:
                runs.append([a, a, key])
        for lo, hi, (r, w, lw, pc0) in runs[:70]:
            span = f"{lo:#010x}" + (f"..{hi:#x}" if hi != lo else "")
            print(f"  {span:<24} r={r:<7} w={w:<3} last_w={'-' if lw is None else hex(lw):<10} first pc={pc0:#x}")
        print("\n== hottest blocks")
        for a, c in self.block_hist.most_common(8):
            print(f"  {a:#x} x{c}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("image")
    ap.add_argument("--max-insns", type=int, default=2_000_000)
    ap.add_argument("--unstick", action="store_true", help="alternate polled MMIO reads 0/0xFFFFFFFF")
    ap.add_argument("--set", action="append", default=[], type=lambda s: tuple(int(x, 0) for x in s.split("=")),
                    help="ADDR=VAL value returned by an MMIO register read")
    ap.add_argument("--run-task", metavar="NAME", help="at the ROM scheduler call, jump into this task")
    ap.add_argument("--call", type=lambda s: int(s, 0), metavar="ADDR",
                    help="skip boot; call one function (Thumb) with --reg args and return to a sentinel")
    ap.add_argument("--reg", action="append", default=[], type=lambda s: (int(s.split("=")[0].lstrip("rR")), int(s.split("=")[1], 0)),
                    help="r0=VAL for --call")
    ap.add_argument("--poke", action="append", default=[], type=lambda s: (int(s.split("=")[0], 0), bytes.fromhex(s.split("=")[1])),
                    help="ADDR=HEXBYTES written to RAM before --call")
    ap.add_argument("--peek", action="append", default=[], type=lambda s: (int(s.split(":")[0], 0), int(s.split(":")[1], 0)),
                    help="ADDR:LEN dumped after --call")
    ap.add_argument("--cpu", default="m4", choices=["m4", "m7"])
    ap.add_argument("--watch", action="append", default=[], type=lambda s: int(s, 0))
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    data = Path(args.image).read_bytes()
    flash = data[0x100:] if data[:6] == b"CONFIG" else data
    if flash[:4] != b"HLKJ":
        sys.exit("no HLKJ header at flash 0")
    Emu(flash, args).run()


if __name__ == "__main__":
    main()
