"""Peripheral models for the Huilian 377H3, as far as stock firmware shows how each one behaves."""
import collections

from openhuilian.emu.machine import Peripheral
from openhuilian.format.upfmt import crc16


class Pmu(Peripheral):
    """Power management block at 0x40085000 with its indirect register bus. IRQ 48 is its
    wake-up interrupt, the only one left enabled when the idle task sleeps in WFI.

    +0x98 power-domain handshake: bit 31 busy, request bit 19 is acknowledged in bit 29 and
    request bit 16 in bit 25 (firmware waits for each to follow). +0x84 is the measured
    frequency of the low-power oscillator in Hz (0 until measured; firmware divides 1e6 by it
    to size sleep timings), assumed to be a nominal 32.768 kHz here. +0xC0/+0xD0 switch a
    supply rail to a new voltage: firmware sets +0xD0 bit 3, waits for bit 1, sets bit 2 and
    waits for bit 1 to drop.
    +0x100 control (bit 31 = soft reset, self-clearing), +0x104 command: bit 31 starts a transfer
    and reads 0 when it finished, bits 8-15 register index, bits 0-7 the address byte on the wire
    (0x60 write / 0x61 read = 7-bit device 0x30), +0x108 write data, +0x10C read data,
    +0x110 status (0xF000 = error, e.g. no ACK).
    """
    base, name = 0x40085000, "pmu"
    slow_clock_hz = 32768

    def __init__(self, machine):
        super().__init__(machine)
        self.devices = collections.defaultdict(dict)   # 7-bit address -> {register: value}
        self.present = {0x30}
        self.rail_ready = False
        self.log = []

    def write(self, off, value, size):
        if off == 0x100:
            value &= ~0x80000000
        elif off == 0xD0:       # bits 3 and 2 are strobes: start the hand-over, acknowledge it
            if value & 8:
                self.rail_ready = True
            if value & 4:
                self.rail_ready = False
            value &= ~0xC
        elif off == 0x104 and value >> 31:
            dev, read, reg = (value & 0xFF) >> 1, value & 1, value >> 8 & 0xFF
            status = 0
            if dev not in self.present:
                status = 0x1000
            elif read:
                self.regs[0x10C] = self.devices[dev].get(reg, 0)
            else:
                self.devices[dev][reg] = self.regs.get(0x108, 0) & 0xFF
            self.regs[0x110] = status
            self.log.append((self.m.cycles, dev, "r" if read else "w", reg,
                             self.regs.get(0x10C if read else 0x108, 0) & 0xFF, status))
            value &= ~0x80000000
        self.regs[off] = value

    def read(self, off, size):
        v = self.regs.get(off, 0)
        if off == 0x84:
            return self.slow_clock_hz
        if off == 0xD0:
            return v & ~2 | (2 if self.rail_ready else 0)
        if off == 0x98:
            v = v & ~0xA2000000 | (v >> 19 & 1) << 29 | (v >> 16 & 1) << 25
        return v


class Clocks(Peripheral):
    """Clock controller at 0x40080000. +0x00, +0x08, +0x10: one PLL each, bits 30-31 enable,
    bit 28 = locked (code sets the enables and waits for it). The clock-enable words at
    +0x60..0x78 read back what was written."""
    base, name = 0x40080000, "clocks"

    def read(self, off, size):
        v = self.regs.get(off, 0)
        if off in (0x00, 0x08, 0x10):
            v = v & ~0x10000000 | (v >> 30 & 1) << 28
        return v


