"""hl dash: a local tuning dashboard for live buds.

Runs a small HTTP server (stdlib only) next to the buds and serves one page.
It holds two Bluetooth links:
  - the C0 command channel (SPP, channel 3): settings, gestures, status
  - the headset channel (HFP, channel 1): the factory ANC gain line
    `+NTC=<side><op><B|F><6 digits>` (FUN_00c4f6f0 / dispatcher
    0xB2000002). side L = connected bud, R = relayed to the peer;
    op 3 sets a gain (F = feedforward, B = feedback) to digits/10000
    (linear, factory default 1.0000), op 4 persists the pair to NV
    'anc info', op 5 reads one back (the bud replies `AT+NTC=...`).
    The `+ANCFFG`-family lines also parse but post events nothing
    consumes, so they do nothing on this firmware.

On the HFP channel the buds are the headset and expect a phone (audio
gateway) on the other end, so this answers their AT commands with minimal
AG replies to bring the service level connection up. If a desktop audio
stack already holds HFP, the channel is busy; the page can release just the
Handsfree profile through BlueZ (A2DP stays up).
"""
import json
import os
import re
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import link

HFP_CHANNEL = 1
ANC_MODES = [0, 1, 2, 5]  # C0 69 takes an index into this table

# name -> (read cmd or None, write cmd, kind, extra)
SETTINGS = {
    "anc_mode": (0x59, 0x69, "anc", None),
    "ear_detect": (0x55, 0x65, "bool", None),
    "game_mode": (0x5E, 0x6E, "bool", None),
    "spatial_audio": (0x58, 0x68, "bool", None),
    "audio_type": (0x56, 0x66, "bool", None),
    "game_check": (0x57, 0x67, "bool", None),
    "air_en": (0x50, 0x60, "bool", None),
    "custom_volume": (None, 0x85, "bool", None),
    "talk_sensitive": (None, 0x86, "bool", None),
    "low_high_vol": (None, 0x87, "bool", None),
    "eq_mode": (0x52, 0x62, "int", (0, 9)),
    "long_press_left": (0x5A, 0x6A, "int", (1, 3)),
    "long_press_right": (0x5B, 0x6B, "int", (1, 3)),
    "double_tap_left": (0x5C, 0x6C, "int", (2, 5)),
    "double_tap_right": (0x5D, 0x6D, "int", (2, 5)),
}

# key -> (side, selector): feedforward/feedback on the connected bud
# (L) or the peer (R). Gain is a linear float, 1.0000 is the default.
GAINS = {
    "ffl": ("L", "F"),
    "fbl": ("L", "B"),
    "ffr": ("R", "F"),
    "fbr": ("R", "B"),
}
GAIN_MIN, GAIN_MAX = 0.0, 1.9999

_NTC_REPLY = re.compile(r"^AT\+NTC=([LR])([0-9])([BF])([0-9]{6})$")

_BTADDR = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}")

CIND_TEST = (b'+CIND: ("service",(0,1)),("call",(0,1)),("callsetup",(0-3)),'
             b'("callheld",(0-2)),("signal",(0-5)),("roam",(0,1)),("battchg",(0-5))')


def ntc_line(side, op, sel, digits=0):
    return f"+NTC={side}{op}{sel}{digits:06d}"


def gain_line(key, value):
    side, sel = GAINS[key]
    v = float(value)
    if not GAIN_MIN <= v <= GAIN_MAX:
        raise ValueError(f"{key} must be {GAIN_MIN}..{GAIN_MAX}")
    return ntc_line(side, "3", sel, round(v * 10000))


def ag_reply(at_line):
    """Minimal audio-gateway answer to one AT command from the headset."""
    cmd = at_line.strip().upper()
    if cmd.startswith("AT+BRSF"):
        body = b"+BRSF: 0"
    elif cmd == "AT+CIND=?":
        body = CIND_TEST
    elif cmd == "AT+CIND?":
        body = b"+CIND: 1,0,0,0,5,0,5"
    elif cmd == "AT+CHLD=?":
        body = b"+CHLD: (0,1,2,3)"
    elif cmd.startswith("AT+XAPL"):
        body = b"+XAPL=iPhone,7"
    else:
        body = None
    out = b""
    if body:
        out += b"\r\n" + body + b"\r\n"
    return out + b"\r\nOK\r\n"


