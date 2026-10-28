"""hl - command line tool for the Huilian H3Pro / 377H3 earbuds.

Talks the StarFun C0 protocol and the 55AA OTA protocol natively over a
serial (RFCOMM/SPP) port, without StarFun or Frida.

Pair the buds to the computer first, then pick the SPP port:
  `hl --port /dev/rfcomm0 info`  (Linux, after `rfcomm bind`)
  `hl --port COM6 info`          (Windows outgoing COM port)

Subcommands:
  info   - model, version, battery, side, link state
  auth   - run the C0 01/02 handshake (the "authorization" gate)
  get    - read a named setting (see `hl get`)
  set    - write a named setting (mirrored to the peer bud by firmware)
  read   - dump live flash via C0 83
  ota    - flash a .up image via the 55AA OTA path
  cmd    - send a raw frame, hex in / hex out
  tone   - list/extract/replace prompt sounds in a .up (wraps tone_tool.py)
  patch  - apply cfw patch files to a .up (wraps cfw.py)
"""
import argparse
import struct
import sys
import time

from . import link, proto

# name -> (read_cmd, write_cmd, payload builder, response formatter)
SETTINGS = {
    "anc_mode": (0x59, 0x69, None,
                 "0=off 1=anc 2=transparency 5=adaptive"),
    "ear_detect": (0x55, 0x65, None, "0/1"),
    "game_mode": (0x5E, 0x6E, None, "0/1"),
    "eq_mode": (0x52, 0x62, None, "one byte"),
    "air_en": (0x50, 0x60, None, "0/1 (AirPods emulation)"),
    "long_press_left": (0x5A, 0x6A, None, "action id 1..3"),
    "long_press_right": (0x5B, 0x6B, None, "action id 1..3"),
    "double_tap_left": (0x5C, 0x6C, None, "action id 2..5"),
    "double_tap_right": (0x5D, 0x6D, None, "action id 2..5"),
    "bt_name": (0x54, 0x64, "str", "string, max 31 chars"),
}
READS = {
    "model": 0x04, "product": 0x03, "version": 0x05, "battery": 0x09,
    "in_ear": 0x0A, "side": 0x10, "link": 0x12, "device_id": 0x07,
    "product_id": 0x14, "dom": 0x15, "serial": 0x51,
    "serial_l": 0x70, "serial_r": 0x71, "bt_addr": 0x06, "bt_addr2": 0x53,
}
SIDES = {"l": 0x11, "r": 0x22}


def _fmt(b):
    if b is None:
        return "<no reply>"
    txt = "".join(chr(c) if 32 <= c < 127 else "." for c in b)
    return f"{b.hex()}  {txt.strip('. ')}".strip()


def _payload(r):
    """Reply `C0 cmd len data` -> data; C0 83 handled separately."""
    if r is None or len(r) < 3 or r[0] != 0xC0:
        return None
    n = r[2]
    return bytes(r[3:3 + n])


def cmd_auth(ser, _a):
    print("C0 01 challenge ...")
    ch = proto.challenge1()
    r = link.c0(ser, 0x01, ch)
    if r is None:
        sys.exit("no reply to C0 01 - unit is not authorized (authorization_code missing/wrong)")
    print("  reply:", _fmt(r))
    print("C0 02 verify ...")
    ch2 = proto.challenge2()
    r = link.c0(ser, 0x02, ch2)
    if r is None:
        sys.exit("no reply to C0 02")
    p = _payload(r)
    ok = p is not None and p == proto.c002_reply(ch2)
    print("  reply:", _fmt(r))
    print("  reply matches expected transform:", ok)
    print("authorized" if ok else "answered, but response did not verify")


def cmd_info(ser, _a):
    for name in ("model", "version", "battery", "in_ear", "side", "link",
                 "product", "serial_l", "serial_r", "bt_addr"):
        r = link.c0(ser, READS[name])
        p = _payload(r)
        if name == "battery" and p and len(p) >= 3:
            print(f"{name:12} L={p[0]} R={p[1]} case={p[2]}")
        elif name in ("side", "link", "in_ear") and p is not None:
            print(f"{name:12} {p.hex()}")
        else:
            print(f"{name:12} {_fmt(p)}")


def cmd_get(ser, a):
    if a.name not in SETTINGS and a.name not in READS:
        print("known settings:", ", ".join(sorted(SETTINGS)))
        print("known reads:", ", ".join(sorted(READS)))
        return
    cmd = SETTINGS[a.name][0] if a.name in SETTINGS else READS[a.name]
    r = link.c0(ser, cmd)
    print(f"{a.name} = {_fmt(_payload(r))}")


def cmd_set(ser, a):
    if a.name not in SETTINGS:
        sys.exit(f"unknown setting {a.name!r}; known: {', '.join(sorted(SETTINGS))}")
    _, wcmd, kind, hint = SETTINGS[a.name]
    if kind == "str":
        v = a.value.encode()
        if len(v) > 31:
            sys.exit("bt_name max 31 bytes")
    else:
        v = bytes([int(a.value, 0)])
    r = link.c0(ser, wcmd, v)
    print(f"{a.name} <- {_fmt(_payload(r))}   ({hint})")


def cmd_read(ser, a):
    addr = int(a.addr, 0)
    total = int(a.length, 0)
    data = link.read_flash_range(ser, addr, total, chunk=a.chunk)
    if data is None:
        sys.exit("read failed partway (see log)")
        return
    with open(a.out, "wb") as f:
        f.write(data)
    print(f"wrote {len(data)} bytes to {a.out}")


