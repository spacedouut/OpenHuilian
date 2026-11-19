#!/usr/bin/env python3
"""Run the OTAP updater in Unicorn and flash an image into an emulated bud with hl's own OTA code. Offline only.

    pip install unicorn capstone
    python3 tools/emu/otap_check.py firmware/h3promax3/h3promax3_2607061716_live.up new.up

The first image is what the emulated bud holds before the update; its OTAP partition is the
updater that runs (loaded at 0x804800, the way BOOT starts it with the 0x55AA flag set). The
OTAP code that runs unmodified: the 55AA byte parser FUN_00805e54 (CRC8, length cap), the frame
handler FUN_0080e770 (80/81/82/83/84/04), the 82 erase planner, the 83 page writer, the index
save/restore and OTAP/PSMP record pinning, the CRC16 over 0x3000..0x3000+total, the bootloader
guard CRC and the 04 flag clear. Modelled at the driver boundary: SPI sector/block erase
(FUN_0082bc40) and page program (FUN_0082bbd4) act on a 1 MB NOR model (erase -> FF, program
ANDs bits), the ROM flash read and libc routines are emulated, timers/peer relay/reboot are
recorded. The sender is tools/huilian/cli.py `_ota_one_bud`, the routine `hl ota --side one` runs.

Scenarios (each from a fresh copy of the first image's flash):
  update       new image end to end: finalize status 0, flash == image below OTAP, boot area,
               OTAP, flag page (cleared) and PSMP otherwise untouched, erase span = stock's
  rollback     the first image again, onto the updated flash
  crc-fail     one data chunk corrupted in flight (frame CRC8 still valid): status 1, old index
               restored, hl stops before 04, flag stays set; then hl retried with no power cycle,
               and again after a power cycle (OTAP restarted from flash)
  interrupted  link drops halfway through 83; power cycle; hl run again from the start
"""
import argparse
import random
import struct
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from unicorn import (UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_FETCH_UNMAPPED, UC_HOOK_MEM_READ_UNMAPPED,
                     UC_HOOK_MEM_WRITE_UNMAPPED, UC_MEM_FETCH_UNMAPPED, UC_MODE_MCLASS, UC_MODE_THUMB, Uc,
                     UcError)
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
                               UC_ARM_REG_SP, UC_CPU_ARM_CORTEX_M4)

from huilian import cli, proto
from upfmt import BODY, MAGIC, live_index_problems, parse_index

OTAP_RAM, SRAM, SRAM_SZ, HEAP = 0x804800, 0x800000, 0x100000, 0x880000
FLASH_SZ, SENT, RXBUF = 0x100000, 0x7F000, 0x8F0000
PARSE, HANDLE, OTAP_INIT = 0x805E54, 0x80E770, 0x805398
RX_STATE, RESULT = 0x840287, 0x82D13B
ERASE_SIZE = {3: 0x1000, 4: 0x8000, 5: 0x10000, 6: FLASH_SZ}
RET0 = {0x8057C0: "flash_wp", 0x806094: "ms_to_ticks", 0x82C2D8: "timer_create", 0x82C24C: "timer_ctl",
        0x80FBF0: "peer_send"}


def parts_of(flash):
    return {t: (a, n) for t, a, n, _ in parse_index(flash)[1]}