class HfpLink:
    """RFCOMM link to the headset channel, with a thread answering AT commands."""

    def __init__(self, addr, channel=HFP_CHANNEL, log=print):
        self.addr, self.channel, self.log = addr, channel, log
        self.sock = None
        self.lock = threading.Lock()
        self.connect_lock = threading.Lock()
        self.error = None
        self.wanted = False
        # gains the bud reported back, keyed (side, selector)
        self.ntc = {}

    @property
    def up(self):
        return self.sock is not None

    def connect(self, tries=4):
        """Open the channel. A link that just dropped can stay busy (EBUSY)
        for a few seconds while the kernel tears it down, so retry."""
        with self.connect_lock:
            self.close()
            for attempt in range(tries):
                s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
                s.settimeout(8)
                try:
                    s.connect((self.addr, self.channel))
                    break
                except OSError as e:
                    s.close()
                    self.error = str(e)
                    busy = getattr(e, "errno", None) in (16, 114)
                    if busy and attempt < tries - 1:
                        time.sleep(2)
                        continue
                    raise OSError(f"HFP channel {self.channel}: {e}"
                                  + (" (busy: another program holds HFP, or the last link "
                                     "is still closing)" if busy else ""))
            s.settimeout(None)
            self.sock, self.error = s, None
            threading.Thread(target=self._reader, args=(s,), daemon=True).start()
            self.log("HFP channel connected")

    def _reader(self, s):
        buf = b""
        try:
            while True:
                d = s.recv(512)
                if not d:
                    break
                buf += d
                while b"\r" in buf:
                    line, _, buf = buf.partition(b"\r")
                    line = line.strip(b"\n").decode(errors="replace")
                    if not line:
                        continue
                    self.log(f"bud> {line}")
                    m = _NTC_REPLY.match(line)
                    if m:
                        self.ntc[(m.group(1), m.group(3))] = int(m.group(4)) / 10000
                        continue
                    if line.upper().startswith("AT"):
                        with self.lock:
                            s.sendall(ag_reply(line))
        except OSError as e:
            self.log(f"HFP read: {e}")
        # close it here: a socket left open after the peer drops keeps the
        # channel busy and every reconnect fails with EBUSY
        try:
            s.close()
        except OSError:
            pass
        if self.sock is s:
            self.sock = None
            self.error = "link dropped"
            self.log("HFP channel dropped")

    def send_line(self, line):
        if not self.up:
            self.connect()
        try:
            with self.lock:
                self.sock.sendall(b"\r\n" + line.encode() + b"\r\n")
        except (OSError, AttributeError):
            self.connect()
            with self.lock:
                self.sock.sendall(b"\r\n" + line.encode() + b"\r\n")
        self.log(f"ag> {line}")

    def close(self):
        s, self.sock = self.sock, None
        if s:
            try:
                s.close()
            except OSError:
                pass


class C0Link:
    def __init__(self, port, opener=link.open_link, log=print):
        self.port, self.opener, self.log = port, opener, log
        self.ser = None
        self.lock = threading.Lock()

    def _c0(self, cmd, payload=b""):
        for attempt in range(2):
            try:
                if self.ser is None:
                    self.ser = self.opener(self.port)
                return link.c0(self.ser, cmd, payload, timeout=2.5)
            except OSError as e:
                self.log(f"C0 link: {e}")
                try:
                    self.ser.close()
                except Exception:
                    pass
                self.ser = None
                if attempt:
                    raise

    def read(self, cmd):
        with self.lock:
            r = self._c0(cmd)
        if r is None or len(r) < 3:
            return None
        return bytes(r[3:3 + r[2]])

    def write(self, cmd, data):
        with self.lock:
            return self._c0(cmd, bytes([len(data)]) + data)


