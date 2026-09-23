# 16 · Reading the real H3Pro Max3 firmware off the buds (live flash dump)

**The blocker is gone.** Instead of waiting for StarFun to publish an `h3promax3` OTA, the firmware
was read straight out of the earbuds over Bluetooth, using StarFun's own already-authenticated
connection. The result is a complete, CRC-valid, genuine **H3Pro Max3 firmware 2607061716** image:
[`firmware/h3promax3/h3promax3_2607061716_live.up`](../firmware/h3promax3/h3promax3_2607061716_live.up).

Nothing was written to the device. The only command ever sent was a flash *read*.

## The idea

The app's OTA SDK has a raw flash-read command it uses before every update to preserve the user's
EQ and voice-prompt partitions ([06](06-bt-ota-protocol.md)):

```
C0 83 <flash address, u32 LE> <length, u32 LE>          (normal command channel, type 1, no CRC8)
reply: C0 83 <address> <length> <data…>
```

`OtaCmdConfig.getReadFlashCmdArray()` builds it; `BtOtaHelper` first reads the partition index at
`0x3000` (200 bytes, `INDEX_START_ADDRESS = 12288`) and then TONE/EQ2P in 100-byte blocks. Nothing
stops the same call from being pointed at address 0 with the whole flash as the range.

The `C0` command channel sits behind a keyed challenge/response in a native library. Rather than
reproduce it, we let StarFun do the handshake as normal and then **borrow its socket**: Frida
attached to the running app on the rooted Echo Show, called `CMDConfig.getReadFlashCmdArray(addr,len)`
+ `BtClient.sendBytes(cmd, 1)` in a loop, and hooked `BtBase.notifyUI` to catch every `C083…`
reply. **[confirmed]**

## Setup that worked

| Piece | Value |
|---|---|
| Host device | Echo Show 5 (2nd gen) on LineageOS 18.1 / Android 11, rooted, wireless ADB over Tailscale |
| App | StarFun `com.fun.app` **2.0.7.016** (the "377H3" build — .017 rejects these buds) |
| Frida | server **16.5.9** (Android ARM). 17.x attached but the agent connection dropped and killed the app. |
| Tools | [`tools/flashdump.js`](../tools/flashdump.js) (agent) + [`tools/flashdump.py`](../tools/flashdump.py) (driver) |
| Read size | 100 / 200 / 240 / 500 requested → device returns **at most 200 bytes** per reply; 200 used |
| Throughput | ~1.1 KB/s → full 1 MiB in ~15.5 min (5,243 replies, zero gaps, zero retries needed) |

```bash
# on the Echo Show: frida-server 16.5.9 listening on 0.0.0.0:27042, StarFun open, buds connected
FRIDA_HOST=<echo-show-ip>:27042 python3 tools/flashdump.py 0x3000 200      index.bin   200
FRIDA_HOST=<echo-show-ip>:27042 python3 tools/flashdump.py 0x0    0x100000 flash.bin   200
python3 tools/build_up.py flash.bin h3promax3_live.up          # parse index, check CRCs, wrap as .up
python3 tools/tone_tool.py verify h3promax3_live.up            # independent second check
```

## What came back — the live partition index **[confirmed]**

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

**All five stored partition CRCs recompute correctly with CRC16/CCITT-FALSE** — the same algorithm
as the SL6801 images, and a strong sign the dump has no bit errors.

Flash map: a **1 MiB class** part. `0x0000` carries an `HLKJ` header, `0x3000` the index, the gap
after FIRM is `00`-filled, the gap after OTAP is erased `FF`, PSMP occupies the last 16 KiB.
Unlike the 2 MiB H2S Turbo there is essentially **no free flash** — TONE has ~1 KiB of slack before
EQ2P, and only ~4.7 KiB sit between OTAP's end and PSMP. Growing prompts on this device means
shrinking something else.

## The reconstructed `.up`

[`tools/build_up.py`](../tools/build_up.py) wraps `flash[0 : end-of-OTAP]` in the standard
256-byte `CONFIG` header (body length, CRC16 of body, `55 AA` trailer). It passes
`tone_tool.py verify` ("ALL CRCs VALID"). Two honest caveats:

* The **chip-name string at header `+0x16` is left empty**. It is not stored anywhere in flash and
  we have never seen a real 377H3 `.up`, so we do not know whether Huilian writes `H3Pro`,
  `SL68xx` or something else there. StarFun's BT OTA path only checks the `CONFIG` magic
  ([06](06-bt-ota-protocol.md)); the desktop flasher and possibly the bootloader do look at it
  ([12](12-shenju-flasher.md), [13](13-open-source-tooling.md)). **[unverified]**
* PSMP is intentionally **excluded** from the committed image and from this repo: it contains the
  owner's Bluetooth address, `authorization_code`, both ear serial numbers, the Apple `air_adv_key`
  and the phone's address. The raw 1 MiB dump exists only on the owner's side.

## First look inside the real thing

Everything below is from `firm_strings.txt` / the extracted partitions in
[`data/partitions-h3promax3/`](../data/partitions-h3promax3/).

