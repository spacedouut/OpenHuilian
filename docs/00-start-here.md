# 00 · Start here

## What this is about

A pair of **H3Pro Max3** true-wireless earbuds. They are an AirPods-Pro-lookalike built on a
Bluetooth SoC from **Huilian (慧联 / HLKJ)**, whose chips are also sold under the
**Smartlink / SL68xx** name and whose company entity appears to be **Shenju (珠海绅聚 / shenjugroup.com)**.
The companion app is **StarFun** (`com.fun.app`), which is the generic control app for Huilian
TWS products sold by many resellers.

The question that started everything: *can we get the firmware for these buds and, eventually,
change it?* Along the way we ended up decoding most of the platform.

## Who's who (glossary)

| Term | What it means here |
|---|---|
| **Huilian / 慧联 / HLKJ** | The chip/firmware vendor. `HLKJ` (慧联科技) is the magic string in every firmware body. |
| **Smartlink / SL6801 / SL6806** | Chip family names. Every image in the public catalog claims `SL6801`. |
| **377 / 377H3 / H3Pro** | Newer silicon generation. The H3Pro Max3 reports chip `H3Pro`; the replica community calls it "Huilian 377H3". |
| **Shenju / 绅聚 / shenjugroup.com** | Company behind the flasher tool and a second OTA server used by StarFun. |
| **StarFun** | The phone app. Tenant/account name inside the app is `yiguo`. |
| **`.up` file** | The firmware container format (starts with `CONFIG`). Full image, not a patch. |
| **OTA** | Over-the-air update: the app downloads a `.up` and streams it to the buds over Bluetooth SPP. |
| **FIRM / TONE / EQ2P / SENC / OTAP / PSMP** | The partitions inside a `.up`. See [04](04-up-format.md). |
| **AAP** | Apple Accessory Protocol — the buds implement an "AAP Server" to look like AirPods. |
| **CFW** | Custom firmware. |

## Safety & ground rules

1. **Nothing has been written to the earbuds.** All experiments are on downloaded files or on the
   read-only flash dump ([16](16-live-flash-dump.md)).
2. **An SL6801 image must never be flashed to an H3Pro / 377H3 device.** Different silicon
   generation; the chip name in the header would differ, and the bootloader's chip-name check
   (see [13](13-open-source-tooling.md)) exists precisely to stop this — but do not rely on it.
3. Modified images must have **both** the partition CRC and the outer container CRC recomputed
   ([05](05-crc-and-integrity.md)); a stale outer CRC is exactly the failure mode seen in one
   reseller image in the public catalog.
4. Credentials (the app's tenant login, JWTs, ADB pairing codes) are intentionally **not** stored
   in this repo. `tools/pull_ota.py` reads them from environment variables.

## The story in six steps

1. **Identify the buds.** StarFun on an Android device (an Echo Show running LineageOS, driven over
   ADB via Tailscale) showed: product `H3Pro Max3`, chip `H3Pro`, manufacturer `377Youth·心动版`,
   firmware `2607061716`. Tapping "Check firmware" fired
   `GET ota.starfun.fun/api/v1/_/appversions/update?package=h3promax3&version=2607061716&deviceid=…`
   → **204 No Content**. → [01](01-device.md)
2. **Log in as the app.** The APK carries a tenant login; with it the whole OTA catalog can be
   listed: 30 records, 16 products, 24 `.up` images, **no `h3promax3`**, newest June 2025.
   → [02](02-starfun-app.md), [03](03-ota-catalog.md)
3. **Decode the images.** `CONFIG` header → `HLKJ` body → partition index → payloads. Integrity is
   CRC16 only. Voice prompts, EQ and sensor tables are plain data. → [04](04-up-format.md) … [09](09-psmp-nvds.md)
4. **Decode the transport and the "AirPods" layer.** The app's bundled `com.shenju.ota` SDK gives the
   full Bluetooth OTA protocol; the firmware contains a real AAP server, Apple SDP/HID records and a
   BLE proximity-pairing template. → [06](06-bt-ota-protocol.md), [10](10-aap-airpods.md), [11](11-anc-transparency.md)
5. **Find the ecosystem.** Public GitHub has a USB boot-ROM dumper (`smartlink_flash`), a bootloader
   reverse-engineering effort (`sl6806`) and a shipped custom firmware (OpenPod) for the same
   chip family — and OpenPod's git history contained Shenju's **official factory flasher**, which
   decompiled cleanly to Python. → [12](12-shenju-flasher.md), [13](13-open-source-tooling.md)
6. **Read the real firmware off the buds.** With the catalog empty for `h3promax3`, the app's own
   `C0 83` flash-read command was driven through StarFun's authenticated Bluetooth socket (Frida on
   the rooted Echo Show) to dump the whole 1 MiB flash. Result: a CRC-valid, genuine
   **H3Pro Max3 2607061716** image, same container conventions as SL6801. → [16](16-live-flash-dump.md)

## Status board

| Area | State |
|---|---|
| Device identity & exact OTA request | **[confirmed]** captured live |
| StarFun auth + catalog enumeration + downloads | **[confirmed]** working (`tools/pull_ota.py`) |
| `.up` container format | **[confirmed]** on 24/24 images, and against vendor source |
| CRC algorithm (partition + container) | **[confirmed]** CRC16/CCITT-FALSE, matches vendor `up_parser.py` |
| Bluetooth OTA wire protocol | **[source]** fully read from the app SDK |
| TONE replace + repack round-trip | **[confirmed]** offline |
| EQ2P edit + repack round-trip | **[confirmed]** offline |
| PSMP / NV record format | partially — keys known, binary layout **not** fully decoded |
| AAP surface | **[confirmed]** what's present; behaviour **[unverified]** |
| ANC/transparency tunables | gains **[source]**; filters compiled in FIRM **[confirmed]** absent from data |
| Bootloader accepts CRC-only images | **[source]** for SL6806 (public RE), **[unverified]** for H3Pro |
| Physical write path into earbuds | **[inferred]** UART boot-ROM via case pins; **[unverified]** |
| **A genuine H3Pro Max3 / 377H3 image** | **[confirmed]** read off the buds, all CRCs valid — [16](16-live-flash-dump.md) |
| Read-only flash dump path via the app's socket | **[confirmed]** ~1.1 KB/s, 200 B/reply, `tools/flashdump.py` |