STATUS_REGS = (("in_ear", 0x0A), ("link", 0x12), ("side", 0x10))


class Dash:
    """Keeps a cached view of the buds so the page never waits on Bluetooth.

    A background thread refreshes battery / in-ear / link every couple of
    seconds and all settings now and then; a write updates its own entry right
    away and re-reads just that register."""

    def __init__(self, c0, hfp, addr=None):
        self.c0, self.hfp, self.addr = c0, hfp, addr
        self.logbuf = []
        self.sent = {k: None for k in GAINS}
        self.cache = {"c0": False, "settings": {}, "version": None}
        self.stop = threading.Event()

    def log(self, msg):
        self.logbuf.append(time.strftime("%H:%M:%S ") + msg)
        del self.logbuf[:-200]

    def _read_setting(self, name):
        rd, _, kind, _ = SETTINGS[name]
        if rd is None:
            return
        v = self.c0.read(rd)
        if v:
            x = v[0]
            # C0 59 answers with the index into ANC_MODES (3 = adaptive),
            # not the mode value the write table uses
            if kind == "anc" and x < len(ANC_MODES):
                x = ANC_MODES[x]
            self.cache["settings"][name] = x

    def refresh_fast(self):
        try:
            if self.cache["version"] is None:
                v = self.c0.read(0x05)
                self.cache["version"] = v.rstrip(b"\0").decode(errors="replace") if v else None
            b = self.c0.read(0x09)
            self.cache["c0"] = b is not None
            if b and len(b) >= 3:
                self.cache["battery"] = {"l": b[0], "r": b[1], "case": b[2]}
            for name, cmd in STATUS_REGS:
                v = self.c0.read(cmd)
                self.cache[name] = v[0] if v else None
            self.cache.pop("c0_error", None)
        except OSError as e:
            self.cache["c0"] = False
            self.cache["c0_error"] = str(e)

    def refresh_settings(self):
        for name in SETTINGS:
            try:
                self._read_setting(name)
            except OSError as e:
                self.cache["c0_error"] = str(e)
                return

    def run_poller(self, fast=2.0, slow=30.0):
        def loop():
            self.refresh_fast()
            self.refresh_settings()
            last_slow = time.time()
            while not self.stop.wait(fast):
                self.refresh_fast()
                if self.hfp is not None and not self.hfp.up:
                    try:
                        self.hfp.connect(tries=1)
                    except OSError:
                        pass
                if time.time() - last_slow > slow:
                    self.refresh_settings()
                    last_slow = time.time()
        threading.Thread(target=loop, daemon=True).start()

    def status(self):
        st = dict(self.cache)
        st["settings"] = dict(self.cache["settings"])
        st["hfp"] = self.hfp.up if self.hfp else False
        st["hfp_error"] = self.hfp.error if self.hfp else "no Bluetooth address"
        g = dict(self.sent)
        if self.hfp is not None:
            for k, (side, sel) in GAINS.items():
                if (side, sel) in self.hfp.ntc:
                    g[k] = self.hfp.ntc[(side, sel)]
        st["gains"] = g
        st["log"] = self.logbuf[-60:]
        return st

    def set(self, name, value):
        rd, wr, kind, extra = SETTINGS[name]
        v = shown = int(value)
        if kind == "anc":
            if v not in ANC_MODES:
                raise ValueError("anc_mode must be 0, 1, 2 or 5")
            v = ANC_MODES.index(v)
        elif kind == "bool":
            v = shown = 1 if v else 0
        else:
            lo, hi = extra
            if not lo <= v <= hi:
                raise ValueError(f"{name} must be {lo}..{hi}")
        r = self.c0.write(wr, bytes([v]))
        self.log(f"set {name}={value} -> {r.hex() if r else 'no reply'}")
        if r is not None:
            self.cache["settings"][name] = shown
            if rd is not None:
                self._read_setting(name)
        return r is not None, self.cache["settings"].get(name)

    def gain(self, key, value):
        line = gain_line(key, value)
        self.hfp.send_line(line)
        self.sent[key] = float(value)

    def gain_read(self):
        """Ask both buds to report their current FF/FB gains."""
        for side in ("L", "R"):
            for sel in ("F", "B"):
                self.hfp.send_line(ntc_line(side, "5", sel))

    def gain_save(self):
        """Persist the current gains to NV 'anc info' on both buds."""
        for side in ("L", "R"):
            self.hfp.send_line(ntc_line(side, "4", "F"))

    def hfp_connect(self):
        # never tear down a working link: that is what kept killing it
        if not self.hfp.up:
            self.hfp.connect()

    def release_hfp(self):
        if self.hfp.up:
            self.log("HFP is up, nothing to release")
            return
        dev = "/org/bluez/hci0/dev_" + self.addr.replace(":", "_").upper()
        r = subprocess.run(["busctl", "--system", "call", "org.bluez", dev, "org.bluez.Device1",
                            "DisconnectProfile", "s", "0000111e-0000-1000-8000-00805f9b34fb"],
                           capture_output=True, text=True, timeout=15)
        self.log(f"release HFP profile: rc={r.returncode} {r.stderr.strip()}")
        if r.returncode != 0:
            raise OSError(r.stderr.strip() or "DisconnectProfile failed")
        time.sleep(2)