class FlashController(Peripheral):
    """SPI NOR controller at 0x30000000 with the flash chip behind it.

    +0x10 command: bit 31 starts it, bits 0-7 are the SPI opcode; +0x14 length - 1; +0x18 flash
    address; +0x1C RAM buffer the controller reads from or fills; +0x0C status, bit 1 = done
    (write 1 to clear). IRQ 50 fires on completion. +0x100..0x118 configure the XIP cache
    regions; +0x11C flushes one (write 1, reads 0 when done). +0x60 bit 0 enables the
    CRC unit (CRC-16/CCITT-FALSE over the bytes read), +0x64 seeds it, +0x6C is the result; the
    ROM uses it to check the flash header and BOOT. The chip follows the common 25-series command
    set: erase sets FF, page program only clears bits and wraps inside its 256 B page, both need
    a write-enable first, and the busy bit is visible for a few status reads afterwards.
    """
    base, name, irqs = 0x30000000, "flash", (25, 50)
    ERASE = {0x20: 0x1000, 0x52: 0x8000, 0xD8: 0x10000}
    READ = {0x03, 0x0B, 0x3B, 0x6B, 0xBB, 0xEB}
    PROGRAM = {0x02, 0x32}

    def __init__(self, machine):
        super().__init__(machine)
        self.jedec = bytes.fromhex("856014")     # 1 MB 25-series part
        self.status = [0, 0x02]                  # SR1, SR2 (QE set, as BOOT leaves it)
        self.busy_reads = 0
        self.log, self.errors = [], []

    def write(self, off, value, size):
        if off == 0x0C:
            self.regs[off] = self.regs.get(off, 0) & ~value
            return
        if off == 0x11C:
            value = 0
        elif off == 0x64:
            self.regs[0x6C] = value & 0xFFFF
        self.regs[off] = value
        if off == 0x10 and value >> 31:
            self.command(value)
            self.regs[off] = value & ~0x80000000
            self.regs[0x0C] = self.regs.get(0x0C, 0) | 2
            for n in self.irqs:
                if 16 + n in self.m.enabled:
                    self.m.raise_irq(n)

    def command(self, word):
        m, op = self.m, word & 0xFF
        n, addr, buf = self.regs.get(0x14, 0) + 1, self.regs.get(0x18, 0), self.regs.get(0x1C, 0)
        flash_size = len(m.flash)
        self.log.append((m.cycles, op, addr, n, m.pc))
        wel = self.status[0] & 2
        if op == 0x9F:
            m.uc.mem_write(buf, (self.jedec * 2)[:n])
        elif op in (0x05, 0x35):
            sr = self.status[op == 0x35]
            if op == 0x05 and self.busy_reads:
                self.busy_reads -= 1
                sr |= 1
            m.uc.mem_write(buf, bytes([sr]) * n)
        elif op in (0x06, 0x50):
            self.status[0] |= 2
        elif op == 0x04:
            self.status[0] &= ~2
        elif op in (0x01, 0x31):
            data = bytes(m.uc.mem_read(buf, n))
            if op == 0x31:
                self.status[1] = data[0]
            else:
                self.status[0] = data[0] & 0xFC
                if n > 1:
                    self.status[1] = data[1]
        elif op in self.READ:
            addr %= flash_size
            data = bytes(m.flash[addr:addr + n]).ljust(n, b"\xff")
            m.uc.mem_write(buf, data)
            if self.regs.get(0x60, 0) & 1:      # CRC unit runs over everything read
                self.regs[0x6C] = crc16(data, self.regs.get(0x6C, 0xFFFF))
        elif op in self.ERASE or op in self.PROGRAM:
            addr %= flash_size
            if not wel:
                self.errors.append(f"opcode {op:#x} at {addr:#x} without write enable: ignored")
                return
            self.status[0] &= ~2
            self.busy_reads = 2
            if op in self.ERASE:
                size = self.ERASE[op]
                m.flash_erase(addr & ~(size - 1), size)
            else:
                data = bytes(m.uc.mem_read(buf, n))
                page = addr & ~0xFF
                if (addr & 0xFF) + n > 0x100:
                    self.errors.append(f"page program {addr:#x}+{n:#x} wraps in its 256 B page")
                for i, b in enumerate(data):       # one byte at a time so the wrap is real
                    m.flash_program(page | (addr + i) & 0xFF, bytes([b]), quiet=True)
                m.flash_ops.append(("program", addr, n, m.pc))
        elif op in (0x66, 0x99, 0xAB, 0xB9, 0x38, 0xFF, 0x75, 0x7A):
            pass                                    # reset, power-down, suspend/resume: no state
        else:
            self.errors.append(f"unmodelled SPI opcode {op:#x} (addr {addr:#x}, {n} B)")


class MicrosecondTimer(Peripheral):
    """Free-running 64-bit microsecond counter at 0x40082100 (+4 low word, +8 high word).

    The ROM delay and timeout routines spin on it. A long run of reads with no register write
    and no exception in between is a busy-wait, so each further read moves time on by `warp_us`
    instead of a few instructions.
    """
    base, name, warp_us = 0x40082000, "ustimer", 25

    def __init__(self, machine):
        super().__init__(machine)
        self.streak = 0
        self.mmio_seen = 0

    def read(self, off, size):
        m = self.m
        if off in (0x104, 0x108):
            self.streak = self.streak + 1 if m.activity == self.mmio_seen else 0
            self.mmio_seen = m.activity
            if self.streak > 64:
                m.cycles += self.warp_us * m.cpu_hz // 1_000_000
            us = m.cycles * 1_000_000 // m.cpu_hz
            return us & 0xFFFFFFFF if off == 0x104 else us >> 32
        return self.regs.get(off, 0)


