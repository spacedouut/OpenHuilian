"""Hardware model of the H3Pro Max3 (Huilian 377H3) for Unicorn. Offline only; never touches a bud.

What is modelled, and what real-chip behaviour each piece stands for:

* the real mask ROM at 0x0 when a dump is supplied (kernel, libc, flash services, BT stack run as
  on the chip); without one, ROM is `bx lr` and only the helpers h3emu names are emulated
* Cortex-M exception entry and return (SVC, PendSV, SysTick, external IRQs) with MSP/PSP, IPSR,
  PRIMASK/BASEPRI and priorities, so the ROM scheduler context-switches real tasks
* SCB, NVIC and SysTick registers; time advances with executed instructions
* peripheral registers through `Peripheral` models; anything unmodelled reads back what was
  written and is reported, with the polling loops that never saw their bit change
* SPI NOR flash behind the XIP window: erase sets FF, program only clears bits
"""
import collections
import struct

from unicorn import (UC_ARCH_ARM, UC_HOOK_BLOCK, UC_HOOK_INTR, UC_HOOK_MEM_FETCH_UNMAPPED,
                     UC_HOOK_MEM_READ, UC_HOOK_MEM_READ_UNMAPPED, UC_HOOK_MEM_WRITE,
                     UC_HOOK_MEM_WRITE_UNMAPPED, UC_MEM_FETCH_UNMAPPED,
                     UC_MODE_MCLASS, UC_MODE_THUMB, Uc, UcError)
from unicorn.arm_const import (UC_ARM_REG_BASEPRI, UC_ARM_REG_CONTROL, UC_ARM_REG_LR, UC_ARM_REG_MSP,
                               UC_ARM_REG_PC, UC_ARM_REG_PRIMASK, UC_ARM_REG_PSP, UC_ARM_REG_R0,
                               UC_ARM_REG_R12, UC_ARM_REG_SP, UC_ARM_REG_XPSR, UC_CPU_ARM_CORTEX_M4)

from openhuilian.format.upfmt import parse_index

SRAM, SRAM_SZ = 0x800000, 0x100000
FLASH, FLASH_SZ = 0xC00000, 0x100000
ROM_SZ = 0x100000
ROM2, ROM2_SZ = 0x400000, 0x80000
SCS = 0xE000E000
EXC_SVC, EXC_PENDSV, EXC_SYSTICK, EXC_IRQ0 = 11, 14, 15, 16
EXCP_SWI, EXCP_EXCEPTION_EXIT = 2, 8
FRAME = (UC_ARM_REG_R0, UC_ARM_REG_R0 + 1, UC_ARM_REG_R0 + 2, UC_ARM_REG_R0 + 3, UC_ARM_REG_R12,
         UC_ARM_REG_LR)


class Peripheral:
    """A block of registers at `base`. Subclasses override read/write; state defaults to RAM."""
    base, size, name = 0, 0x1000, "?"

    def __init__(self, machine):
        self.m, self.regs = machine, {}

    def read(self, off, size):
        return self.regs.get(off, 0)

    def write(self, off, value, size):
        self.regs[off] = value


