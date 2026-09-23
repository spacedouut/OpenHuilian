#!/usr/bin/env python3
"""Dump flash from the H3Pro buds via StarFun's authenticated SPP link (C0 83 reads).

Read-only: the only command ever sent is C0 83 <addr> <len>.
Usage: flashdump.py <addr_hex> <total_len> <out.bin> [chunk]

The device answers with at most MAX_REPLY bytes per request. Each reply is matched
against the outstanding request's address and the loop only advances by the number of
bytes actually received, so nothing is silently skipped. Output is written only when the
whole requested range was read.
"""
import os
import sys
import threading
import time

import frida

HOST = os.environ.get("FRIDA_HOST", "127.0.0.1:27042")
MAX_REPLY = 200


def main():
    addr = int(sys.argv[1], 16)
    total = int(sys.argv[2], 0)
    out = sys.argv[3]
    chunk = int(sys.argv[4]) if len(sys.argv) > 4 else 100
    if not 1 <= chunk <= MAX_REPLY:
        raise SystemExit(f"chunk must be 1..{MAX_REPLY} (device reply cap)")

    dev = frida.get_device_manager().add_remote_device(HOST)
    ses = dev.attach("Starfun")
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "flashdump.js")) as fh:
        script = ses.create_script(fh.read())

    got = {}
    pending = [None, 0]
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
            b = bytes.fromhex(p["hex"])
            if len(b) < 10:
                return
            a = int.from_bytes(b[2:6], "little")
            n = int.from_bytes(b[6:10], "little")
            data = b[10:]
            if n == 0 or len(data) != n:
                print(f"  bad reply @0x{a:x}: declared {n}, got {len(data)}", file=sys.stderr)
                return
            if a != pending[0] or n > pending[1]:
                print(f"  ignoring reply @0x{a:x} len {n} (wanted 0x{pending[0]:x} len {pending[1]})",
                      file=sys.stderr)
                return
            got[a] = data
            rx.set()

    script.on("message", on_message)
    script.load()
    ready.wait(10)

    pos, fails, reqs = addr, 0, 0
    t0 = time.time()
    complete = True
    while pos < addr + total:
        n = min(chunk, addr + total - pos)
        pending[0], pending[1] = pos, n
        rx.clear()
        script.exports_sync.read(pos, n)
        if not rx.wait(6):
            fails += 1
            if fails > 5:
                print(f"giving up at 0x{pos:x}", file=sys.stderr)
                complete = False
                break
            continue
        fails = 0
        pos += len(got[pos])
        reqs += 1
        done = pos - addr
        if reqs % 50 == 0:
            rate = done / max(time.time() - t0, 0.001)
            eta = (total - done) / max(rate, 1)
            print(f"  {done}/{total} ({rate:.0f} B/s, eta {eta/60:.1f} min)")

    ses.detach()

    blob = bytearray()
    for a in sorted(got):
        if a - addr != len(blob):
            raise SystemExit(f"internal error: gap before 0x{a:x}, not writing {out}")
        blob.extend(got[a])
    if not complete or len(blob) != total:
        raise SystemExit(f"incomplete: {len(blob)}/{total} bytes read, not writing {out}")
    with open(out, "wb") as fh:
        fh.write(bytes(blob))
    print(f"wrote {len(blob)} bytes to {out} ({len(got)} chunks)")


if __name__ == "__main__":
    main()
