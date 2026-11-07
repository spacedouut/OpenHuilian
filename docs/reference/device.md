# Device: H3Pro Max3

Identity, the flash layout and what is in the stock 2607061716 image.

## Identity

What StarFun's "More" screen shows. The app reads it live over Bluetooth (`C0 04` "product model")
and doesn't cache it.

| Field | Value |
|---|---|
| Product number | `H3Pro Max3` |
| Chip model | `H3Pro` |
| Manufacturer | `377Youth·心动版` |
| Firmware version | `2607061716` (build stamp 2026-07-06 17:16) |

The same screen shows a production date and the bud's Bluetooth MAC, which differ per pair.

Replica-community naming: "V5.4 = Huilian 377", "V7 = Huilian 377H3". The `H3Pro` / `377Youth`
strings match 377H3.

Use StarFun **2.0.7.016**. 2.0.7.017 refuses these buds with "This device is not supported, please
replace it" ([the app](../explanation/the-app-and-servers.md)).

## The OTA check

Tapping **Check Firmware** sends:

```
GET https://ota.starfun.fun/api/v1/_/appversions/update
      ?package=h3promax3
      &version=2607061716
      &deviceid=<the bud's Bluetooth MAC>
Authorization: <tenant JWT>

→ HTTP 204 No Content
```

* `package` is the product name lower-cased with spaces removed. That's the server key.
* **204 means "no update"**, not an auth failure. Other `version` values (including `0`) also get
  204, while known packages such as `a10` return JSON with a download URL.
* The catalog ([catalog](../explanation/the-app-and-servers.md#the-public-catalog)) has no `h3promax3` entry, and its newest image (June 2025) is
  older than this firmware.

## Flash layout

### The partition index

Read from flash `0x3000`. Same 16-byte-record layout as every catalog image ([.up format](up-format.md)).

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
Unlike the 2 MiB H2S Turbo there is essentially **no free flash**, TONE has ~1 KiB of slack before
EQ2P, and only ~4.7 KiB sit between OTAP's end and PSMP. Growing prompts on this device means
shrinking something else. (Correction, [research](../research/README.md): the ~53 KB of `00` padding
between EQ2P and OTAP is also claimable if you repartition within `0x4000..0xD2000` - OTAP and
PSMP stay pinned, everything else just moves in the index.)

### The stock image in this repo

[`tools/build_up.py`](../../tools/build_up.py) wraps `flash[0 : end-of-OTAP]` in the standard
256-byte `CONFIG` header (body length, CRC16 of body, `55 AA` trailer). It passes
`tone_tool.py verify` ("ALL CRCs VALID"). Two caveats:

* The **chip-name string at header `+0x16` is left empty**. It isn't stored in flash, and there's
  no official H3Pro `.up` to copy it from. The bud's updater never sees the header
  ([updater](../research/updater-otap.md)); the desktop flasher does read it ([vendor tools](../explanation/vendor-tools-and-prior-art.md)).
* PSMP is **not** in the committed image. It holds per-bud data: the Bluetooth address,
  `authorization_code`, both ear serials, the Apple `air_adv_key` and the paired phone's address.
  Keep your own dump private.

## What's in the image

Everything below is from `firm_strings.txt` / the extracted partitions in
[`data/partitions-h3promax3/`](../../data/partitions-h3promax3/).

**Build identity.** FIRM carries `377Super PRO3` and `Super2026+`, against `377 Super++` in the
newest catalog image and `LHK-SL6800-TEST` in the older ones.

**The container conventions carried over 1:1.** Same `HLKJ` body, same index format at `0x3000`,
same partition names, same CRC. Every offline tool in this repo works on it unchanged.

**TONE, 18 prompts (h2sturbo has 17).** Same `[size][name\0]` directory. New: `game_mode_close.mp3`.
All 18 list cleanly with `tone_tool.py list`; replacement works exactly as in [TONE](tone.md),
but the partition is packed 84,903 / 84,903 and only ~1 KiB of flash follows before EQ2P.

**EQ2P, 4,172 bytes, a new layout with 7 profiles.** Header `SLEQ 02 07`, then 7 `u16` record
counts (92, 71 ×6), 28-byte header, then 8-byte records `[kind u8][param u8][band u16][f32]`:

| param | meaning |
|---|---|
| `0x00` / `0x01` / `0x02` | frequency Hz / Q / gain dB |
| `0x03` | band enable (1/0) |
| `0xFC` | always 1.0, filter type? |
| `0xDD` | profile pre-gain (−4.8 … −9.73 dB) |
| `0x3C–0x41` | page 0 only, bands 0–3, a second filter block with thresholds 0/−9/−30/−50 dB (looks like a 4-stage compressor/limiter, not an EQ) |

Page 1 is **byte-for-byte the H2S Turbo factory curve** (80/130/240/420/900/2421/4100/6100/7990/
9750/12200 Hz, 12.2 kHz +6.3 dB) padded to 14 bands, the same house sound. Pages 2–6 are five
alternative 14-band curves (bass-heavy, vocal, treble-cut and so on), almost certainly the presets
behind StarFun .017's "EQ adjustment (only some models)" and the `eq_preset_cur_num` NV key. Page 0 is a
different, more aggressive 14-band curve with the extra compressor block. Full decoded table:
[`eq2p_profiles.txt`](../../data/partitions-h3promax3/eq2p_profiles.txt). ANC/talk-through pages 51–57
are **still absent**, consistent with [ANC](../explanation/anc-and-transparency.md): filters live in FIRM code.

**SENC** is identical in size and CRC to the H2S Turbo one (`0x77AA`).

**AAP / AirPods layer.** Still `AT+XAPL=0042-0887-0100,2`, still the 2007 Apple copyright string, the
`devmotion6` AccessoryService plist and its HID report descriptor are present. New string vs. the
catalog build: **`AirPods Pro2`** alongside `AirPods` / `AirPods Pro`. The BLE model literal `0E 20`
still appears (50 hits, most are code). The pop-up template is the one at FIRM `0xC4BF58`
([research](../research/README.md)). ANC AT commands are unchanged (`+ANCFFG/+ANCFBG/+ANCAG/
+ANCDG/+ANCTEST`), plus NV keys `anc_mode_sel`, `anc_mode_phone_sel`. Head-tracking markers
(`task motion`, `taskB motion`, `air motion timer`) are present; no `spatial`/`conversation`/`adaptive`
strings.

**NV keys.** The key names this firmware uses are listed in [PSMP](psmp.md).
