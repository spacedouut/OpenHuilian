# hl - a native CLI for the buds

`tools/hl` (package `tools/huilian/`) talks to the H3Pro Max3 / 377H3 buds
directly over Bluetooth SPP, with no StarFun install and no Frida. It implements
the `C0` command channel and the `55AA` OTA transport itself ([18](18-firm-walkthrough.md),
[06](06-bt-ota-protocol.md)).

## Getting a port

Pair the buds to the computer, then give the tool the serial port the SPP
service sits on:

| OS | How | Port example |
|---|---|---|
| Linux | `rfcomm bind /dev/rfcomm0 <bt-addr>` (bluetoothctl `pair`/`trust` first) | `/dev/rfcomm0` |
| Windows | pairing creates an "Outgoing" COM port | `COM6` |
| macOS | `/dev/cu.*` serial device appears on pair | `/dev/cu.H3Pro-SPP` |

Only dependency is `pyserial`.

## Commands

```
hl --port PORT info             model, version, battery, in-ear, side, link, serials
hl --port PORT auth             run the C0 01/02 handshake and check the reply
hl --port PORT get <name>       read a setting
hl --port PORT set <name> <v>   write a setting (mirrored to the peer bud)
hl --port PORT read 0x0 0x100000 out.bin   dump flash via C0 83 (200 B/reply cap)
hl --port PORT ota file.up --side both     flash a .up through the 55AA path
hl --port PORT cmd <hex>        send a raw frame, print the raw reply
hl tone ...                     wraps tone_tool.py (file-side, no port needed)
hl patch fw.up out.up ...       wraps cfw.py apply (file-side, no port needed)
```

Settings you can get/set: `anc_mode` (0 off, 1 ANC, 2 transparency, 5 adaptive),
`ear_detect`, `game_mode`, `eq_mode`, `air_en`, `long_press_left/right`,
`double_tap_left/right`, `bt_name`. `hl get` with a bad name lists everything it
knows, including read-only IDs (`device_id`, `product_id`, `dom`, `serial*`,
`bt_addr`).

## The auth handshake

`hl auth` is the honest way to check the "authorization" gate: `C0 01` carries a
64-byte challenge (rejected if all-0/all-FF), `C0 02` a 64-byte verify with two
degenerate-range checks. `tools/huilian/proto.py` implements both the challenge
rules and the scrambler itself (a 16-bit LFSR, `s = rotl16(s,1) ^ (s&0x8000 ?
0xD103 : 0)`, clocked once per input bit, XOR keystream - it encrypts and
decrypts with the same call), including `c002_reply()` which reproduces the
bud's reply transform so the exchange can be verified the same way StarFun does.

A unit whose PSMP `authorization_code` doesn't descramble to "APP" simply never
answers `C0 01`, so any reply at all means the unit is authorized.

## OTA, and what isn't tested

`hl ota` mirrors the app's own flow: `80` enter, `81` prepare, `82` declare
(CRC16 + length over the payload region), `83` 512-byte writes at absolute flash
addresses, the partition index last, `84` finalize; left then right for
`--side both`. The payload region is FIRM through the last partition actually
stored in the image - a PSMP index entry with no bytes in the file is skipped,
so per-unit data is never written.

Nothing in `hl` has been run against real buds yet: the framing and transforms
come from the firmware and the app, not a captured session. First-time order of
operations on hardware: `info`, then `auth`, then a small `read`, then anything
that writes.

## The WebUI

`tools/webui/index.html` is the same stack reimplemented in JavaScript, a
static page with no build step. Chrome and Edge only: it uses
[Web Serial](https://developer.mozilla.org/docs/Web/API/Web_Serial_API)
to open the buds' SPP virtual COM port directly - Windows exposes paired
RFCOMM devices as COM ports, Linux as `/dev/rfcomm*`, macOS as `/dev/cu.*`.

The page uses ES modules, which browsers refuse to load over `file://`, so
serve the directory first:

```bash
python3 -m http.server 8000 -d tools/webui   # then open http://localhost:8000
```

(Any static host works the same way; nothing leaves the browser.)

Sections map 1:1 onto the CLI: connect, info/auth, get/set for the same
SETTINGS table, flash dump, OTA flash, plus the file-side tools (`cfw.py`
patching and `tone_tool.py` replacement) running client-side on a `.up` you
pick. `node tools/webui/selftest.mjs` replays fixed vectors to confirm the JS
produces byte-identical frames to `huilian/proto.py`.

Same caveat: hardware-unverified. The OTA section refuses to write the index
until every payload chunk is acknowledged, and `side=both` re-picks the port
between ears because the bud reboots after finalize.
