#!/usr/bin/env python3
"""Check in Unicorn that FIRM still finds SENC, TONE and EQ2P after they move. Offline only.

    pip install unicorn capstone
    python3 tools/emu/repart_check.py firmware/h3promax3/h3promax3_2607061716_live.up [other.up ...]

The first image is the reference (stock). Each image is also checked in a built-in "shuffled"
layout made from the reference: EQ2P, SENC, TONE in that order, TONE grown, so every movable
partition lands at a new address. For each image this:

  1. boots FIRM through h3emu into `task main` and records every flash access that lands in the
     movable span (ROM flash_read, memcpy from XIP, direct XIP loads) and every partition lookup
     (FUN_00805444) with its result,
  2. maps each access to (partition, offset) through that image's own index and requires the same
     sequence, the same bytes and the same peripheral register writes as the reference,
  3. calls FIRM's two TONE readers for every prompt on the booted state: FUN_00c6f9b8 (name ->
     prompt number) and FUN_00c6fa38 (number -> flash address, length), and checks them against
     tone_tool's directory and the prompt bytes.

An access outside every partition, or at a stock address in a moved image, fails the check.
"""
import argparse
import struct
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from unicorn import UC_HOOK_BLOCK, UC_HOOK_CODE, UC_HOOK_MEM_READ, UcError
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP

from emu.h3emu import FLASH, Emu
from tone_tool import TONE_DATA_START, read_dir
from upfmt import BODY, MAGIC, crc16, index_offset, ota_image_problems, parse_index

LOOKUP, TONE_FIND, TONE_LOCATE = 0x805444, 0xC6F9B8, 0xC6FA38
MOVABLE = [b"SENC", b"TONE", b"EQ2P"]
SENT, STACK, SCRATCH = 0x7F000, 0x8F8000, 0x8FC000


def parts_of(flash):
    return {t: (a, n) for t, a, n, _ in parse_index(flash)[1]}


def shuffled(data, order=(b"EQ2P", b"SENC", b"TONE"), tone_len=0x1E000):
    """Same partitions, new addresses: EQ2P first, a spare page, then SENC, TONE (grown)."""
    body = bytearray(data[BODY:])
    io = index_offset(body)
    _, entries = parse_index(body, io)
    p = {t: [a, n] for t, a, n, _ in entries}
    blobs = {t: bytes(body[p[t][0]:p[t][0] + p[t][1]]) for t in MOVABLE}
    blobs[b"TONE"] = blobs[b"TONE"].ljust(tone_len, b"\0")
    lo = (p[b"FIRM"][0] + p[b"FIRM"][1] + 0xFFF) & ~0xFFF
    body[lo:p[b"OTAP"][0]] = bytes(p[b"OTAP"][0] - lo)
    cur = lo
    for k, t in enumerate(order):
        p[t] = [cur, len(blobs[t])]
        body[cur:cur + len(blobs[t])] = blobs[t]
        cur = (cur + len(blobs[t]) + 0xFFF) & ~0xFFF
        cur += 0x1000 if k == 0 else 0
    assert cur <= p[b"OTAP"][0], hex(cur)
    for k, (t, *_r) in enumerate(entries):
        if t in MOVABLE:
            struct.pack_into("<4sIII", body, io + 16 + 16 * k, t, *p[t], crc16(blobs[t]))
    hdr = bytearray(data[:BODY])
    struct.pack_into("<I", hdr, 0x10, len(body))
    struct.pack_into("<H", hdr, 0x14, crc16(body))
    out = bytes(hdr) + bytes(body)
    bad = ota_image_problems(out)
    assert not bad, bad
    return out


