# hl - a native CLI for the buds

`tools/hl` (package `tools/huilian/`) talks to the H3Pro Max3 / 377H3 buds
directly over Bluetooth SPP, with no StarFun install and no Frida. It implements
the `C0` command channel and the `55AA` OTA transport itself ([18](18-firm-walkthrough.md),
[06](06-bt-ota-protocol.md)).

## Getting a port

Pair the buds to the computer, then tell the tool where the SPP service is. The
buds hold one SPP session at a time, so the phone's Bluetooth has to be off.

| OS | How | `--port` |
|---|---|---|
| Linux, raw socket | nothing to set up: `bluetoothctl pair` + `trust`, then give the address. Opens an RFCOMM socket on channel 3 (the buds' `SL_SPP` record), no `rfcomm bind`, no root, no pyserial | `AA:BB:CC:DD:EE:FF` (or `...:FF:3`) |
| Linux, serial | `rfcomm bind /dev/rfcomm0 <bt-addr> 3`, and make the device readable | `/dev/rfcomm0` |
| Windows | pairing creates an "Outgoing" COM port | `COM6` |
| macOS | `/dev/cu.*` serial device appears on pair | `/dev/cu.H3Pro-SPP` |

The serial forms need `pyserial`; the address form has no dependencies. Channel
3 matters: `rfcomm bind` without a channel picks 1, which is the buds' HFP
channel and answers `AT+BRSF` instead of `C0` frames.

## Commands

```
hl --port PORT info             model, version, battery, in-ear, side, link, serials
hl --port PORT auth             run the C0 01/02 handshake and check the reply
hl --port PORT get <name>       read a setting
hl --port PORT set <name> <v>   write a setting (mirrored to the peer bud)
hl --port PORT read 0x0 0x100000 out.bin   dump flash via C0 83 (200 B/reply cap)
hl --port PORT ota file.up      flash a .up through the 55AA path, both buds
hl --port PORT leave-ota        get buds stuck in the updater back into FIRM
hl --port BTADDR dash           local web dashboard for live tuning (see below)
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

## OTA

`hl ota` runs the app's flow against real buds (verified on an H3Pro Max3 pair,
both directions, stock and patched images):

1. `80` enter. FIRM relays it to the peer bud, so both buds reboot into the
   updater (OTAP). Whichever bud grabs the SPP link next is the one every
   following frame lands on. OTAP ignores the side byte in requests and
   answers with its own (`11`/`22`).
2. `81` prepare. The bud erases the target region first and answers when it is
   done, which takes longer than the other steps (the tool waits 30 s).
3. `82` declare (CRC16 + length over `0x3000`..OTAP), `83` 512-byte writes at
   absolute flash addresses (about 4 KB/s over RFCOMM, 3 to 4 minutes per
   bud), the partition index last, `84` finalize. A `00` status means the CRC
   matched and the new index is committed; anything else means the old index
   was put back, and the tool stops there.
4. `04` leave: clears the boot-to-OTAP flag and reboots into FIRM. This step is
   not optional. Without it both buds stay in the updater: they still pair and
   answer `C0 04/05/09/51/83`, but not `C0 0A` (in-ear) or the serial reads,
   have no A2DP/AirPods layer, and show up as a generic Bluetooth device.
5. Reconnect. If the bud that answers is still in OTAP it is the other one;
   flash it the same way. If FIRM answers (the first bud came back and holds
   the link), the tool sends `80` again so the remaining bud enters the
   updater, then flashes whoever answers. `--side one` stops after one bud.

The payload region is FIRM through the last partition actually stored in the
image; a PSMP index entry with no bytes in the file is skipped, so per-unit
data is never written.

### Stuck in the updater

`hl leave-ota` is the recovery for buds left in OTAP (an interrupted flash, or
an older tool that stopped after `84`). OTAP's `04` handler only clears the
flag and reboots when the bud has no linked peer; a linked master instead
relays the request to its peer and follows 2 s later. Sending `04` to an OTAP
bud whose peer is already back in FIRM drags that peer back into the updater,
so the command sends `04` only when the answering bud is in OTAP, rechecks
after the reboot, and tells you when the remaining bud needs the other one
powered off (in the case, lid closed) to be reached alone. Done means `C0 0A`
answers and `C0 12` reads `00` (both buds linked; `02` is no peer). The flag
page itself is at `OTAP.addr + ((OTAP.len >> 12) + 1) * 0x1000` (`0xFB000` on
the H3Pro layout): `AA 55 00 00` set, `00 00 00 00` cleared, readable with
`hl read 0xfb000 4 flag.bin`.

## The tuning dashboard

`hl --port AA:BB:CC:DD:EE:FF dash` starts a stdlib-only HTTP server on
`127.0.0.1:8765` (`--listen host:port` to change it) and serves one page:
battery, in-ear, peer link, ANC mode, the C0 toggles and gestures, and sliders
for the factory ANC gains. It needs the Bluetooth address form of `--port`
because it opens two links.

* **C0, channel 3.** Same reads and writes as `hl get`/`set`, plus the toggles
  StarFun names in `CMDConfig` (`68` spatial audio, `66` audio type, `67` game
  check, `85` custom volume, `86` talk sensitive, `87` low/high volume). The
  last three have no known read command, so the page shows what was last set.
* **HFP, channel 1.** Live ANC gains go over `+NTC=<side><op><B|F><6 digits>`
  (see [11](11-anc-transparency.md)): op `3` sets feedforward (`F`) or
  feedback (`B`) gain to `digits/10000` (1.0000 is stock), `5` reads one back,
  `4` writes both to NV `anc info`. `L` hits the connected bud, `R` is relayed
  to the peer. The dashboard sends these as `+NTC=...` lines; "Read gains"
  fills the sliders with what the buds report, "Save to flash" persists them.
  The buds are the headset on this channel, so the dashboard plays phone: it
  answers their AT commands (`BRSF`, `CIND`, `CMER`, `XAPL`...) to bring up
  the service level connection first. If desktop audio (PipeWire, BlueZ)
  already holds HFP, the channel is busy. "Release HFP" disconnects only the
  Handsfree profile through BlueZ `DisconnectProfile`, and A2DP stays up.

Move in small steps and keep the buds out of your ears for big feedback
changes, since too much feedback gain can squeal. Unsaved gains reset on
reboot.

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