class Bud:
    """One emulated bud in OTAP: flash model + Unicorn running the updater."""

    def __init__(self, flash):
        self.flash = flash
        self.erases, self.programs, self.errors, self.events, self.replies = [], [], [], [], []
        self.rebooted = False
        self.boot()

    def boot(self):
        p = parts_of(self.flash)
        a, n = p[b"OTAP"]
        otap = bytes(self.flash[a + 0x30:a + n])
        uc = self.uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
        uc.ctl_set_cpu_model(UC_CPU_ARM_CORTEX_M4)
        uc.mem_map(0, 0x100000)
        uc.mem_write(0, b"\x70\x47" * 0x80000)
        uc.mem_map(SRAM, SRAM_SZ)
        uc.mem_write(OTAP_RAM, otap)
        self.sp = struct.unpack_from("<I", otap, 0)[0]
        self.heap = HEAP
        uc.hook_add(UC_HOOK_MEM_READ_UNMAPPED | UC_HOOK_MEM_WRITE_UNMAPPED | UC_HOOK_MEM_FETCH_UNMAPPED,
                    self.on_unmapped)
        uc.hook_add(UC_HOOK_CODE, self.on_rom, begin=0, end=0xFFFFF)
        for addr, fn in [(0x82BC40, self.on_erase), (0x82BBD4, self.on_program), (0x80DCF0, self.on_reply),
                         (0x8112A8, self.on_reply), (0x80B060, self.on_reboot)] + \
                        [(x, self.on_stub) for x in RET0]:
            uc.hook_add(UC_HOOK_CODE, fn, begin=addr, end=addr)
        self.call(OTAP_INIT)
        self.rebooted = False

    def r(self, reg):
        return self.uc.reg_read(reg)

    def ret(self, r0=None):
        if r0 is not None:
            self.uc.reg_write(UC_ARM_REG_R0, r0)
        self.uc.reg_write(UC_ARM_REG_PC, self.r(UC_ARM_REG_LR))

    def on_unmapped(self, uc, access, addr, size, value, _):
        if access == UC_MEM_FETCH_UNMAPPED:
            return False
        uc.mem_map(addr & ~0xFFF, 0x1000)
        return True

    def on_rom(self, uc, addr, size, _):
        r0, r1, r2 = (self.r(x) for x in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
        if addr == 0x83B4:
            off = r1 & 0xFFFFFF
            uc.mem_write(r0, bytes(self.flash[off:off + r2]).ljust(r2, b"\xff")) if r2 else None
        elif addr == 0xB2A and r2:
            uc.mem_write(r0, bytes(uc.mem_read(r1, r2)))
        elif addr == 0xBAA and r2:
            uc.mem_write(r0, bytes([r1 & 0xFF]) * r2)
        elif addr in (0xC54, 0xAB2):
            n = r2 if addr == 0xC54 else 64
            x, y = bytes(uc.mem_read(r0, n)), bytes(uc.mem_read(r1, n))
            if addr == 0xAB2:
                x, y = x.split(b"\0")[0], y.split(b"\0")[0]
            uc.reg_write(UC_ARM_REG_R0, ((x > y) - (x < y)) & 0xFFFFFFFF)
        elif addr == 0xC70:
            p, self.heap = self.heap, (self.heap + r0 + 7) & ~7
            uc.reg_write(UC_ARM_REG_R0, p)

    def on_erase(self, uc, addr, size, _):
        cmd, at = self.r(UC_ARM_REG_R0), self.r(UC_ARM_REG_R1)
        n = ERASE_SIZE.get(cmd)
        if n is None:
            self.errors.append(f"unknown erase command {cmd} at {at:#x}")
        else:
            lo = at & ~(n - 1)
            self.flash[lo:lo + n] = b"\xff" * n
            self.erases.append((lo, n))
        self.ret(0)

    def on_program(self, uc, addr, size, _):
        src, at, n = (self.r(x) for x in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
        data = bytes(uc.mem_read(src, n))
        if (at & 0xFF) + n > 0x100:
            self.errors.append(f"page program crosses a 256 B page: {at:#x}+{n:#x}")
        old = self.flash[at:at + n]
        if any(d & ~o & 0xFF for d, o in zip(data, old)):
            self.errors.append(f"program onto non-erased flash at {at:#x}+{n:#x}")
        self.flash[at:at + n] = bytes(d & o for d, o in zip(data, old))
        self.programs.append((at, n))
        self.ret(0)

    def on_reply(self, uc, addr, size, _):
        buf, n = self.r(UC_ARM_REG_R0), self.r(UC_ARM_REG_R1)
        self.replies.append(bytes(uc.mem_read(buf, n & 0xFFFF)))
        self.ret(0)

    def on_reboot(self, uc, addr, size, _):
        self.rebooted = True
        self.events.append("reboot (FUN_0080b060)")
        uc.emu_stop()

    def on_stub(self, uc, addr, size, _):
        if addr != 0x806094:
            self.events.append(RET0[addr])
            self.ret(0)
        else:
            self.ret()

    def call(self, fn, *args):
        uc = self.uc
        for i, v in enumerate(args):
            uc.reg_write(UC_ARM_REG_R0 + i, v)
        uc.reg_write(UC_ARM_REG_SP, self.sp)
        uc.reg_write(UC_ARM_REG_LR, SENT | 1)
        try:
            uc.emu_start(fn | 1, SENT, count=400_000_000)
        except UcError as e:
            self.errors.append(f"CPU fault in {fn:#x}: {e} at pc={self.r(UC_ARM_REG_PC):#x}")
            return None
        if self.r(UC_ARM_REG_PC) != SENT and not self.rebooted:
            self.errors.append(f"{fn:#x} did not return (pc={self.r(UC_ARM_REG_PC):#x})")
        return self.r(UC_ARM_REG_R0)

    def receive(self, data):
        """RFCOMM bytes in: OTAP's parser, then its handler once a frame is complete."""
        self.uc.mem_write(RXBUF, data)
        self.call(PARSE, RXBUF, len(data))
        if self.uc.mem_read(RX_STATE, 1)[0] == 8:
            self.call(HANDLE)


class FakeLink:
    """What hl's link layer talks to: bytes go into the emulated OTAP, replies come back."""

    def __init__(self, bud, tamper=None, drop_after=None):
        self.bud, self.rx, self.tamper, self.drop_after, self.writes = bud, bytearray(), tamper, drop_after, 0

    @property
    def in_waiting(self):
        return len(self.rx)

    def write(self, data):
        if data[:2] != b"\x55\xaa":
            return len(data)          # C0 commands: FIRM-only probes; OTAP doesn't answer 0A
        if data[2] == 0x83:
            self.writes += 1
            if self.drop_after is not None and self.writes > self.drop_after:
                raise OSError("link dropped (simulated)")
            if self.tamper and self.tamper(self.writes, data):
                body = bytearray(data[:-1])
                body[13 + 100] ^= 0x01
                data = bytes(body) + bytes([proto.crc8(bytes(body))])
        n = len(self.bud.replies)
        self.bud.receive(data)
        for rep in self.bud.replies[n:]:
            self.rx += rep
        return len(data)

    def read(self, n=1):
        out = bytes(self.rx[:n])
        del self.rx[:n]
        return out

    def close(self):
        pass


def send(bud, image, **kw):
    """hl ota's one-bud routine against the emulated bud. Returns (exit message or None, link)."""
    payload, fw_addr, index, io, declared, _last, parts = cli._up_payloads(image)
    bad = live_index_problems(bytes(bud.flash[0x3000:0x3000 + 0x100]), parts)
    if bad:
        return "live index check: " + "; ".join(bad), None
    ser = FakeLink(bud, **kw)
    a = SimpleNamespace(timeout=3.0, resume=False, port="emu", baud=0)
    try:
        cli._ota_one_bud(ser, a, payload, fw_addr, index, io, declared)
    except SystemExit as e:
        return str(e.code), ser
    except OSError as e:
        return f"OSError: {e}", ser
    return None, ser


def flag_word(flash):
    a, n = parts_of(flash)[b"OTAP"]
    at = a + ((n >> 12) + 1) * 0x1000
    return at, struct.unpack_from("<I", flash, at)[0]


def check_written(bud, before, image_flash, label):
    """Flash after a completed update must be the image below OTAP and untouched elsewhere."""
    errs = list(bud.errors)
    f = bud.flash
    otap_a = parts_of(before)[b"OTAP"][0]
    if f[:0x3000] != before[:0x3000]:
        errs.append("bootloader/config area 0x0..0x3000 changed")
    if f[0x3000:otap_a] != image_flash[0x3000:otap_a]:
        first = next(i for i in range(0x3000, otap_a) if f[i] != image_flash[i])
        errs.append(f"flash differs from the image at {first:#x}")
    fa, fw = flag_word(before)
    rest_before = bytearray(before[otap_a:])
    rest_before[fa - otap_a:fa - otap_a + 4] = b"\0\0\0\0"
    flag_page = slice(fa - otap_a, fa - otap_a + 0x1000)
    rb, ra = bytearray(rest_before), bytearray(f[otap_a:])
    rb[flag_page] = ra[flag_page] = b""
    if rb != ra:
        errs.append("OTAP, PSMP or the gap after OTAP changed")
    if f[fa:fa + 4] != b"\0\0\0\0":
        errs.append(f"OTA flag at {fa:#x} not cleared: {f[fa:fa + 4].hex()}")
    if not bud.rebooted:
        errs.append("04 did not reboot")
    lo = min(a for a, n in bud.erases if a >= 0x4000 and a < fa)
    hi = max(a + n for a, n in bud.erases if a >= 0x4000 and a < fa)
    print(f"  {label}: 82 erased {lo:#x}..{hi:#x}, 83 programmed {len(bud.programs)} pages, "
          f"index page 0x3000 rewritten, flag {fa:#x} {fw:#010x} -> {struct.unpack_from('<I', f, fa)[0]:#x}")
    if (lo, hi) != (0x4000, otap_a):
        errs.append(f"erase span {lo:#x}..{hi:#x}, expected 0x4000..{otap_a:#x}")
    return errs


def load(path):
    data = Path(path).read_bytes()
    if data[:6] != MAGIC:
        sys.exit(f"{path}: not a .up")
    return data


def initial_flash(stock):
    """The bud before the update: the stock image, PSMP filled with stand-in settings bytes,
    the 0x55AA flag set (FIRM sets it on 80, BOOT then starts OTAP)."""
    body = stock[BODY:]
    f = bytearray(body[:FLASH_SZ].ljust(FLASH_SZ, b"\xff"))
    a, n = parts_of(f)[b"PSMP"]
    f[a:a + n] = random.Random(0x5053).randbytes(n)
    fa, _ = flag_word(f)
    f[fa:fa + 4] = b"\xaa\x55\x00\x00"
    return f


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("stock")
    ap.add_argument("image")
    a = ap.parse_args()
    stock, new = load(a.stock), load(a.image)
    cli.time.sleep = lambda s: None
    cli.print = lambda *x, **k: None
    new_flash = bytearray(new[BODY:].ljust(FLASH_SZ, b"\xff"))
    stock_flash = bytearray(stock[BODY:].ljust(FLASH_SZ, b"\xff"))
    failed = False

    def report(name, errs):
        nonlocal failed
        failed |= bool(errs)
        print(f"{'FAIL' if errs else 'ok  '} {name}")
        for e in errs:
            print("      ", e)

    t0 = time.time()
    before = initial_flash(stock)
    bud = Bud(bytearray(before))
    msg, _ = send(bud, a.image)
    errs = ([f"hl stopped: {msg}"] if msg else []) + check_written(bud, before, new_flash, "update")
    report(f"update {Path(a.image).name} onto {Path(a.stock).name} ({time.time() - t0:.0f}s)", errs)
    updated = bytearray(bud.flash)

    before2 = bytearray(updated)
    fa, _ = flag_word(before2)
    before2[fa:fa + 4] = b"\xaa\x55\x00\x00"
    bud = Bud(bytearray(before2))
    msg, _ = send(bud, a.stock)
    errs = ([f"hl stopped: {msg}"] if msg else []) + check_written(bud, before2, stock_flash, "rollback")
    report(f"rollback to {Path(a.stock).name} from the updated flash", errs)

    before = initial_flash(stock)
    bud = Bud(bytearray(before))
    msg, _ = send(bud, a.image, tamper=lambda k, d: k == 200)
    errs = list(bud.errors)
    res = bud.uc.mem_read(RESULT, 1)[0]
    fa, _ = flag_word(before)
    if not msg or "CRC mismatch" not in msg:
        errs.append(f"expected hl to stop on finalize status 1, got: {msg}")
    if res != 1:
        errs.append(f"OTAP result byte {res}, expected 1")
    if bud.flash[0x3000:0x4000] != before[0x3000:0x4000]:
        errs.append("old index not restored at 0x3000")
    if bud.flash[fa:fa + 4] != b"\xaa\x55\x00\x00":
        errs.append("flag cleared after a failed CRC")
    if bud.rebooted:
        errs.append("rebooted after a failed CRC")
    firm_a, firm_n = parts_of(before)[b"FIRM"]
    print(f"  crc-fail: hl: {msg.splitlines()[0] if msg else None}")
    print(f"  crc-fail: index at 0x3000 = old index: {bud.flash[0x3000:0x4000] == before[0x3000:0x4000]}; "
          f"flag {bud.flash[fa:fa + 4].hex()}; FIRM bytes equal to stock: "
          f"{bud.flash[firm_a:firm_a + firm_n] == before[firm_a:firm_a + firm_n]}")
    report("crc-fail: corrupted chunk #200 -> status 1, old index back, no 04, flag still set", errs)

    failed_state = bytearray(bud.flash)
    bud.errors.clear()
    bud.erases.clear()
    bud.programs.clear()
    msg, _ = send(bud, a.image)
    errs = ([f"hl stopped: {msg}"] if msg else []) + check_written(bud, failed_state, new_flash, "retry")
    report("crc-fail retry, same OTAP session (no power cycle)", errs)

    bud = Bud(bytearray(failed_state))
    msg, _ = send(bud, a.image)
    errs = ([f"hl stopped: {msg}"] if msg else []) + check_written(bud, failed_state, new_flash, "retry")
    report("crc-fail retry after a power cycle (OTAP restarted from flash)", errs)

    before = initial_flash(stock)
    bud = Bud(bytearray(before))
    msg, _ = send(bud, a.image, drop_after=200)
    errs = list(bud.errors)
    fa, _ = flag_word(before)
    if bud.flash[fa:fa + 4] != b"\xaa\x55\x00\x00":
        errs.append("flag not set after an interrupted transfer")
    if bud.flash[0x3000:0x4000] != before[0x3000:0x4000]:
        errs.append("index page changed by an interrupted transfer")
    cut = bytearray(bud.flash)
    bud = Bud(bytearray(cut))
    msg2, _ = send(bud, a.image)
    errs += ([f"hl stopped: {msg2}"] if msg2 else []) + check_written(bud, cut, new_flash, "resume")
    report(f"interrupted after 200 chunks ({msg}), power cycle, hl run again", errs)
    print(f"total {time.time() - t0:.0f}s")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