def _up_payloads(up_path):
    """From a .up file: (payload_region_bytes, firmware_addr, index_bytes, index_addr)."""
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
    from upfmt import MAGIC, BODY, index_offset, parse_index
    data = open(up_path, "rb").read()
    if data[:6] != MAGIC:
        sys.exit("not a .up (missing CONFIG header)")
    body = data[BODY:]
    io = index_offset(body)
    ver, entries = parse_index(body, io)
    # only partitions whose bytes are actually stored in the image get written
    present = [e for e in entries if e[1] + e[2] <= len(body)]
    fw_addr = min(e[1] for e in present)
    last_end = max(e[1] + e[2] for e in present)
    payload = body[fw_addr:last_end]
    idx_len = 8 + 16 * len(entries)
    index = body[io:io + idx_len]
    return payload, fw_addr, index, io, entries, last_end


def cmd_ota(ser, a):
    payload, fw_addr, index, io, entries, last_end = _up_payloads(a.file)
    print(f"payload region 0x{fw_addr:x}..0x{last_end:x} ({len(payload)} bytes), "
          f"index @{io:#x} ({len(index)} bytes)")
    sides = [SIDES["l"], SIDES["r"]] if a.side == "both" else [SIDES[a.side]]
    for side in sides:
        print(f"--- side {side:#x} ---")
        for attempt in range(6):
            r = link.ota_frame(ser, proto.ota_enter(side))
            print("enter(80):", r.hex() if r else "<no reply>")
            if r:
                break
        else:
            sys.exit("bud never answered 55AA80")
        r = link.ota_frame(ser, proto.ota_prepare(side))
        print("prepare(81):", r.hex() if r else "<no reply>")
        r = link.ota_frame(ser, proto.ota_declare(payload + index, side))
        print("declare(82):", r.hex() if r else "<no reply>")
        pos = 0
        while pos < len(payload):
            chunk = payload[pos:pos + 512]
            r = link.ota_frame(ser, proto.ota_write(fw_addr + pos, chunk), timeout=a.timeout)
            if not r:
                sys.exit(f"write at 0x{fw_addr + pos:#x} got no reply")
            pos += len(chunk)
            if pos % 8192 < 512:
                print(f"  0x{pos:x}/{len(payload):x}")
        r = link.ota_frame(ser, proto.ota_write(io, index), timeout=a.timeout)
        print("index write:", r.hex() if r else "<no reply>")
        r = link.ota_frame(ser, proto.ota_finalize(side), timeout=a.timeout)
        print("finalize(84):", r.hex() if r else "<link dropped / rebooting>")
    print("done. Buds reboot on their own.")


def cmd_cmd(ser, a):
    frame = bytes.fromhex(a.hex)
    ser.write(frame)
    time.sleep(0.5)
    out = ser.read(ser.in_waiting or 1)
    time.sleep(0.3)
    out += ser.read(ser.in_waiting)
    print(_fmt(bytes(out)))


def cmd_tone(_ser, a):
    import subprocess, os
    tt = os.path.join(os.path.dirname(__file__), "..", "tone_tool.py")
    args = ["python3", tt] + a.tone_args
    os.execvp("python3", args)


def cmd_patch(_ser, a):
    import os
    cf = os.path.join(os.path.dirname(__file__), "..", "cfw.py")
    os.execvp("python3", ["python3", cf, "apply", a.fw, a.out] + a.patch_args)


def main():
    p = argparse.ArgumentParser(prog="hl", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--port", "-p", help="serial port (rfcomm device / COM port)")
    p.add_argument("--baud", type=int, default=link.BAUD)
    sub = p.add_subparsers(dest="sub", required=True)

    sub.add_parser("auth").set_defaults(f=cmd_auth)
    sub.add_parser("info").set_defaults(f=cmd_info)

    g = sub.add_parser("get"); g.add_argument("name"); g.set_defaults(f=cmd_get)
    s = sub.add_parser("set"); s.add_argument("name"); s.add_argument("value"); s.set_defaults(f=cmd_set)

    r = sub.add_parser("read")
    r.add_argument("addr"); r.add_argument("length"); r.add_argument("out")
    r.add_argument("--chunk", type=int, default=100)
    r.set_defaults(f=cmd_read)

    o = sub.add_parser("ota")
    o.add_argument("file")
    o.add_argument("--side", choices=["l", "r", "both"], default="both")
    o.add_argument("--timeout", type=float, default=3.0)
    o.set_defaults(f=cmd_ota)

    c = sub.add_parser("cmd"); c.add_argument("hex"); c.set_defaults(f=cmd_cmd)

    t = sub.add_parser("tone"); t.add_argument("tone_args", nargs=argparse.REMAINDER)
    t.set_defaults(f=cmd_tone, needs_link=False)

    pa = sub.add_parser("patch")
    pa.add_argument("fw"); pa.add_argument("out")
    pa.add_argument("patch_args", nargs=argparse.REMAINDER)
    pa.set_defaults(f=cmd_patch, needs_link=False)

    a = p.parse_args()
    ser = None
    if getattr(a, "needs_link", True):
        if not a.port:
            sys.exit("--port is required (RFCOMM/SPP serial port of the buds)")
        ser = link.open_link(a.port, a.baud)
    a.f(ser, a)


if __name__ == "__main__":
    main()
