#!/usr/bin/env python3
"""Push a .up image to one H3Pro bud over StarFun's authenticated SPP link (55 AA OTA frames).

  flashota.py plan  <image.up> --stock <stock.up> [--frames frames.txt]
  flashota.py send  <image.up> --stock <stock.up> --side L|R [--yes]
  flashota.py selftest

`plan` is offline: it runs every check below and prints the frames it would send. `send` is
the only mode that touches a bud; it does the same checks first, then asks for confirmation.

Frames match StarFun 2.0.7 (BtOtaHelper / OtaCmdConfig.packCmd83Data) byte for byte, minus the
app's step that copies the bud's current EQ2P/TONE into the image, so custom prompts survive.
Sequence: 80 enter, 81 prepare, 82 declare CRC16+length of flash 0x3000..OTAP, 83 x N with
512-byte chunks of FIRM..OTAP, 83 with the partition index at 0x3000, 84 finalize, 04 reboot.

Refuses an image unless:
  * the CONFIG CRC and every stored partition CRC check out,
  * the index sits at 0x3000, FIRM starts at 0x4000 and the index fits OTAP's 0x80-byte buffer,
  * the OTAP and PSMP index entries and the OTAP bytes are identical to --stock,
  * nothing else reaches into OTAP, and index padding matches stock images (zeros).
Nothing below 0x4000 is written except the index page, and nothing at or above OTAP at all,
so the bootloader, OTAP and PSMP stay as they are. If 84 reports a CRC failure, 04 is not sent
and the bud stays in OTAP (old index restored) so you can retry. See docs/06 and docs/17.
"""
import argparse
import os
import struct
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from upfmt import BODY, MAGIC, crc16, index_offset, parse_index  # noqa: E402

HOST = os.environ.get("FRIDA_HOST", "127.0.0.1:27042")
INDEX_ADDR = 0x3000
FIRM_ADDR = 0x4000
CHUNK = 512
INDEX_MAX = 0x80
SIDES = {"L": 0x11, "R": 0x22}


def crc8_maxim(data: bytes) -> int:
    """CRC-8/MAXIM (Dallas 1-Wire): reflected poly 0x31, init 0."""
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8C if crc & 1 else crc >> 1
    return crc


def seal(frame: bytes) -> bytes:
    return frame + bytes([crc8_maxim(frame)])


def control(cmd: int, side: int) -> bytes:
    return seal(bytes([0x55, 0xAA, cmd, side, 0x00]))


def declare(side: int, crc: int, total: int) -> bytes:
    return seal(bytes([0x55, 0xAA, 0x82, side, 0x08]) + struct.pack("<II", crc, total))


def data_frame(addr: int, chunk: bytes) -> bytes:
    return seal(b"\x55\xAA\x83" + struct.pack("<HII", len(chunk) + 8, addr, len(chunk)) + chunk)


def parse_reply(b: bytes):
    """OTAP reply: 55 AA <cmd> <side of the bud answering> <len> <payload> <crc8>."""
    if len(b) < 6 or b[:2] != b"\x55\xAA":
        return None
    n = b[4]
    if len(b) < 6 + n or crc8_maxim(b[:5 + n]) != b[5 + n]:
        return None
    return {"cmd": b[2], "side": b[3], "payload": b[5:5 + n]}


def load(path):
    data = open(path, "rb").read()
    if data[:6] != MAGIC:
        raise SystemExit(f"{path}: not a .up (missing CONFIG magic)")
    body = data[BODY:]
    outer = struct.unpack_from("<H", data, 0x14)[0]
    if crc16(body) != outer:
        raise SystemExit(f"{path}: CONFIG CRC mismatch (stored 0x{outer:04x}, calc 0x{crc16(body):04x})")
    idx = index_offset(body)
    _, entries = parse_index(body, idx)
    parts = {tag: (addr, length, crc) for tag, addr, length, crc in entries}
    return body, idx, entries, parts


