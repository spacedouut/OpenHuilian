#!/usr/bin/env python3
"""Run the debug monitor patch through the real C0 handler in Unicorn. Offline only.

    pip install unicorn capstone
    python3 tools/emu/monitor_check.py firmware/h3promax3/h3promax3_2607061716_live.up

Applies patches/2607061716/debug-monitor.json with cfw.py, boots stock and patched FIRM into
`task main`, then feeds request frames into FUN_00c69b3c, the C0 handler whose first
instruction the patch replaces. Replies are captured at FUN_00c69870 (the reply post).
Checks: every monitor command and its error paths; poke/call refused before the C0 01/02
handshake and accepted after the firmware's own handshake code sets the session flag; stock
commands (05 version, 83 flash read, 0A in-ear) answer byte-identically through the hook; the
patched image's boot matches stock (same partition reads, lookups, peripheral writes).
"""
import argparse
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from unicorn import UC_HOOK_CODE, UcError
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

from emu.repart_check import FLASH, SENT, STACK, boot, rel
from huilian import proto
from upfmt import BODY

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / "patches/2607061716/debug-monitor.json"
HANDLER, REPLY = 0xC69B3C, 0xC69870
AUTH = 0x8343E8
FRAME, SCRATCH = 0x8FA000, 0x8FB000


class Bud:
    def __init__(self, flash, insns):
        self.e = boot(flash, insns)
        self.replies = []
        self.e.uc.hook_add(UC_HOOK_CODE, self.on_reply, begin=REPLY, end=REPLY)

    def on_reply(self, uc, addr, size, _):
        buf, n = uc.reg_read(UC_ARM_REG_R0), uc.reg_read(UC_ARM_REG_R1)
        self.replies.append(bytes(uc.mem_read(buf, n & 0xFFFF)))
        uc.reg_write(UC_ARM_REG_R0, 0)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    def send(self, frame):
        uc = self.e.uc
        self.replies = []
        uc.mem_write(FRAME, frame)
        uc.reg_write(UC_ARM_REG_R0, FRAME)
        uc.reg_write(UC_ARM_REG_R1, len(frame))
        uc.reg_write(UC_ARM_REG_SP, STACK)
        uc.reg_write(UC_ARM_REG_LR, SENT | 1)
        uc.emu_start(HANDLER | 1, SENT, count=3_000_000)
        return self.replies

    def mon(self, cmd, payload=b""):
        r = self.send(bytes([0xC0, cmd]) + payload)
        if len(r) != 1:
            raise AssertionError(f"C0 {cmd:02X}: {len(r)} replies")
        r = r[0]
        assert r[:2] == bytes([0xC0, cmd]) and r[2] == len(r) - 3, r.hex()
        return r[3], r[4:]


class EmuLink:
    """pyserial-like object that hands each write to the emulated C0 handler."""

    def __init__(self, bud):
        self.bud, self.rx = bud, bytearray()

    @property
    def in_waiting(self):
        return len(self.rx)

    def write(self, frame):
        for r in self.bud.send(bytes(frame)):
            self.rx += r

    def read(self, n=1):
        out = bytes(self.rx[:n])
        del self.rx[:n]
        return out


def hl_check(bud, flash, fails):
    import contextlib
    import io
    from argparse import Namespace
    from huilian import cli

    ser = EmuLink(bud)

    def run(action, *args, **kw):
        ns = Namespace(action=action, args=list(args), width=kw.get("width", 4), bytes=kw.get("bytes", False),
                       out=None, clear=kw.get("clear", False), mark=kw.get("mark"))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli.cmd_mon(ser, ns)
        return buf.getvalue()

    out = run("info")
    check("HLMN v1" in out and "0xcae000" in out, f"hl mon info: {out.splitlines()[0]}", fails)
    out = run("peek", "0xc04000", "300")
    want = flash[0x4000:0x4000 + 16].hex(" ")
    check(len(out.splitlines()) == 19 and want in out.splitlines()[0], "hl mon peek 300 B (two D1 frames)", fails)
    out = run("poke", hex(SCRATCH), "0x11223344")
    check(out.strip().endswith("44332211"), f"hl mon poke runs the handshake itself: {out.strip()}", fails)
    out = run("poke", hex(SCRATCH + 0x40), b"EQ2P\0".hex(), bytes=True)
    check(out.strip().endswith(b"EQ2P\0".hex()), "hl mon poke --bytes", fails)
    out = run("call", "0x805444", hex(SCRATCH + 0x40), hex(SCRATCH + 0x80))
    r0 = int(out.split("r0=")[1].split()[0], 16)
    check(rel(flash, r0) == ("EQ2P", 0), f"hl mon call: {out.strip()}", fails)
    out = run("log", clear=True, mark="boot ok")
    check(out.splitlines()[-1] == "boot ok", "hl mon log --clear --mark", fails)