class I2CMaster(Peripheral):
    """I2C master at 0x40089000 (sensor bus). +0x00 bit 31 soft reset (self-clearing); +0x04
    command: bit 31 go/busy, bit 0 send START + the byte in +0x08 (address << 1 | read), bit 3
    send/receive a data byte, bit 1 STOP; +0x08 TX byte; +0x0C RX byte; +0x10 status, bit 15 =
    NACK (write 1 to clear). No slave is modelled unless one is put in `devices`
    (7-bit address -> object with write(byte) and read() -> byte), so every address NACKs,
    which is what the firmware sees with the sensor absent. `log` keeps (address byte, acked)."""
    base, name = 0x40089000, "i2c"

    def __init__(self, machine):
        super().__init__(machine)
        self.devices, self.log, self.cur = {}, [], None

    def read(self, off, size):
        if off == 0x0C and self.cur is not None:
            return self.cur.read() & 0xFF
        return self.regs.get(off, 0)

    def write(self, off, value, size):
        if off == 0x00:
            value &= ~0x80000000
        elif off == 0x10:
            value = self.regs.get(off, 0) & ~value
        elif off == 0x04 and value >> 31:
            tx = self.regs.get(0x08, 0) & 0xFF
            if value & 1:
                self.cur = self.devices.get(tx >> 1)
                self.log.append((tx, self.cur is not None))
                if self.cur is None:
                    self.regs[0x10] = self.regs.get(0x10, 0) | 0x8000
            elif value & 8 and self.cur is not None and hasattr(self.cur, "write"):
                self.cur.write(tx)
            value = 0
        self.regs[off] = value


class System(Peripheral):
    """0x40000000. +0x100 receives a boot stage number (write-only progress marker); kept in
    `stages` and noted in the machine's event log."""
    base, name = 0x40000000, "system"

    def __init__(self, machine):
        super().__init__(machine)
        self.stages = []

    def write(self, off, value, size):
        if off == 0x100:
            self.stages.append(value)
            self.m.note(f"boot stage {value:#x}")
        self.regs[off] = value


class Uart(Peripheral):
    """UART at 0x40090000 / 0x40091000 / 0x40092000. +0x00 data, +0x08 status (bit 4 = can send).
    Nothing is connected to RX. Sent bytes are kept in `tx`."""
    name = "uart0"

    def __init__(self, machine):
        super().__init__(machine)
        self.tx = bytearray()

    def read(self, off, size):
        return 0x10 if off == 8 else self.regs.get(off, 0)

    def write(self, off, value, size):
        if off == 0:
            self.tx.append(value & 0xFF)
        self.regs[off] = value


class Uart0(Uart):
    base = 0x40090000


class Uart1(Uart):
    base, name = 0x40091000, "uart1"


class Uart2(Uart):
    base, name = 0x40092000, "uart2"


# Request bits that hardware clears by itself once the request is carried out. The firmware
# writes 1 and spins until it reads 0. Kept as a table because nothing else is known about them.
SELF_CLEARING = {
    0x40003000: 0x00000007,   # card/storage host: controller, FIFO and DMA reset
    0x40003004: 0x80000000,   # card/storage host: command start
    0x40009400: 0x80000000,   # indexed port: go/busy, bits 8-12 bank, bits 0-6 register; +0x404 data
    0x400D0020: 0x80000000,   # 0x400D0000 block (IRQ 36): reset of each of its three channels
    0x400D0040: 0x80000000,
    0x400D0060: 0x80000000,
    0x400D1010: 0x80000000,   # coefficient port: +0x10 go/busy (bit 30 write, low 12 bits index), +0x14/+0x18 data
}


def power_on(flash, rom=None):
    """A reset Machine with every modelled peripheral attached; returns (machine, peripherals)."""
    from openhuilian.emu.machine import Machine
    m = Machine(flash, rom)
    peripherals = attach(m)
    m.reset()
    return m, peripherals


def attach(machine):
    """Add every modelled 377H3 peripheral to a Machine; returns them by name."""
    machine.self_clearing.update(SELF_CLEARING)
    return {p.name: p for p in (machine.add(c) for c in (Pmu, Clocks, FlashController, I2CMaster, MicrosecondTimer, System, Uart0, Uart1, Uart2))}