def make_handler(dash, page):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, obj=None, body=None, ctype="application/json"):
            data = body if body is not None else json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                return self._send(200, body=page, ctype="text/html; charset=utf-8")
            if self.path == "/api/status":
                return self._send(200, dash.status())
            if self.path == "/api/meta":
                return self._send(200, {"settings": {k: {"kind": v[2], "range": v[3], "readable": v[0] is not None}
                                                     for k, v in SETTINGS.items()},
                                        "gains": {k: {"min": GAIN_MIN, "max": GAIN_MAX}
                                                  for k in GAINS}})
            self._send(404, {"error": "not found"})

        def do_POST(self):
            # same-origin only: the page is served from here
            origin = self.headers.get("Origin")
            if origin and origin != f"http://{self.headers.get('Host')}":
                return self._send(403, {"error": "cross-origin request refused"})
            try:
                n = int(self.headers.get("Content-Length") or 0)
                req = json.loads(self.rfile.read(n) or b"{}")
                if self.path == "/api/set":
                    ok, value = dash.set(req["name"], req["value"])
                    return self._send(200, {"ok": ok, "value": value})
                if self.path == "/api/gain":
                    dash.gain(req["key"], req["value"])
                    return self._send(200, {"ok": True})
                if self.path == "/api/gain/read":
                    dash.gain_read()
                    return self._send(200, {"ok": True})
                if self.path == "/api/gain/save":
                    dash.gain_save()
                    return self._send(200, {"ok": True})
                if self.path == "/api/hfp/connect":
                    dash.hfp_connect()
                    return self._send(200, {"ok": True})
                if self.path == "/api/hfp/release":
                    dash.release_hfp()
                    dash.hfp_connect()
                    return self._send(200, {"ok": True})
            except (KeyError, ValueError, OSError) as e:
                dash.log(f"error: {e}")
                return self._send(400, {"error": str(e)})
            self._send(404, {"error": "not found"})
    return H


def serve(port, listen="127.0.0.1:8765", c0=None, hfp=None):
    host, _, p = listen.rpartition(":")
    addr = port.split(":")[:6] if _BTADDR.match(port or "") else None
    addr = ":".join(addr) if addr else None
    dash = Dash(None, None, addr)
    dash.c0 = c0 or C0Link(port, log=dash.log)
    dash.hfp = hfp or (HfpLink(addr, log=dash.log) if addr else None)
    if dash.hfp is not None:
        try:
            dash.hfp_connect()
        except OSError as e:
            dash.log(str(e))
    dash.run_poller()
    page = open(os.path.join(os.path.dirname(__file__), "dash.html"), "rb").read()
    srv = ThreadingHTTPServer((host or "127.0.0.1", int(p)), make_handler(dash, page))
    print(f"dashboard on http://{host or '127.0.0.1'}:{p}  (Ctrl-C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if dash.hfp:
            dash.hfp.close()