**Build identity.** FIRM carries `377Super PRO3` and `Super2026+` — vs. `377 Super++` in the newest
catalog image and `LHK-SL6800-TEST` in the older ones. So this is the third named generation seen,
and it is a July-2026 build (`2607061716` = 26-07-06 17:16). PSMP's `device_id` record begins
`XCWX01TWS---247-------H3PROMAX3` — the **247** family tag the Shenju PSM editor lists
([12](12-shenju-flasher.md)), so 247Youth/377Youth are one product line.

**The container conventions carried over 1:1.** Same `HLKJ` body, same index format at `0x3000`,
same partition names, same CRC. Every offline tool in this repo works on it unchanged.

**TONE — 18 prompts (h2sturbo has 17).** Same `[size][name\0]` directory. New: `game_mode_close.mp3`.
All 18 list cleanly with `tone_tool.py list`; replacement works exactly as in [07](07-tone-sfx.md),
but the partition is packed 84,903 / 84,903 and only ~1 KiB of flash follows before EQ2P.

**EQ2P — 4,172 bytes, a new layout with 7 profiles.** Header `SLEQ 02 07`, then 7 `u16` record
counts (92, 71 ×6), 28-byte header, then 8-byte records `[kind u8][param u8][band u16][f32]`:

| param | meaning **[inferred]** |
|---|---|
| `0x00` / `0x01` / `0x02` | frequency Hz / Q / gain dB |
| `0x03` | band enable (1/0) |
| `0xFC` | always 1.0 — filter type? |
| `0xDD` | profile pre-gain (−4.8 … −9.73 dB) |
| `0x3C–0x41` | page 0 only, bands 0–3 — a second filter block with thresholds 0/−9/−30/−50 dB (looks like a 4-stage compressor/limiter, not an EQ) |

Page 1 is **byte-for-byte the H2S Turbo factory curve** (80/130/240/420/900/2421/4100/6100/7990/
9750/12200 Hz, 12.2 kHz +6.3 dB) padded to 14 bands — the same house sound. Pages 2–6 are five
alternative 14-band curves (bass-heavy, vocal, treble-cut, …) — almost certainly the presets behind
StarFun .017's "EQ adjustment (only some models)" and the `eq_preset_cur_num` NV key. Page 0 is a
different, more aggressive 14-band curve with the extra compressor block. Full decoded table:
[`eq2p_profiles.txt`](../data/partitions-h3promax3/eq2p_profiles.txt). ANC/talk-through pages 51–57
are **still absent** — consistent with [11](11-anc-transparency.md): filters live in FIRM code.

**SENC** is identical in size and CRC to the H2S Turbo one (`0x77AA`).

**AAP / AirPods layer.** Still `AT+XAPL=0042-0887-0100,2`, still the 2007 Apple copyright string, the
`devmotion6` AccessoryService plist and its HID report descriptor are present. New string vs. the
catalog build: **`AirPods Pro2`** alongside `AirPods` / `AirPods Pro`. The BLE model literal `0E 20`
still appears (50 hits, most are code); which one is the pop-up template needs the same locate-by-
context pass as [10](10-aap-airpods.md). ANC AT commands are unchanged (`+ANCFFG/+ANCFBG/+ANCAG/
+ANCDG/+ANCTEST`), plus NV keys `anc_mode_sel`, `anc_mode_phone_sel`. Head-tracking markers
(`task motion`, `taskB motion`, `air motion timer`) are present; no `spatial`/`conversation`/`adaptive`
strings.

**NV keys seen in the live PSMP** (names only; values are private): `authorization_code`,
`authorization_code_length`, `bt_addr`, `ble_addr`, `bt_addr_backup`, `addr_backup_flag`, `device_id`,
`freq_drift`, `paired_flag`, `bootup_flag`, `ear_type`, `vc30fx_oscclk_freq`, `product_mode`,
`date_of_manufacture`, `product_id`, `sn_l_info`, `sn_r_info`, `sn_info`, `air_en`, `air_reset`,
`air_link`, `air_adv_key`, `air_pair`, `air_phone_addr`, `air_callctrl_setting`,
`air_volumectrl_setting`, `air_audio_setting`, `air_clean`, `kws_en`, `anc_mode_sel`,
`anc_mode_phone_sel`, `link_phone_type`, `eq_preset_cur_num`, `eq_ud_gain`, `bt_name`, `bt_vol`,
`bat_level`, `link_info`. `psmp_tool.py` parses the live log without errors (76 records, log ends at
`0xD1F` of `0x4000`) — the record format is the same as SL6801's.

## What this changes for the roadmap

* The gating item in [15](15-cfw-roadmap.md) — **"a genuine 377H3 base image"** — is done.
* The app's flash-read also gives a **free, safe verification path**: after any future write, the
  same `C0 83` loop can read the flash back and diff it against what was sent.
* The still-open acceptance question (does the H3Pro OTAP/bootloader take a CRC-only image with a
  new timestamp?) can now be studied offline on the real OTAP (`0xD2000`, 167,248 bytes — the same
  length as every SL6801 OTAP, so probably the same updater).
* Any write is still a **write to real hardware with no proven recovery path**. Nothing here
  authorises one.
