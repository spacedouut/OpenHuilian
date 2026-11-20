#!/usr/bin/env python3
"""Generate the test vectors for openhuilian/ui/webui/selftest.mjs from the Python
implementation. Usage:

    python3 -m openhuilian.ui.webui.genvec [firmware.up] > /tmp/vec.json
    node openhuilian/ui/webui/selftest.mjs /tmp/vec.json [firmware.up]
"""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from openhuilian.device import proto
from openhuilian.device.cli import _up_payloads
from openhuilian.format.tone_tool import load_tone, read_dir

out = {}
t = bytes(range(256))
out["crc16"] = "%04x" % proto.crc16(t)
out["crc8"] = "%02x" % proto.crc8(bytes.fromhex("55aa803300"))
out["scramble"] = proto.scramble(
    bytes.fromhex("00112233445566778899aabbccddeeff"), 0x756)[0].hex()
out["c0"] = proto.c0(0x6E, b"\x01\x01").hex()
out["ota_enter"] = proto.with_crc8(proto.ota_enter(0x11)).hex()
out["ota_prepare"] = proto.with_crc8(proto.ota_prepare(0x22)).hex()
out["ota_write"] = proto.with_crc8(proto.ota_write(0x4000, b"\xde\xad")).hex()
req = b"\xc0\x02\x3d" + bytes(range(0x10, 0x10 + 61))
out["req"] = req.hex()
out["c002_reply"] = proto.c002_reply(req).hex()

if len(sys.argv) > 1:
    up_path = sys.argv[1]
    payload, fw_addr, index, io_, declared, last_end, _ = _up_payloads(up_path)
    out["declared"] = proto.with_crc8(proto.ota_declare(declared, 0x33)).hex()
    out["index_len"] = "%04x" % len(index)
    with tempfile.TemporaryDirectory() as scratch, contextlib.redirect_stdout(io.StringIO()):
        patched = Path(scratch) / "patched.up"
        subprocess.run(
            [sys.executable, "-m", "openhuilian.patch.cfw", "apply", up_path, str(patched),
             str(Path(__file__).resolve().parents[3] / "patches/2607061716/head-tracking.json")],
            check=True, capture_output=True)
        out["cfw_head"] = patched.read_bytes()[:64].hex()
    _, _, _, tone = load_tone(up_path)
    out["tone_count"] = "%02x" % len(read_dir(tone))

print(json.dumps(out))