class Probe(Emu):
    def build(self):
        super().build()
        p = parts_of(self.flash)
        self.span = (min(p[t][0] for t in MOVABLE), max(p[t][0] + p[t][1] for t in MOVABLE))
        self.lo = min(self.span[0], 0xAE000)
        self.hi = p[b"OTAP"][0]
        self.accesses, self.lookups, self.pending = [], [], None
        self.uc.hook_add(UC_HOOK_CODE, self.on_lookup, begin=LOOKUP, end=LOOKUP)
        self.uc.hook_add(UC_HOOK_BLOCK, self.on_ret)
        self.uc.hook_add(UC_HOOK_MEM_READ, self.on_xip, begin=FLASH + self.lo, end=FLASH + self.hi - 1)

    def on_lookup(self, uc, addr, size, _):
        tag = bytes(uc.mem_read(self.r(UC_ARM_REG_R0), 4))
        self.pending = (self.r(UC_ARM_REG_LR) & ~1, tag, self.r(UC_ARM_REG_R1))

    def on_ret(self, uc, addr, size, _):
        if self.pending and addr == self.pending[0]:
            _, tag, lenp = self.pending
            self.pending = None
            ln = struct.unpack("<I", uc.mem_read(lenp, 4))[0] if lenp else None
            self.lookups.append((tag, self.r(UC_ARM_REG_R0), ln))

    def record(self, kind, off, n):
        if self.lo <= off < self.hi and n:
            self.accesses.append((kind, off, n, self.flash[off:off + n]))

    def on_xip(self, uc, access, addr, size, value, _):
        self.record("xip", addr - FLASH, size)

    def on_rom(self, uc, addr, size, _):
        r0, r1, r2 = (self.r(x) for x in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
        if addr == 0x83B4:
            off = r1 & 0xFFFFFF
            self.record("flash_read", off - FLASH if off >= FLASH else off, r2)
        elif addr == 0xB2A and FLASH <= r1 < FLASH + 0x100000:
            self.record("memcpy", r1 - FLASH, r2)
        super().on_rom(uc, addr, size, _)

    def call(self, fn, *regs):
        uc = self.uc
        for i, v in enumerate(regs):
            uc.reg_write(UC_ARM_REG_R0 + i, v)
        uc.reg_write(UC_ARM_REG_SP, STACK)
        uc.reg_write(UC_ARM_REG_LR, SENT | 1)
        uc.emu_start(fn | 1, SENT, count=2_000_000)
        return self.r(UC_ARM_REG_R0)


def boot(flash, insns):
    args = SimpleNamespace(set=[], watch=[], verbose=False, unstick=True, run_task="task main",
                           call=None, max_insns=insns, cpu="m4", poke=[], reg=[], peek=[])
    e = Probe(flash, args)
    try:
        e.uc.emu_start(e.entry | 1, 0, count=insns)
    except UcError as err:
        e.fault = str(err)
    else:
        e.fault = None
    return e


def rel(flash, off):
    for t, (a, n) in parts_of(flash).items():
        if a <= off < a + n:
            return t.decode(), off - a
    return None, off


def tone_check(e, flash):
    a, n = parts_of(flash)[b"TONE"]
    tone = flash[a:a + n]
    errs = []
    for i, (name, size, doff) in enumerate(read_dir(tone)):
        e.uc.mem_write(SCRATCH, name.encode("latin1") + b"\0")
        e.uc.mem_write(SCRATCH + 0x40, b"\xee")
        found = e.call(TONE_FIND, SCRATCH, SCRATCH + 0x40)
        idx = e.uc.mem_read(SCRATCH + 0x40, 1)[0]
        e.uc.mem_write(SCRATCH + 0x80, bytes(8))
        e.call(TONE_LOCATE, 0, i, SCRATCH + 0x80, SCRATCH + 0x84)
        addr, ln = struct.unpack("<II", e.uc.mem_read(SCRATCH + 0x80, 8))
        want = a + doff
        got = addr - FLASH if addr >= FLASH else addr
        ok = found == 1 and idx == i and got == want and ln == size and flash[got:got + ln] == tone[doff:doff + size]
        if not ok:
            errs.append(f"{name}: find={found} idx={idx} (want {i}) addr={addr:#x} (want {want:#x}) len={ln} (want {size})")
    return len(read_dir(tone)), errs


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("images", nargs="+")
    ap.add_argument("--max-insns", type=int, default=5_000_000)
    a = ap.parse_args()
    raw = [Path(p).read_bytes() for p in a.images]
    for p, d in zip(a.images, raw):
        if d[:6] != MAGIC:
            sys.exit(f"{p}: not a .up")
    cases = list(zip(a.images, raw)) + [("<shuffled reference>", shuffled(raw[0]))]

    ref = None
    failed = False
    for name, data in cases:
        flash = data[BODY:]
        e = boot(flash, a.max_insns)
        layout = "  ".join(f"{t.decode()}@{x:#x}+{n:#x}" for t, (x, n) in parts_of(flash).items() if t in MOVABLE)
        seq = [(k, *rel(flash, off), n, blob) for k, off, n, blob in e.accesses]
        mmio = {k: (v["w"], v["last_w"]) for k, v in e.mmio.items() if v["w"]}
        looks = [(t.decode(), rel(flash, x - FLASH if x >= FLASH else x), n) for t, x, n in e.lookups]
        blocks = e.count()
        ntone, terrs = tone_check(e, flash)
        errs = [f"access outside any partition: {k} {off:#x}+{n}" for k, t, off, n, _ in seq if t is None]
        errs += terrs
        if e.fault:
            errs.append(f"CPU fault during boot: {e.fault}")
        if ref is None:
            ref = (seq, mmio, looks, blocks)
            if not any(t == "SENC" for _, t, *_r in seq) or not any(t == "EQ2P" for _, t, *_r in seq):
                errs.append("reference boot never read SENC and EQ2P; raise --max-insns")
        else:
            rseq, rmmio, rlooks, rblocks = ref
            if [s[:5] for s in seq] != [s[:5] for s in rseq]:
                diff = next(i for i, (x, y) in enumerate(zip(seq + [None], rseq + [None])) if x != y)
                errs.append(f"flash access #{diff} differs: {seq[diff][:4] if diff < len(seq) else None} vs stock "
                            f"{rseq[diff][:4] if diff < len(rseq) else None}")
            if looks != rlooks:
                errs.append(f"lookups differ: {looks} vs stock {rlooks}")
            if mmio != rmmio:
                bad = sorted(set(mmio.items()) ^ set(rmmio.items()))[:6]
                errs.append(f"peripheral writes differ: {bad}")
            if blocks != rblocks:
                errs.append(f"blocks executed {blocks} vs stock {rblocks}")
        failed |= bool(errs)
        print(f"{'FAIL' if errs else 'ok  '}  {name}\n      {layout}")
        print(f"      boot: {blocks:,} blocks, {len(seq)} flash accesses in span, lookups "
              + ", ".join(f"{t}->{r[0]}+{r[1]:#x} len {n:#x}" for t, r, n in looks))
        print(f"      TONE readers: {ntone - len(terrs)}/{ntone} prompts resolved to the right bytes")
        for m in errs:
            print("      !", m)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
