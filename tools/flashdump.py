#!/usr/bin/env python3
"""Dump flash from the H3Pro buds via StarFun's authenticated SPP link (C0 83 reads).

Read-only: the only command ever sent is C0 83 <addr> <len>.
Usage: flashdump.py <addr_hex> <total_len> <out.bin> [chunk]
"""
import os
import sys
import threading
import time

import frida

HOST = os.environ.get("FRIDA_HOST", "127.0.0.1:27042")


def main():
    addr = int(sys.argv[1], 16)
    total = int(sys.argv[2], 0)
    out = sys.argv[3]
    chunk = int(sys.argv[4]) if len(sys.argv) > 4 else 100

    dev = frida.get_device_manager().add_remote_device(HOST)
    ses = dev.attach("Starfun")
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "flashdump.js")) as fh:
        script = ses.create_script(fh.read())

    got = {}
    ready = threading.Event()
    rx = threading.Event()

    def on_message(msg, data):
        if msg.get("type") != "send":
            print("ERR", msg, file=sys.stderr)
            return
        p = msg["payload"]
        if p.get("t") == "ready":
            ready.set()
        elif p.get("t") == "log":
            print("[js]", p["m"])
        elif p.get("t") == "rx":
            h = p["hex"]
            b = bytes.fromhex(h)
            a = int.from_bytes(b[2:6], "little")
            n = int.from_bytes(b[6:10], "little")
            got[a] = b[10:10 + n]
            rx.set()

    script.on("message", on_message)
    script.load()
    ready.wait(10)

    pos, fails = addr, 0
    t0 = time.time()
    while pos < addr + total:
        n = min(chunk, addr + total - pos)
        rx.clear()
        script.exports_sync.read(pos, n)
        if not rx.wait(6):
            fails += 1
            if fails > 5:
                print(f"giving up at 0x{pos:x}", file=sys.stderr)
                break
            continue
        fails = 0
        if pos not in got:
            time.sleep(0.05)
        pos += n
        done = pos - addr
        if done % (chunk * 50) == 0:
            rate = done / max(time.time() - t0, 0.001)
            eta = (total - done) / max(rate, 1)
            print(f"  {done}/{total} ({rate:.0f} B/s, eta {eta/60:.1f} min)")

    blob = bytearray()
    for a in sorted(got):
        off = a - addr
        if off < 0:
            continue
        if len(blob) < off:
            blob.extend(b"\xff" * (off - len(blob)))
        blob[off:off + len(got[a])] = got[a]
    with open(out, "wb") as fh:
        fh.write(bytes(blob))
    print(f"wrote {len(blob)} bytes to {out} ({len(got)} chunks)")
    ses.detach()


if __name__ == "__main__":
    main()
