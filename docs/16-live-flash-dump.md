# 16 · Reading flash over Bluetooth, and what's in 2607061716

[`firmware/h3promax3/h3promax3_2607061716_live.up`](../firmware/h3promax3/h3promax3_2607061716_live.up)
is a complete, CRC-valid H3Pro Max3 image read off the buds with the app's flash-read command. This
page covers how to do the read and what's in the image. The read only ever sends `C0 83`; it never
writes.

## The read command

The app's OTA SDK has a raw flash-read command it uses before every update, to preserve the user's
EQ and voice-prompt partitions ([06](06-bt-ota-protocol.md)):

```
C0 83 <flash address, u32 LE> <length, u32 LE>          (normal command channel, type 1, no CRC8)
reply: C0 83 <address> <length> <data…>
```

`OtaCmdConfig.getReadFlashCmdArray()` builds it; `BtOtaHelper` first reads the partition index at
`0x3000` (200 bytes, `INDEX_START_ADDRESS = 12288`) and then TONE/EQ2P in 100-byte blocks. Nothing
stops the same call from being pointed at address 0 with the whole flash as the range.

The `C0` channel sits behind the app's challenge/response, which turned out to be a 16-bit LFSR.
`tools/hl read` reimplements it and reads flash over a plain RFCOMM socket with no app
([20](20-hl-cli.md)). The older route below reuses the app instead.
[`tools/flashdump.js`](../tools/flashdump.js) runs inside StarFun with Frida after the app has
connected. It calls `CMDConfig.getReadFlashCmdArray(addr,len)` and
`BtClient.sendBytes(cmd, 1)` in a loop and hooks `BtBase.notifyUI` to catch the `C083…` replies.
[`tools/flashdump.py`](../tools/flashdump.py) drives it.

## What you need

| Piece | Notes |
|---|---|
| Android host | Rooted, buds paired, StarFun open and connected |
| App | StarFun `com.fun.app` **2.0.7.016**. 2.0.7.017 rejects these buds. |
| Frida | **16.5.9** on both sides. 17.x attaches, then drops the agent and kills the app. |
| Read size | The buds return at most **200 bytes** per reply, whatever you ask for |
| Speed | ~1.1 KB/s, so the full 1 MiB takes about 16 minutes |

```bash
# frida-server 16.5.9 on the phone, on loopback (its default, 127.0.0.1:27042).
# Forward it over ADB rather than exposing 27042 on the network:
adb forward tcp:27042 tcp:27042
FRIDA_HOST=127.0.0.1:27042 python3 tools/flashdump.py 0x3000 200      index.bin   200
FRIDA_HOST=127.0.0.1:27042 python3 tools/flashdump.py 0x0    0x100000 flash.bin   200
python3 tools/build_up.py flash.bin h3promax3_live.up          # parse index, check CRCs, wrap as .up
python3 tools/tone_tool.py verify h3promax3_live.up            # second check
```

The same loop works as a read-back check after any future write.

## The partition index

Read from flash `0x3000`. Same 16-byte-record layout as every catalog image ([04](04-up-format.md)).

```
count = 6      version = 0x9B649AD4 = 2607061716   (exactly what StarFun displays)

FIRM  addr 0x00004000  len 0x0A9C54 (695,380)  crc 0x6BC3  OK
SENC  addr 0x000AE000  len 0x000808 (  2,056)  crc 0x77AA  OK   (byte-identical CRC to h2sturbo's SENC)
TONE  addr 0x000AF000  len 0x014BA7 ( 84,903)  crc 0x6386  OK
EQ2P  addr 0x000C4000  len 0x00104C (  4,172)  crc 0xACF5  OK
OTAP  addr 0x000D2000  len 0x028D50 (167,248)  crc 0xC5DD  OK
PSMP  addr 0x000FC000  len 0x004000 ( 16,384)  crc 0       declared only (runtime NV store)
```

**All five stored partition CRCs recompute correctly with CRC16/CCITT-FALSE**, the same algorithm
as the SL6801 images. A bad read would show up here.

Flash map: a **1 MiB class** part. `0x0000` carries an `HLKJ` header, `0x3000` the index, the gap
after FIRM is `00`-filled, the gap after OTAP is erased `FF`, PSMP occupies the last 16 KiB.
Unlike the 2 MiB H2S Turbo there is essentially **no free flash** — TONE has ~1 KiB of slack before
EQ2P, and only ~4.7 KiB sit between OTAP's end and PSMP. Growing prompts on this device means
shrinking something else. (Correction, [21](21-night-shift.md): the ~53 KB of `00` padding
between EQ2P and OTAP is also claimable if you repartition within `0x4000..0xD2000` - OTAP and
PSMP stay pinned, everything else just moves in the index.)