def plan(image, stock, side=0x11):
    """Check `image` against `stock` and return (frames, summary). Raises SystemExit on refusal."""
    body, idx, entries, parts = load(image)
    sbody, _, _, sparts = load(stock)
    fail = []

    if idx != INDEX_ADDR:
        fail.append(f"index at 0x{idx:x}, expected 0x{INDEX_ADDR:x}")
    index_len = (len(entries) + 1) * 16
    if index_len > INDEX_MAX:
        fail.append(f"index is {index_len} bytes, OTAP only buffers {INDEX_MAX}")
    for tag in (b"FIRM", b"OTAP", b"PSMP"):
        if tag not in parts:
            raise SystemExit(f"refusing: no {tag.decode()} partition")
        if tag not in sparts:
            raise SystemExit(f"refusing: stock image has no {tag.decode()} partition")
    if parts[b"FIRM"][0] != FIRM_ADDR:
        fail.append(f"FIRM at 0x{parts[b'FIRM'][0]:x}, expected 0x{FIRM_ADDR:x}")
    for tag in (b"OTAP", b"PSMP"):
        if parts[tag] != sparts[tag]:
            fail.append(f"{tag.decode()} index entry differs from stock")
    otap, otap_len, _ = parts[b"OTAP"]
    if len(body) < otap + otap_len or sbody[otap:otap + otap_len] != body[otap:otap + otap_len]:
        fail.append("OTAP bytes differ from stock (or are missing)")

    for tag, addr, length, crc in entries:
        name = tag.decode("latin1")
        if tag not in (b"OTAP", b"PSMP"):
            if addr < FIRM_ADDR or addr + length > otap:
                fail.append(f"{name} 0x{addr:x}+0x{length:x} is outside 0x{FIRM_ADDR:x}..0x{otap:x}")
        if addr + length <= len(body) and tag != b"PSMP" and crc16(body[addr:addr + length]) != crc:
            fail.append(f"{name} CRC mismatch")
    pad = body[INDEX_ADDR + index_len:FIRM_ADDR]
    if any(pad):
        fail.append("index page padding is not all zero (stock images are)")
    if fail:
        raise SystemExit("refusing:\n  " + "\n  ".join(fail))

    total = otap - INDEX_ADDR
    crc = crc16(body[INDEX_ADDR:otap])
    frames = [("80", control(0x80, side)), ("81", control(0x81, side)),
              ("82", declare(side, crc, total))]
    counted = 0
    for a in range(FIRM_ADDR, otap, CHUNK):
        chunk = body[a:min(a + CHUNK, otap)]
        frames.append(("83", data_frame(a, chunk)))
        counted += len(chunk)
    frames.append(("83i", data_frame(INDEX_ADDR, body[INDEX_ADDR:INDEX_ADDR + index_len])))
    counted += 0x1000  # OTAP counts the index frame as one page
    frames += [("84", control(0x84, side)), ("04", control(0x04, side))]

    for kind, f in frames:
        if f[2] == 0x83:
            a, n = struct.unpack_from("<II", f, 5)
            ok = (a == INDEX_ADDR and n == index_len) or (FIRM_ADDR <= a and a + n <= otap)
            assert ok, f"internal error: write 0x{a:x}+{n} outside the allowed range"
    assert counted == total, "internal error: byte count would not reach the declared total"

    summary = {"crc": crc, "total": total, "otap": otap, "index_len": index_len,
               "writes": sum(1 for k, _ in frames if k == "83"),
               "parts": [(t.decode("latin1"), a, n) for t, a, n, _ in entries]}
    return frames, summary


def print_plan(frames, s):
    for name, a, n in s["parts"]:
        sent = "kept by OTAP" if name in ("OTAP", "PSMP") else "written"
        print(f"  {name}  0x{a:06x}  {n:7d} B  {sent}")
    print(f"declare: CRC16 0x{s['crc']:04x} over flash 0x{INDEX_ADDR:x}..0x{s['otap']:x} "
          f"({s['total']} B)")
    print(f"writes:  {s['writes']} x 83 to 0x{FIRM_ADDR:x}..0x{s['otap']:x}, "
          f"then index ({s['index_len']} B) at 0x{INDEX_ADDR:x}")
    for kind, f in frames:
        if kind in ("80", "81", "82", "84", "04"):
            print(f"  {kind}: {f.hex(' ')}")
    print(f"  first 83: {frames[3][1][:13].hex(' ')} ... ({len(frames[3][1])} B)")