def check(cond, what, fails):
    print(f"  {'ok  ' if cond else 'FAIL'} {what}")
    if not cond:
        fails.append(what)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("image")
    ap.add_argument("--max-insns", type=int, default=5_000_000)
    a = ap.parse_args()
    stock = Path(a.image).read_bytes()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "mon.up"
        subprocess.run([sys.executable, str(ROOT / "tools/cfw.py"), "apply", a.image, str(out), str(PATCH)],
                       check=True, stdout=subprocess.DEVNULL)
        patched = out.read_bytes()
    fails = []
    s, p = Bud(stock[BODY:], a.max_insns), Bud(patched[BODY:], a.max_insns)
    flash = patched[BODY:]

    print("boot")
    seq = lambda b, f: [(k, *rel(f, o), n, blob) for k, o, n, blob in b.e.accesses]
    mm = lambda b: {k: (v["w"], v["last_w"]) for k, v in b.e.mmio.items() if v["w"]}
    check(seq(s, stock[BODY:]) == seq(p, flash), "same partition reads as stock", fails)
    check([(t, n) for t, _, n in s.e.lookups] == [(t, n) for t, _, n in p.e.lookups], "same partition lookups", fails)
    check(mm(s) == mm(p), "same peripheral writes", fails)
    check(not p.e.fault, f"no CPU fault ({p.e.fault})", fails)

    print("stock commands through the hook")
    for frame in (b"\xc0\x05", b"\xc0\x0a", b"\xc0\x07"):
        rs, rp = s.send(frame), p.send(frame)
        check(rs == rp, f"C0 {frame[1]:02X} same reply as stock ({rp[0].hex()[:32] if rp else 'none, answered elsewhere'})", fails)
    for addr, n in ((0x4000, 32), (0x3000, 112), (0xB0000, 64)):
        rs, rp = s.send(proto.c0_read_flash(addr, n)), p.send(proto.c0_read_flash(addr, n))
        ok = all(len(r) == 1 and r[0][10:] == f[addr:addr + n] for r, f in ((rs, stock[BODY:]), (rp, flash)))
        check(ok, f"C0 83 read 0x{addr:x}+{n}: each image returns its own flash bytes", fails)

    print("monitor")
    st, d = p.mon(0xD0)
    magic, ver, auth = d[:4], d[4], d[5]
    ram, ram_len, log, log_size, head, cave = struct.unpack_from("<IIIIII", d, 6)
    check(st == 0 and magic == b"HLMN" and ver == 1, f"D0 info: ver {ver}, state 0x{ram:x}+0x{ram_len:x}, "
          f"log 0x{log:x}/{log_size}, cave 0x{cave:x}", fails)
    check(auth == 0, "D0 reports no handshake yet", fails)
    st, d = p.mon(0xD1, struct.pack("<IB", 0xC04000, 32))
    check(st == 0 and d[4:] == flash[0x4000:0x4020], "D1 peek 32 B of FIRM via XIP", fails)
    st, d = p.mon(0xD1, struct.pack("<IB", 0x805298, 4))
    check(st == 0 and struct.unpack_from("<I", d, 4)[0] == ram - 0x836420, "D1 peek heap-size literal = reserved base", fails)
    check(p.mon(0xD1, struct.pack("<IB", 0xC04000, 201))[0] == 1, "D1 peek > 200 B refused", fails)
    check(p.mon(0xD1, b"\x00")[0] == 1, "D1 short frame refused", fails)
    check(p.mon(0xD2, struct.pack("<IBI", SCRATCH, 4, 1))[0] == 2, "D2 poke locked before handshake", fails)
    check(p.mon(0xD3, struct.pack("<I", 0x824B24))[0] == 2, "D3 call locked before handshake", fails)

    r2 = p.send(b"\xc0\x02\x3d" + proto.challenge2())
    check(len(r2) == 1 and p.e.uc.mem_read(AUTH, 1)[0] == 1,
          f"stock C0 02 handshake code sets the session flag at 0x{AUTH:x}", fails)
    check(p.mon(0xD0)[1][5] == 1, "D0 reports handshake done", fails)

    st, d = p.mon(0xD2, struct.pack("<IBI", SCRATCH, 4, 0xDEADBEEF))
    check(st == 0 and d == struct.pack("<II", SCRATCH, 0xDEADBEEF), "D2 poke u32 + readback", fails)
    st, d = p.mon(0xD2, struct.pack("<IBI", SCRATCH + 2, 2, 0x1234))
    check(st == 0 and bytes(p.e.uc.mem_read(SCRATCH, 4)) == bytes.fromhex("efbe3412"), "D2 poke u16", fails)
    check(p.mon(0xD2, struct.pack("<IBI", SCRATCH + 1, 4, 0))[0] == 1, "D2 misaligned u32 refused", fails)
    st, d = p.mon(0xD2, struct.pack("<IB", SCRATCH + 0x10, 0) + b"TONE\0")
    check(st == 0 and d[4:] == b"TONE\0", "D2 poke bytes", fails)
    st, d = p.mon(0xD3, struct.pack("<III", 0x805444, SCRATCH + 0x10, SCRATCH + 0x20))
    tone_addr, = struct.unpack_from("<I", d, 0)
    tone_len, = struct.unpack_from("<I", p.e.uc.mem_read(SCRATCH + 0x20, 4))
    check(st == 0 and rel(flash, tone_addr)[0] == "TONE" and rel(flash, tone_addr)[1] == 0,
          f"D3 call FUN_00805444(\"TONE\") -> 0x{tone_addr:x} len 0x{tone_len:x} (moved TONE)", fails)
    check(p.mon(0xD3, b"\x00\x00")[0] == 1, "D3 bad length refused", fails)

    st, d = p.mon(0xD4, b"\x01")
    check(st == 0 and struct.unpack_from("<I", d, 4)[0] == 0, "D4 clear", fails)
    st, d = p.mon(0xD4, b"\x02hello monitor")
    h = struct.unpack_from("<I", d, 4)[0]
    st2, d2 = p.mon(0xD1, struct.pack("<IB", log, h))
    check(st == 0 and h == 13 and d2[4:] == b"hello monitor", "D4 append, ring readable with D1", fails)
    st, d = p.mon(0xD4, b"\x02" + bytes(range(200)))
    st, d = p.mon(0xD4, b"\x02" + bytes(range(200)))
    st, d = p.mon(0xD4, b"\x02" + bytes(range(200)))
    magic, head, size, wraps, logp = struct.unpack("<5I", d)
    check(st == 0 and head == 613 and wraps == 1 and size == 512, f"D4 ring wraps (head {head}, wraps {wraps})", fails)
    check(p.mon(0xD7)[0] == 3, "unknown D7 answered status 3", fails)
    rs, rp = s.send(b"\xc0\xd0"), p.mon(0xD0)
    check(rs == [], "stock FIRM ignores C0 D0 (nothing to collide with)", fails)

    print("hl mon over an emulated link")
    hl_check(Bud(patched[BODY:], a.max_insns), flash, fails)

    print(f"\n{'FAIL' if fails else 'ok'}: {len(fails)} failure(s)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