## The reconstructed `.up`

[`tools/build_up.py`](../tools/build_up.py) wraps `flash[0 : end-of-OTAP]` in the standard
256-byte `CONFIG` header (body length, CRC16 of body, `55 AA` trailer). It passes
`tone_tool.py verify` ("ALL CRCs VALID"). Two caveats:

* The **chip-name string at header `+0x16` is left empty**. It isn't stored in flash, and there's
  no official H3Pro `.up` to copy it from. The bud's updater never sees the header
  ([17](17-firmware-internals.md)); the desktop flasher does read it ([12](12-shenju-flasher.md)).
* PSMP is **not** in the committed image. It holds per-bud data: the Bluetooth address,
  `authorization_code`, both ear serials, the Apple `air_adv_key` and the paired phone's address.
  Keep your own dump private.

## What's in the image

Everything below is from `firm_strings.txt` / the extracted partitions in
[`data/partitions-h3promax3/`](../data/partitions-h3promax3/).

**Build identity.** FIRM carries `377Super PRO3` and `Super2026+`, against `377 Super++` in the
newest catalog image and `LHK-SL6800-TEST` in the older ones.

**The container conventions carried over 1:1.** Same `HLKJ` body, same index format at `0x3000`,
same partition names, same CRC. Every offline tool in this repo works on it unchanged.

**TONE — 18 prompts (h2sturbo has 17).** Same `[size][name\0]` directory. New: `game_mode_close.mp3`.
All 18 list cleanly with `tone_tool.py list`; replacement works exactly as in [07](07-tone-sfx.md),
but the partition is packed 84,903 / 84,903 and only ~1 KiB of flash follows before EQ2P.

**EQ2P — 4,172 bytes, a new layout with 7 profiles.** Header `SLEQ 02 07`, then 7 `u16` record
counts (92, 71 ×6), 28-byte header, then 8-byte records `[kind u8][param u8][band u16][f32]`:

| param | meaning |
|---|---|
| `0x00` / `0x01` / `0x02` | frequency Hz / Q / gain dB |
| `0x03` | band enable (1/0) |
| `0xFC` | always 1.0 — filter type? |
| `0xDD` | profile pre-gain (−4.8 … −9.73 dB) |
| `0x3C–0x41` | page 0 only, bands 0–3 — a second filter block with thresholds 0/−9/−30/−50 dB (looks like a 4-stage compressor/limiter, not an EQ) |

Page 1 is **byte-for-byte the H2S Turbo factory curve** (80/130/240/420/900/2421/4100/6100/7990/
9750/12200 Hz, 12.2 kHz +6.3 dB) padded to 14 bands — the same house sound. Pages 2–6 are five
alternative 14-band curves (bass-heavy, vocal, treble-cut and so on), almost certainly the presets
behind StarFun .017's "EQ adjustment (only some models)" and the `eq_preset_cur_num` NV key. Page 0 is a
different, more aggressive 14-band curve with the extra compressor block. Full decoded table:
[`eq2p_profiles.txt`](../data/partitions-h3promax3/eq2p_profiles.txt). ANC/talk-through pages 51–57
are **still absent** — consistent with [11](11-anc-transparency.md): filters live in FIRM code.

**SENC** is identical in size and CRC to the H2S Turbo one (`0x77AA`).

**AAP / AirPods layer.** Still `AT+XAPL=0042-0887-0100,2`, still the 2007 Apple copyright string, the
`devmotion6` AccessoryService plist and its HID report descriptor are present. New string vs. the
catalog build: **`AirPods Pro2`** alongside `AirPods` / `AirPods Pro`. The BLE model literal `0E 20`
still appears (50 hits, most are code). The pop-up template is the one at FIRM `0xC4BF58`
([21](21-night-shift.md)). ANC AT commands are unchanged (`+ANCFFG/+ANCFBG/+ANCAG/
+ANCDG/+ANCTEST`), plus NV keys `anc_mode_sel`, `anc_mode_phone_sel`. Head-tracking markers
(`task motion`, `taskB motion`, `air motion timer`) are present; no `spatial`/`conversation`/`adaptive`
strings.

**NV keys.** The key names this firmware uses are listed in [09](09-psmp-nvds.md).