def send(frames, side, yes):
    import frida

    if not yes:
        ans = input(f"Flash the {'left' if side == 0x11 else 'right'} bud? Type FLASH to go: ")
        if ans.strip() != "FLASH":
            raise SystemExit("aborted")
    dev = frida.get_device_manager().add_remote_device(HOST)
    ses = dev.attach("Starfun")
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "flashota.js")) as fh:
        script = ses.create_script(fh.read())

    replies, lock = [], threading.Condition()
    ready, link = threading.Event(), {"up": True, "drops": 0}

    def on_message(msg, _data):
        if msg.get("type") != "send":
            print("ERR", msg, file=sys.stderr)
            return
        p = msg["payload"]
        with lock:
            if p["t"] == "ready":
                ready.set()
            elif p["t"] == "log":
                print("[js]", p["m"])
            elif p["t"] == "disc":
                link["up"] = False
                link["drops"] += 1
            elif p["t"] == "conn":
                link["up"] = True
            elif p["t"] == "rx":
                r = parse_reply(bytes.fromhex(p["hex"]))
                if r:
                    replies.append(r)
            lock.notify_all()

    script.on("message", on_message)
    script.load()
    ready.wait(10)
    if not script.exports_sync.connected():
        raise SystemExit("StarFun has no SPP link to the buds")

    def xfer(frame, tries, timeout, check):
        for _ in range(tries):
            with lock:
                replies.clear()
            script.exports_sync.ota(frame.hex().upper())
            end = time.time() + timeout
            with lock:
                while time.time() < end:
                    for r in replies:
                        if r["cmd"] == frame[2] and check(r):
                            return r
                    if not link["up"]:
                        return None
                    lock.wait(end - time.time())
        return None

    def wait_link(up, secs):
        end = time.time() + secs
        with lock:
            while link["up"] != up and time.time() < end:
                lock.wait(end - time.time())
            return link["up"] == up

    ok = lambda r: r["payload"][:1] == b"\x00"  # noqa: E731
    f = dict((k, v) for k, v in frames if k != "83")

    # 80: FIRM sets the 0x55AA flag and reboots into OTAP; OTAP just says ok.
    r = xfer(f["80"], 6, 3, lambda r: True)
    if wait_link(False, 8):
        print("bud rebooting into OTAP; waiting for the link to come back (reconnect in Android "
              "Bluetooth settings if StarFun doesn't)")
        if not wait_link(True, 120):
            raise SystemExit("no reconnect; bud should be sitting in OTAP, rerun to continue")
        time.sleep(1)
        r = xfer(f["80"], 6, 3, ok)
    if not r or not ok(r):
        raise SystemExit(f"80 not acknowledged: {r}")
    if r["side"] != side:
        raise SystemExit(f"the connected bud reports side 0x{r['side']:02x}, not 0x{side:02x}; "
                         "OTAP flashes whichever bud is connected. Nothing written.")
    drops = link["drops"]
    for k in ("81", "82"):
        if not xfer(f[k], 6, 3, ok):
            raise SystemExit(f"{k} not acknowledged; nothing written yet")

    writes = [fr for k, fr in frames if k in ("83", "83i")]
    t0 = time.time()
    for i, fr in enumerate(writes, 1):
        a, n = struct.unpack_from("<II", fr, 5)
        want = struct.pack("<II", a, n)
        r = xfer(fr, 5, 4, lambda r: ok(r) and r["payload"][1:9] == want)
        if not r or link["drops"] != drops:
            raise SystemExit(f"write @0x{a:x} failed; the bud stays in OTAP, rerun from the start")
        if i % 100 == 0 or i == len(writes):
            rate = i * CHUNK / max(time.time() - t0, 0.001)
            print(f"  {i}/{len(writes)} ({rate:.0f} B/s)")

    r = xfer(f["84"], 3, 10, lambda r: True)
    if not r or not ok(r):
        raise SystemExit(f"84 reports failure ({r}); NOT sending 04, the bud stays in OTAP "
                         "with its old index. Rerun to retry.")
    xfer(f["04"], 1, 3, lambda r: True)
    print("verified; 04 sent, bud is rebooting into the new firmware")
    ses.detach()


def selftest():
    assert crc8_maxim(b"123456789") == 0xA1
    assert crc16(b"123456789") == 0x29B1
    c = control(0x80, 0x11)
    assert c[:5] == bytes.fromhex("55aa801100") and len(c) == 6 and parse_reply(c)
    d = declare(0x22, 0xBEEF, 0xCF000)
    assert d[:5] == bytes.fromhex("55aa822208") and d[5:13] == bytes.fromhex("efbe000000f00c00")
    w = data_frame(0x4000, bytes(range(256)) * 2)
    assert w[3:13] == bytes.fromhex("0802 00400000 00020000".replace(" ", ""))
    assert len(w) == 13 + 512 + 1 and crc8_maxim(w[:-1]) == w[-1]
    ack = seal(bytes.fromhex("55aa831109") + b"\0" + struct.pack("<II", 0x4000, 512))
    assert parse_reply(ack)["payload"][1:9] == struct.pack("<II", 0x4000, 512)
    assert parse_reply(ack[:-1] + bytes([ack[-1] ^ 1])) is None
    print("selftest OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=["plan", "send", "selftest"])
    ap.add_argument("image", nargs="?")
    ap.add_argument("--stock", help="stock .up for the same model (OTAP/PSMP reference)")
    ap.add_argument("--side", choices=sorted(SIDES), help="bud to flash (send mode)")
    ap.add_argument("--frames", help="plan: write every frame as hex, one per line")
    ap.add_argument("--yes", action="store_true", help="send: skip the confirmation prompt")
    a = ap.parse_args()
    if a.mode == "selftest":
        return selftest()
    if not a.image or not a.stock:
        ap.error("image and --stock are required")
    if a.mode == "send" and not a.side:
        ap.error("send needs --side L or --side R (one bud per run)")
    side = SIDES[a.side or "L"]
    frames, s = plan(a.image, a.stock, side)
    print_plan(frames, s)
    if a.frames:
        with open(a.frames, "w") as fh:
            fh.writelines(f"{fr.hex()}\n" for _, fr in frames)
        print(f"wrote {len(frames)} frames to {a.frames}")
    if a.mode == "send":
        send(frames, side, a.yes)


if __name__ == "__main__":
    main()
