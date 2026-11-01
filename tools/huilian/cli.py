"""hl - command line tool for the Huilian H3Pro / 377H3 earbuds.

Talks the StarFun C0 protocol and the 55AA OTA protocol natively over a
serial (RFCOMM/SPP) port, without StarFun or Frida.

Pair the buds to the computer first, then point --port at them:
  `hl --port AA:BB:CC:DD:EE:FF info`  (Linux: raw RFCOMM socket, channel 3,
                                       no rfcomm bind, no root, no pyserial)
  `hl --port /dev/rfcomm0 info`       (Linux serial device, needs pyserial)
  `hl --port COM6 info`               (Windows outgoing COM port)
The phone's Bluetooth must be off: the buds hold one SPP session.

Subcommands:
  info   - model, version, battery, side, link state
  auth   - run the C0 01/02 handshake (the "authorization" gate)
  get    - read a named setting (see `hl get`)
  set    - write a named setting (mirrored to the peer bud by firmware)
  read   - dump live flash via C0 83
  ota    - flash a .up image via the 55AA OTA path (both buds)
  leave-ota - get buds that are stuck in the updater (OTAP) back into FIRM
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
    r = link.c0(ser, 0x01, b"\x3d" + ch)
    if r is None:
        sys.exit("no reply to C0 01 - unit is not authorized (authorization_code missing/wrong)")
    print("  reply:", _fmt(r))
    print("C0 02 verify ...")
    ch2 = proto.challenge2()
    r = link.c0(ser, 0x02, b"\x3d" + ch2)
    if r is None:
        sys.exit("no reply to C0 02")
    p = _payload(r)
    ok = p is not None and p == proto.c002_reply(b"\xc0\x02\x3d" + ch2)
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
    # app write frames carry a one-byte payload length: C06E0101 = cmd 6E len 1 val 1
    r = link.c0(ser, wcmd, bytes([len(v)]) + v)
    print(f"{a.name} <- {_fmt(_payload(r))}   ({hint})")


def cmd_read(ser, a):
    addr = int(a.addr, 0)
    total = int(a.length, 0)
    if not 1 <= a.chunk <= 200:
        sys.exit("--chunk must be 1..200 (the device reply cap)")
    data = link.read_flash_range(ser, addr, total, chunk=a.chunk)
    if data is None:
        sys.exit("read failed partway (see log)")
        return
    with open(a.out, "wb") as f:
        f.write(data)
    print(f"wrote {len(data)} bytes to {a.out}")


def _up_payloads(up_path):
    """From a .up file: (payload, fw_addr, index, io, declared, last_end).

    Mirrors BtUtils.getUploadContent / packCmd83Data:
      - payload  = body[FIRM_addr : OTAP_addr]   (OTAP itself is never written)
      - index    = body[io : io + 16*(count+1)]  (16B header + 16B per entry)
      - declared = body[io : OTAP_addr]          (index + gap + payload, in flash
        order - this is the region the updater CRC16-verifies afterwards)
    If the index has no OTAP entry, the region ends at the last partition whose
    bytes are present in the file.
    """
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
    from upfmt import MAGIC, BODY, index_offset, parse_index
    data = open(up_path, "rb").read()
    if data[:6] != MAGIC:
        sys.exit("not a .up (missing CONFIG header)")
    body = data[BODY:]
    io = index_offset(body)
    ver, entries = parse_index(body, io)
    present = [e for e in entries if e[1] + e[2] <= len(body)]
    if not present:
        sys.exit("no partition in the index is backed by bytes in this file")
    fw_addr = min(e[1] for e in present)
    otap = [e for e in entries if e[0].rstrip(b"\0 ") == b"OTAP" and e[1] <= len(body)]
    last_end = otap[0][1] if otap else max(e[1] + e[2] for e in present)
    if last_end <= fw_addr:
        sys.exit("payload region is empty (OTAP absent and nothing else stored)")
    payload = body[fw_addr:last_end]
    index = body[io:io + 16 * (len(entries) + 1)]
    declared = body[io:last_end]
    return payload, fw_addr, index, io, declared, last_end


def _hx(v):
    return "?" if v is None else f"{v:#x}"


def _in_firm(ser):
    """FIRM answers C0 0A (in-ear); the updater (OTAP) does not."""
    return link.c0(ser, 0x0A, timeout=2.0) is not None


def _state(ser):
    side = _payload(link.c0(ser, 0x10, timeout=2.0))
    lk = _payload(link.c0(ser, 0x12, timeout=2.0))
    return (side[0] if side else None, lk[0] if lk else None, _in_firm(ser))


def _enter_updater(ser, a):
    """From FIRM, 80 is acked and then the bud (and its peer, which the master
    relays it to) reboots into OTAP and the link drops. Reconnect until the
    updater answers. Returns the new link."""
    for _ in range(4):
        if not _in_firm(ser):
            return ser
        print("FIRM answered: sending 80, both buds reboot into the updater")
        try:
            r = link.ota_frame(ser, proto.ota_enter(0x33))
            print("enter(80) from FIRM:", r.hex() if r else "<no reply>")
            if r and not r.ok:
                sys.exit(f"enter refused, status {r.status} (3 = battery too low)")
        except OSError as e:
            print("  link dropped:", e)
        ser.close()
        time.sleep(8)
        ser = link.reopen(a.port, a.baud)
    sys.exit("buds did not enter the updater")


def _ota_one_bud(ser, a, payload, fw_addr, index, io, declared):
    """Run 80..84 + 04 against whichever bud holds the link (entering the
    updater first if needed). Returns (link, answering side)."""
    ser = _enter_updater(ser, a)
    side = None
    for _ in range(6):
        r = link.ota_frame(ser, proto.ota_enter(0x33))
        print("enter(80):", r.hex() if r else "<no reply>")
        if r:
            side = r.side
            break
        time.sleep(0.5)
    else:
        sys.exit("no answer to 55AA80")
    if not r.ok:
        sys.exit(f"enter refused, status {r.status} (3 = battery too low)")
    # prepare can take a while to answer, give it 30 s
    for _ in range(3):
        r = link.ota_frame(ser, proto.ota_prepare(0x33), timeout=30)
        print("prepare(81):", r.hex() if r else "<no reply>")
        if r:
            break
    else:
        sys.exit("no reply to prepare (55AA81)")
    if not r.ok:
        sys.exit(f"prepare refused, status {r.status}")
    r = link.ota_frame(ser, proto.ota_declare(declared, 0x33))
    if not r or not r.ok:
        sys.exit(f"declare (55AA82) failed: {r.hex() if r else '<no reply>'}")
    print("declare(82):", r.hex())
    pos = 0
    t0 = time.time()
    while pos < len(payload):
        chunk = payload[pos:pos + 512]
        for attempt in range(4):
            r = link.ota_frame(ser, proto.ota_write(fw_addr + pos, chunk), timeout=a.timeout)
            if r and r.ok:
                break
            print(f"  write @0x{fw_addr + pos:x}: {r.hex() if r else 'no reply'}, retry {attempt + 1}")
        else:
            sys.exit(f"write at 0x{fw_addr + pos:x} failed")
        pos += len(chunk)
        if pos % 16384 < 512:
            print(f"  0x{pos:x}/{len(payload):x}  ({time.time() - t0:.0f}s)")
    r = link.ota_frame(ser, proto.ota_write(io, index), timeout=a.timeout)
    if not r or not r.ok:
        sys.exit("index write failed - stopping before finalize")
    print("index write:", r.hex())
    r = link.ota_frame(ser, proto.ota_finalize(0x33), timeout=10)
    print("finalize(84):", r.hex() if r else "<no reply>")
    if not r:
        sys.exit("no reply to finalize; NOT sending 04. Run `hl ota` again.")
    if not r.ok:
        sys.exit(f"finalize status {r.status}: CRC mismatch, old index restored. "
                 "NOT sending 04 (that would boot a half-written FIRM). Flash again.")
    try:
        r = link.ota_frame(ser, proto.ota_leave(0x33), timeout=5)
        print("leave(04):", r.hex() if r else "<link dropped>")
    except OSError as e:
        print("leave(04): link dropped:", e)
    return ser, side


def _find_updater(a, flashed, wait=240):
    """After the first bud's 04, find the bud still in OTAP. If the flashed bud
    comes back in FIRM and holds the link, the other one can't be reached
    until the flashed one is out of the way (in the case, lid closed)."""
    end = time.time() + wait
    told = False
    while time.time() < end:
        ser = link.reopen(a.port, a.baud)
        side, lk, firm = _state(ser)
        print(f"  answering side {_hx(side)} link {lk} mode {'FIRM' if firm else 'OTAP'}")
        if not firm:
            return ser, side
        if lk == 0:
            ser.close()
            return None, side
        if not told:
            print(f"  bud {_hx(side)} is back in FIRM and holds the link, the other bud is "
                  "still in the updater. Put the flashed bud in the case and close the "
                  "lid, keep the other one out.")
            told = True
        ser.close()
        time.sleep(5)
    sys.exit("the other bud never showed up in the updater; run `hl leave-ota`")


def cmd_ota(ser, a):
    """The 55AA flow, the way the app runs it and the way real buds accept it.

    A 55AA80 to FIRM makes BOTH buds reboot into the updater (the master
    relays it to the peer), then whichever bud grabs the SPP link is the one
    the frames land on: OTAP ignores the side byte in requests. So: flash the
    bud that answers, send 04 (clear the boot-to-OTAP flag + reboot), wait for
    the link to come back, and flash the bud that is still in the updater the
    same way (if the flashed bud grabs the link first, it has to go in the
    case). Without the 04 both buds stay in OTAP and look like a generic
    Bluetooth device.
    """
    payload, fw_addr, index, io, declared, last_end = _up_payloads(a.file)
    print(f"payload region 0x{fw_addr:x}..0x{last_end:x} ({len(payload)} bytes), "
          f"index @{io:#x} ({len(index)} bytes), declared {len(declared)} bytes")
    done = []
    ser, side = _ota_one_bud(ser, a, payload, fw_addr, index, io, declared)
    done.append(side)
    print(f"--- flashed side {_hx(side)} ---")
    if a.side == "both":
        print("waiting for the other bud ...")
        ser.close()
        time.sleep(6)
        ser2, side2 = _find_updater(a, side)
        if ser2 is None:
            print(f"both buds answer from FIRM and are linked; only {_hx(side)} was in the updater")
        elif side2 == side:
            sys.exit(f"bud {_hx(side)} is in the updater again after 04; run `hl leave-ota`")
        else:
            ser2, side2 = _ota_one_bud(ser2, a, payload, fw_addr, index, io, declared)
            done.append(side2)
            print(f"--- flashed side {_hx(side2)} ---")
            ser = ser2
    print("waiting for the buds to reboot ...")
    ser.close()
    time.sleep(8)
    ser = link.reopen(a.port, a.baud)
    side, lk, firm = _state(ser)
    print(f"answering side {_hx(side)} link {lk} mode {'FIRM' if firm else 'OTAP'}; "
          f"flashed: {[_hx(s) for s in done]}")
    if not firm:
        print("a bud is still in the updater: run `hl leave-ota`")
    elif lk != 0:
        print("peer not linked yet (link != 0); give them a moment or case-cycle both buds")
    else:
        print("done: both buds in FIRM and linked")


def cmd_leave_ota(ser, a):
    """Get buds out of the updater. OTAP's 04 handler clears the boot flag and
    reboots when the bud has no linked peer; a linked master instead relays
    the request to its peer and follows 2 s later. Sending 04 to an OTAP bud
    whose peer is already back in FIRM drags that peer back into the updater,
    so this only sends 04 when the answering bud is in OTAP, then re-checks."""
    for rnd in range(4):
        if rnd:
            ser.close()
            time.sleep(5)
            ser = link.reopen(a.port, a.baud)
        side, lk, firm = _state(ser)
        print(f"round {rnd}: side {_hx(side)} link {lk} mode {'FIRM' if firm else 'OTAP'}")
        if firm:
            if lk == 0:
                print("both buds in FIRM and linked")
            else:
                print("this bud is in FIRM but has no peer. If the other bud is still in "
                      "the updater: put THIS bud in the case with the lid closed, keep "
                      "the other out, and rerun `hl leave-ota`.")
            return
        r = link.ota_frame(ser, proto.ota_leave(0x33), timeout=5)
        print("  04:", r.hex() if r else "<link dropped>")
    sys.exit("still in the updater after 4 rounds; case-cycle both buds and rerun")


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
    r.add_argument("--chunk", type=int, default=100,
                   help="bytes per C0 83 read (1..200, device reply cap)")
    r.set_defaults(f=cmd_read)

    o = sub.add_parser("ota")
    o.add_argument("file")
    o.add_argument("--side", choices=["both", "one"], default="both",
                   help="both: flash whichever bud answers, 04, then the other; "
                        "one: stop after the first bud")
    o.add_argument("--timeout", type=float, default=3.0)
    o.set_defaults(f=cmd_ota)
    sub.add_parser("leave-ota").set_defaults(f=cmd_leave_ota)

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