class Machine:
    def __init__(self, flash, rom=None, cpu=UC_CPU_ARM_CORTEX_M4, cpu_hz=16_000_000):
        self.flash = bytearray(flash[:FLASH_SZ].ljust(FLASH_SZ, b"\xff"))
        self.rom, self.cpu_hz = rom, cpu_hz
        self.parts = {t.decode(): (a, n) for t, a, n, _ in parse_index(flash)[1]}
        a, n = self.parts["FIRM"]
        self.firm = bytes(self.flash[a:a + n])
        self.load, self.entry, self.blk = struct.unpack_from("<III", self.firm, 0x10)
        self.vectors = self.load   # FIRM's vector table heads its RAM block? set by VTOR write
        self.cycles = 0
        self.blocks = collections.deque(maxlen=48)
        self.block_hist = collections.Counter()
        self.events = []
        self.verbose = False
        self.pending, self.active = set(), []
        self.enabled = set()
        self.prio = collections.defaultdict(int)
        self.systick = {"csr": 0, "rvr": 0, "next": None}
        self.scs = {0xD88: 0x00F00000, 0xD00: 0x410FC241}
        self.mmio = {}
        self.activity = 0   # register writes + exceptions taken; lets models spot busy-waits
        self.unmodelled_pages = []
        self.peripherals = []
        self.exc_counts = collections.Counter()
        self.flash_ops = []
        self.fault = None
        self.trace = None          # set to a list to record every block entered
        self._stop = None
        self.stall_limit = 2_000_000   # reads of one register with nothing else happening
        self._last_read = None
        self._woken = None
        self._wfi_blocks, self.wfi_count = {}, 0
        self.self_clearing = {}    # register -> bits that read back 0 after being written 1
        self.read_values = {}      # register -> fixed value or callable(machine) -> value
        uc = self.uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        uc.ctl_set_cpu_model(cpu)
        uc.mem_map(SRAM, SRAM_SZ)
        uc.mem_map(0, ROM_SZ)
        uc.mem_write(0, b"\x70\x47" * (ROM_SZ // 2))
        if rom:
            uc.mem_write(0, rom)
        uc.mem_map(ROM2, ROM2_SZ)
        uc.mem_write(ROM2, b"\x70\x47" * (ROM2_SZ // 2))
        uc.mem_map(FLASH, FLASH_SZ)   # writable for the model; CPU writes are caught by a hook
        self._sync_flash(0, FLASH_SZ)
        uc.hook_add(UC_HOOK_MEM_WRITE, self._on_prot, begin=FLASH, end=FLASH + FLASH_SZ - 1)
        uc.mem_map(SCS, 0x1000)
        uc.mem_write(SCS + 0xD88, struct.pack("<I", 0x00F00000))
        uc.hook_add(UC_HOOK_MEM_READ_UNMAPPED | UC_HOOK_MEM_WRITE_UNMAPPED |
                    UC_HOOK_MEM_FETCH_UNMAPPED, self._on_unmapped)
        uc.hook_add(UC_HOOK_BLOCK, self._on_block)
        uc.hook_add(UC_HOOK_INTR, self._on_intr)
        uc.hook_add(UC_HOOK_MEM_READ, self._on_scs_read, begin=SCS, end=SCS + 0xFFF)
        uc.hook_add(UC_HOOK_MEM_WRITE, self._on_scs_write, begin=SCS, end=SCS + 0xFFF)
        for lo, hi in ((0x10000000, 0x5FFFFFFF),):
            uc.hook_add(UC_HOOK_MEM_READ, self._on_mmio_read, begin=lo, end=hi)
            uc.hook_add(UC_HOOK_MEM_WRITE, self._on_mmio_write, begin=lo, end=hi)

    # ---- helpers
    def r(self, reg):
        return self.uc.reg_read(reg)

    def w(self, reg, value):
        self.uc.reg_write(reg, value & 0xFFFFFFFF)

    def rd32(self, addr):
        return struct.unpack("<I", self.uc.mem_read(addr, 4))[0]

    def wr32(self, addr, value):
        self.uc.mem_write(addr, struct.pack("<I", value & 0xFFFFFFFF))

    def note(self, msg):
        self.events.append((self.cycles, msg))
        if self.verbose:
            print(f"  [{self.cycles:>10}] {msg}")

    @property
    def pc(self):
        return self.uc.reg_read(UC_ARM_REG_PC)

    @property
    def ms(self):
        return self.cycles * 1000 // self.cpu_hz

    def halt(self):
        """Make run() return "halt" at the current instruction (for hooks and models)."""
        self._stop = "halt"
        self.uc.emu_stop()

    def add(self, peripheral_cls):
        p = peripheral_cls(self)
        self.peripherals.append(p)
        return p

    def peripheral(self, addr):
        for p in self.peripherals:
            if p.base <= addr < p.base + p.size:
                return p

    # ---- reset
    def reset(self):
        """Power-on reset. With a ROM dump the CPU starts at the ROM reset vector, as on the chip
        (ROM start-up, then BOOT from flash, then FIRM). Without one, start where BOOT would
        have left FIRM: first block copied to RAM, PC at its entry."""
        self.pending.clear()
        self.active.clear()
        self.w(UC_ARM_REG_XPSR, 0x01000000)
        self.w(UC_ARM_REG_CONTROL, 0)
        self.w(UC_ARM_REG_PRIMASK, 0)
        self.w(UC_ARM_REG_BASEPRI, 0)
        if self.rom:
            self.vectors = 0
            self.w(UC_ARM_REG_SP, self.rd32(0))
            self.w(UC_ARM_REG_PC, self.rd32(4))
        else:
            self.uc.mem_write(self.load, self.firm[0x470:0x470 + self.blk])
            self.w(UC_ARM_REG_SP, struct.unpack_from("<I", self.firm, 0x30)[0])
            self.w(UC_ARM_REG_PC, self.entry)

    # ---- flash (SPI NOR behind the XIP window)
    def _sync_flash(self, off, n):
        self.uc.mem_write(FLASH + off, bytes(self.flash[off:off + n]))

    def flash_erase(self, off, n):
        self.flash[off:off + n] = b"\xff" * n
        self._sync_flash(off, n)
        self.flash_ops.append(("erase", off, n, self.r(UC_ARM_REG_PC)))

    def flash_program(self, off, data, quiet=False):
        old = self.flash[off:off + len(data)]
        if any(d & ~o & 0xFF for d, o in zip(data, old)):
            self.flash_ops.append(("program onto non-erased", off, len(data), self.r(UC_ARM_REG_PC)))
        self.flash[off:off + len(data)] = bytes(d & o for d, o in zip(data, old))
        self._sync_flash(off, len(data))
        if not quiet:
            self.flash_ops.append(("program", off, len(data), self.r(UC_ARM_REG_PC)))

    # ---- memory hooks
    def _on_unmapped(self, uc, access, addr, size, value, _):
        pc = self.r(UC_ARM_REG_PC)
        if access == UC_MEM_FETCH_UNMAPPED:
            self.fault = f"fetch from unmapped {addr:#x} (pc={pc:#x} lr={self.r(UC_ARM_REG_LR):#x})"
            return False
        if addr < 0x1000:
            self.fault = f"NULL-page data access {addr:#x} at pc={pc:#x}"
        page = addr & ~0xFFF
        uc.mem_map(page, 0x1000)
        self.unmodelled_pages.append(page)
        self.note(f"access outside the memory map: page {page:#x} first touched at pc={pc:#x}")
        return True

    def _on_prot(self, uc, access, addr, size, value, _):
        self.fault = f"CPU write to XIP flash {addr:#x} <- {value:#x} (pc={self.r(UC_ARM_REG_PC):#x})"
        self._stop = "fault"
        uc.emu_stop()
        return False

    def _on_block(self, uc, addr, size, _):
        if not self.blocks or self.blocks[-1] != addr:
            self.blocks.append(addr)
            if self.trace is not None:
                self.trace.append(addr)
        self.block_hist[addr] += 1
        self.cycles += size >> 1
        st = self.systick
        wfi = self._has_wfi(addr, size)
        if wfi and addr == self._woken:
            self._woken = None      # back from the interrupt that ended this sleep
            wfi = False
        if wfi and not any(e < EXC_IRQ0 or e in self.enabled for e in self.pending):
            # WFI: the core sleeps until an enabled interrupt is pending (masked by PRIMASK or
            # not). Skip to the next SysTick if it can wake us; with no modelled wake source
            # left the machine is asleep for good.
            self.wfi_count += 1
            if st["next"] is not None and st["csr"] & 2:
                self.cycles = max(self.cycles, st["next"])
            else:
                self._stop = "idle"
                uc.emu_stop()
                return
        if st["next"] is not None and self.cycles >= st["next"]:
            st["next"] += self._systick_period()
            st["csr"] |= 0x10000
            if st["csr"] & 2:
                self.pending.add(EXC_SYSTICK)
        for p in self.tickers:
            p.tick()
        if self.pending and self._deliverable() is not None:
            if wfi:
                self._woken = addr
            self._stop = "exception"
            uc.emu_stop()

    tickers = ()

    def _has_wfi(self, addr, size):
        hit = self._wfi_blocks.get(addr)
        if hit is None:
            code, i, hit = bytes(self.uc.mem_read(addr, size)), 0, False
            while i + 1 < len(code):
                hw = code[i] | code[i + 1] << 8
                if hw == 0xBF30:
                    hit = True
                    break
                i += 4 if hw >= 0xE800 else 2
            self._wfi_blocks[addr] = hit
        return hit

    def _on_intr(self, uc, intno, _):
        if intno == EXCP_SWI:
            self.pending.add(EXC_SVC)
            self._stop = "exception"
        elif intno == EXCP_EXCEPTION_EXIT:
            self._stop = "return"
        else:
            self.fault = f"CPU exception {intno} at pc={self.r(UC_ARM_REG_PC):#x}"
            self._stop = "fault"
        uc.emu_stop()

    # ---- System Control Space: NVIC, SysTick, SCB
    def _on_scs_read(self, uc, access, addr, size, value, _):
        off = addr - SCS
        base = off & ~3
        st = self.systick
        if base == 0x10:
            v = st["csr"]
            st["csr"] &= ~0x10000
        elif base == 0x14:
            v = st["rvr"]
        elif base == 0x18:
            v = 0
            if st["next"] is not None:
                v = (st["next"] - self.cycles) * (st["rvr"] + 1) // self._systick_period()
        elif 0x100 <= base < 0x140 or 0x180 <= base < 0x1C0:
            n = (base & 0x7F) // 4 * 32
            v = sum(1 << i for i in range(32) if EXC_IRQ0 + n + i in self.enabled)
        elif 0x200 <= base < 0x240 or 0x280 <= base < 0x2C0:
            n = (base & 0x7F) // 4 * 32
            v = sum(1 << i for i in range(32) if EXC_IRQ0 + n + i in self.pending)
        elif 0x400 <= base < 0x500:
            v = sum(self.prio[EXC_IRQ0 + base - 0x400 + i] << (8 * i) for i in range(4))
        elif 0xD18 <= base < 0xD24:
            v = sum(self.prio[4 + base - 0xD18 + i] << (8 * i) for i in range(4))
        elif base == 0xD04:
            active = self.r(UC_ARM_REG_XPSR) & 0x1FF
            pend = min(self.pending, default=0)
            v = active | pend << 12 | (EXC_PENDSV in self.pending) << 28 | \
                (EXC_SYSTICK in self.pending) << 26 | (not self.active[:-1]) << 11
        elif base == 0xD08:
            v = self.vectors
        else:
            v = self.scs.get(base, 0)
        uc.mem_write(SCS + base, struct.pack("<I", v & 0xFFFFFFFF))

    def _on_scs_write(self, uc, access, addr, size, value, _):
        off = addr - SCS
        base = off & ~3
        st = self.systick
        if size != 4:   # byte/halfword writes land in the priority registers
            for i in range(size):
                if 0x400 <= off + i < 0x500:
                    self.prio[EXC_IRQ0 + off + i - 0x400] = value >> (8 * i) & 0xFF
                elif 0xD18 <= off + i < 0xD24:
                    self.prio[4 + off + i - 0xD18] = value >> (8 * i) & 0xFF
            return
        if base == 0x10:
            st["csr"] = value & 7
            st["next"] = self.cycles + self._systick_period() if value & 1 else None
        elif base == 0x14:
            st["rvr"] = value & 0xFFFFFF
        elif base == 0x18:
            if st["next"] is not None:
                st["next"] = self.cycles + self._systick_period()
        elif 0x100 <= base < 0x140:
            self.enabled |= {EXC_IRQ0 + (base - 0x100) * 8 + i for i in range(32) if value >> i & 1}
        elif 0x180 <= base < 0x1C0:
            self.enabled -= {EXC_IRQ0 + (base - 0x180) * 8 + i for i in range(32) if value >> i & 1}
        elif 0x200 <= base < 0x240:
            self.pending |= {EXC_IRQ0 + (base - 0x200) * 8 + i for i in range(32) if value >> i & 1}
        elif 0x280 <= base < 0x2C0:
            self.pending -= {EXC_IRQ0 + (base - 0x280) * 8 + i for i in range(32) if value >> i & 1}
        elif 0x400 <= base < 0x500:
            for i in range(4):
                self.prio[EXC_IRQ0 + base - 0x400 + i] = value >> (8 * i) & 0xFF
        elif 0xD18 <= base < 0xD24:
            for i in range(4):
                self.prio[4 + base - 0xD18 + i] = value >> (8 * i) & 0xFF
        elif base == 0xD04:
            for bit, exc, on in ((28, EXC_PENDSV, 1), (27, EXC_PENDSV, 0), (26, EXC_SYSTICK, 1),
                                 (25, EXC_SYSTICK, 0)):
                if value >> bit & 1:
                    (self.pending.add if on else self.pending.discard)(exc)
        elif base == 0xD08:
            self.vectors = value
            self.note(f"VTOR <- {value:#x}")
        elif base == 0xD0C and value >> 16 == 0x05FA and value & 4:
            self.note(f"SYSRESETREQ at pc={self.r(UC_ARM_REG_PC):#x}")
            self._stop = "reset"
            uc.emu_stop()
        else:
            self.scs[base] = value

    def _systick_period(self):
        """Instructions per SysTick wrap. CLKSOURCE=0 selects the 1 MHz reference clock."""
        n = self.systick["rvr"] + 1
        return n if self.systick["csr"] & 4 else max(1, n * self.cpu_hz // 1_000_000)

    def raise_irq(self, n):
        self.pending.add(EXC_IRQ0 + n)

    # ---- peripherals
    def _reg(self, addr):
        return self.mmio.setdefault(addr, {"r": 0, "w": 0, "last_w": None, "pc": None, "last_r": 0,
                                           "streak": 0, "max_streak": 0, "poll_pc": None})

    def _on_mmio_read(self, uc, access, addr, size, value, _):
        base = addr & ~3
        rec = self._reg(base)
        pc = self.r(UC_ARM_REG_PC)
        rec["r"] += 1
        rec["pc"] = rec["pc"] or pc
        if self._last_read != base:   # a streak is one register read over and over, nothing between
            self._last_read, rec["streak"] = base, 0
        rec["streak"] += 1
        if rec["streak"] > rec["max_streak"]:
            rec["max_streak"], rec["poll_pc"] = rec["streak"], pc
            if self.stall_limit and rec["streak"] > self.stall_limit:
                self.fault = f"stalled polling {base:#x} at pc={pc:#x}"
                self._stop = "stall"
                uc.emu_stop()
        p = self.peripheral(base)
        if base in self.read_values:
            v = self.read_values[base]
            self.wr32(base, v(self) if callable(v) else v)
        elif base in self.self_clearing:
            self.wr32(base, self.rd32(base) & ~self.self_clearing[base])
        elif p:
            v = p.read(base - p.base, 4) & 0xFFFFFFFF
            try:
                uc.mem_write(base, struct.pack("<I", v))
            except UcError:
                uc.mem_map(base & ~0xFFF, 0x1000)
                uc.mem_write(base, struct.pack("<I", v))

    def _on_mmio_write(self, uc, access, addr, size, value, _):
        base = addr & ~3
        rec = self._reg(base)
        self.activity += 1
        rec["w"] += 1
        rec["pc"] = rec["pc"] or self.r(UC_ARM_REG_PC)
        rec["streak"], self._last_read = 0, None
        p = self.peripheral(base)
        if size != 4:
            try:
                old = self.rd32(base)
            except UcError:
                old = 0
            sh = (addr & 3) * 8
            mask = ((1 << size * 8) - 1) << sh
            value = old & ~mask | (value << sh) & mask
        rec["last_w"] = value & 0xFFFFFFFF
        if p:
            p.write(base - p.base, value & 0xFFFFFFFF, 4)

    # ---- exceptions
    def _exec_prio(self):
        prio = 256
        if self.active:
            prio = min(self.prio[e] if e >= 4 else e - 4 for e in self.active)
        basepri = self.r(UC_ARM_REG_BASEPRI) & 0xFF
        if basepri:
            prio = min(prio, basepri)
        if self.r(UC_ARM_REG_PRIMASK) & 1:
            prio = min(prio, 0)
        return prio

    def _deliverable(self):
        cur = self._exec_prio()
        best = None
        for e in self.pending:
            if e >= EXC_IRQ0 and e not in self.enabled:
                continue
            if self.prio[e] < cur and (best is None or (self.prio[e], e) < (self.prio[best], best)):
                best = e
        return best

    def _enter(self, exc):
        uc = self.uc
        self.pending.discard(exc)
        self.exc_counts[exc] += 1
        self.activity += 1
        xpsr, control = self.r(UC_ARM_REG_XPSR), self.r(UC_ARM_REG_CONTROL)
        handler = bool(xpsr & 0x1FF)
        on_psp = not handler and bool(control & 2)
        sp = self.r(UC_ARM_REG_SP)
        align = sp & 4
        sp = (sp - 0x20) & ~7
        frame = [self.r(x) for x in FRAME] + [self.r(UC_ARM_REG_PC),
                                              xpsr | (0x200 if align else 0)]
        uc.mem_write(sp, struct.pack("<8I", *frame))
        if on_psp:
            self.w(UC_ARM_REG_CONTROL, control & ~2)
            self.w(UC_ARM_REG_PSP, sp)
        else:
            self.w(UC_ARM_REG_SP, sp)
        self.w(UC_ARM_REG_XPSR, 0x01000000 | exc)
        self.w(UC_ARM_REG_LR, 0xFFFFFFF1 if handler else 0xFFFFFFFD if on_psp else 0xFFFFFFF9)
        self.active.append(exc)
        self.w(UC_ARM_REG_PC, self.rd32(self.vectors + 4 * exc))

    def _return(self):
        uc = self.uc
        exc_return = self.r(UC_ARM_REG_PC) & 0xF | 1
        if self.active:
            self.active.pop()
        to_psp = exc_return == 0xD
        sp = self.r(UC_ARM_REG_PSP) if to_psp else self.r(UC_ARM_REG_SP)
        r0, r1, r2, r3, r12, lr, pc, xpsr = struct.unpack("<8I", uc.mem_read(sp, 0x20))
        sp += 0x20 + (4 if xpsr & 0x200 else 0)
        for reg, v in zip(FRAME, (r0, r1, r2, r3, r12, lr)):
            self.w(reg, v)
        if exc_return == 1:
            self.w(UC_ARM_REG_SP, sp)
            self.w(UC_ARM_REG_XPSR, xpsr & ~0x200 | 0x01000000)
        else:
            if to_psp:
                self.w(UC_ARM_REG_PSP, sp)
            else:
                self.w(UC_ARM_REG_SP, sp)
            self.w(UC_ARM_REG_XPSR, xpsr & 0xFE0FFC00 & ~0x200 | 0x01000000)
            control = self.r(UC_ARM_REG_CONTROL)
            self.w(UC_ARM_REG_CONTROL, control | 2 if to_psp else control & ~2)
        self.w(UC_ARM_REG_PC, pc)

    # ---- run loop
    def run(self, max_insns=5_000_000, until=None):
        """Run until the budget, a fault, or until() is true (checked between slices). Returns
        "budget", "fault" (see .fault; includes a register polled stall_limit times), "until",
        "halt", "reset", or "idle" (WFI with no interrupt source left that could wake the core)."""
        uc = self.uc
        budget = max_insns
        start = self.cycles
        while self.cycles - start < budget:
            self._stop = None
            pc = self.r(UC_ARM_REG_PC)
            try:
                uc.emu_start(pc | 1, 0xFFFFFFFE, count=min(200_000, budget))
            except UcError as e:
                if self._stop not in ("exception", "return"):
                    self.fault = self.fault or f"{e} at pc={self.r(UC_ARM_REG_PC):#x} lr={self.r(UC_ARM_REG_LR):#x}"
                    return "fault"
            if self._stop == "return":
                self._return()
            elif self._stop in ("fault", "reset", "halt", "idle"):
                return self._stop
            if self.fault:
                return "fault"
            exc = self._deliverable() if self.pending else None
            if exc is not None:
                self._enter(exc)
            if until and until():
                return "until"
        return "budget"
