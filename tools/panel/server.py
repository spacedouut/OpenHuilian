#!/usr/bin/env python3
"""Desktop control panel for Huilian H3Pro/377H3 buds.

Serves a local web UI and proxies C0 commands through tools/huilian over an
RFCOMM/SPP link (pair the buds to this computer first; phone BT must be off).
Run:  python3 tools/panel/server.py --port AA:BB:CC:DD:EE:FF
      python3 tools/panel/server.py --port /dev/rfcomm0
Then open http://127.0.0.1:8765
"""
import argparse, json, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from huilian import link, proto  # tools/huilian

SETTINGS = {
    "anc_mode":        (0x59, 0x69, "choice", {"0":"off","1":"anc","2":"transparency","5":"adaptive"}),
    "ear_detect":      (0x55, 0x65, "bool", None),
    "game_mode":       (0x5E, 0x6E, "bool", None),
    "voice_wake":      (0x52, 0x62, "bool", None),
    "dialog_op":       (0x50, 0x60, "choice", {"1":"on","2":"off"}),
    "audio_type":      (0x66, 0x66, "wonly", None),
    "space_audio":     (0x68, 0x68, "wonly", None),
    "game_check":      (0x67, 0x67, "bool", None),
    "custom_volume":   (0x85, 0x85, "bool", None),
    "talk_sensitive":  (0x86, 0x86, "bool", None),
    "low_high_vol":    (0x87, 0x87, "bool", None),
    "long_press_left": (0x5A, 0x6A, "int", None),
    "long_press_right":(0x5B, 0x6B, "int", None),
    "double_tap_left": (0x5C, 0x6C, "int", None),
    "double_tap_right":(0x5D, 0x6D, "int", None),
    "bt_name":         (0x54, 0x64, "str", None),
}
READS = {"model":0x04,"product":0x03,"version":0x05,"battery":0x09,"in_ear":0x0A,
         "side":0x10,"link":0x12,"device_id":0x07,"product_id":0x14,"dom":0x15,
         "serial":0x51,"serial_l":0x70,"serial_r":0x71,"bt_addr":0x06,"bt_addr2":0x53}

lock = threading.Lock()
ser = None

def connect(port):
    global ser
    with lock:
        if ser is not None:
            try: ser.close()
            except Exception: pass
        ser = link.open_link(port)

def state():
    with lock:
        out = {"settings":{}, "reads":{}}
        for name,(rc,wc,kind,_) in SETTINGS.items():
            if kind == "wonly": continue
            try: out["settings"][name] = link.c0(ser, rc)
            except Exception as e: out["settings"][name] = None
        for name,rc in READS.items():
            try: out["reads"][name] = link.c0(ser, rc)
            except Exception: out["reads"][name] = None
    return out

def get(name):
    if name in SETTINGS:
        rc = SETTINGS[name][0]
    elif name in READS:
        rc = READS[name]
    else: raise KeyError(name)
    with lock: r = link.c0(ser, rc)
    return r.hex() if r else None

def setting(name, value):
    if name not in SETTINGS: raise KeyError(name)
    _, wc, kind, _ = SETTINGS[name]
    if kind == "str": v = value.encode()[:31]
    elif kind == "bool": v = bytes([1 if value in ("1",True,"true","on") else 0])
    else: v = bytes([int(value,0) & 0xFF])
    with lock: r = link.c0(ser, wc, bytes([len(v)]) + v)
    return r.hex() if r else None

def raw(cmd, payload_hex=""):
    payload = bytes.fromhex(payload_hex.replace(" ",""))
    with lock: r = link.c0(ser, int(cmd,0) & 0xFF, payload)
    return r.hex() if r else None

class H(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def _send(self, code, body, ctype="application/json"):
        self.send_response(code); self.send_header("Content-Type",ctype)
        self.send_header("Content-Length",str(len(body))); self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/":
            self._send(200, open(os.path.join(os.path.dirname(__file__),"index.html"),"rb").read(), "text/html")
        elif p == "/state":
            try: self._send(200, json.dumps(state()).encode())
            except Exception as e: self._send(500, json.dumps({"error":str(e)}).encode())
        elif p.startswith("/get/"):
            try: self._send(200, json.dumps({"reply":get(p[5:])}).encode())
            except Exception as e: self._send(500, json.dumps({"error":str(e)}).encode())
        else: self._send(404, b"{}")
    def do_POST(self):
        n = int(self.headers.get("Content-Length",0)); req = json.loads(self.rfile.read(n) or b"{}")
        try:
            if self.path == "/connect": connect(req["port"]); self._send(200, json.dumps({"ok":True}).encode())
            elif self.path == "/set": self._send(200, json.dumps({"reply":setting(req["name"],req["value"])}).encode())
            elif self.path == "/raw": self._send(200, json.dumps({"reply":raw(req["cmd"],req.get("payload",""))}).encode())
            else: self._send(404, b"{}")
        except Exception as e: self._send(500, json.dumps({"error":str(e)}).encode())

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", "-p", help="RFCOMM address or serial device; omit to connect from the UI")
    ap.add_argument("--bind", default="127.0.0.1"); ap.add_argument("--http", type=int, default=8765)
    a = ap.parse_args()
    if a.port: connect(a.port)
    ThreadingHTTPServer((a.bind, a.http), H).serve_forever()
