# OpenHuilian — Huilian / Smartlink TWS research (H3Pro Max3, 377H3, SL6801)

A wiki-style archive of everything learned while trying to obtain, decode and eventually
modify the firmware of a pair of **H3Pro Max3** earbuds (Huilian **377H3** chip, sold as an
AirPods-Pro-style replica, controlled by the **StarFun** Android/iOS app).

Nothing here has been flashed to any earbud. Experiments were done offline on downloaded firmware
images, plus one strictly **read-only** live acquisition of the H3Pro Max3's flash over Bluetooth
([16](docs/16-live-flash-dump.md)). Read [Safety & ground rules](docs/00-start-here.md#safety--ground-rules) first.

## How to read this

Start at **[docs/00-start-here.md](docs/00-start-here.md)** — a plain-English overview of what the
buds are, what we know, what we still don't, and how the pieces fit. Each page in `docs/` is
self-contained and marks every claim as one of:

| Tag | Meaning |
|---|---|
| **[confirmed]** | Seen directly in tool output, a live capture, or vendor source code |
| **[source]** | Read from decompiled app / vendor code or a public repo |
| **[inferred]** | Our interpretation; consistent with evidence but not directly observed |
| **[unverified]** | Plausible, would need a device or a 377H3 image to prove |

## Wiki index

| # | Page | One-liner |
|---|---|---|
| 00 | [Start here](docs/00-start-here.md) | Overview, glossary, safety, status board |
| 01 | [The device: H3Pro Max3](docs/01-device.md) | Exact identity, live OTA request capture, why the server says "no update" |
| 02 | [StarFun app](docs/02-starfun-app.md) | Versions, servers, auth flow, hidden local-file OTA path |
| 03 | [OTA catalog](docs/03-ota-catalog.md) | All 24 public firmware images and what they are |
| 04 | [`.up` container format](docs/04-up-format.md) | Header, HLKJ body, partition index, flash map |
| 05 | [CRCs & integrity model](docs/05-crc-and-integrity.md) | The only "security" there is: CRC16/CCITT-FALSE, no signing. Confirmed on the catalog images, and on H3Pro from its own updater code ([17](docs/17-firmware-internals.md)) |
| 06 | [Bluetooth OTA protocol](docs/06-bt-ota-protocol.md) | `55AA80..84` frames, 512-byte writes, per-ear sequence |
| 07 | [TONE / sound effects](docs/07-tone-sfx.md) | Voice-prompt archive; proven replace + repack |
| 08 | [EQ2P & SENC tables](docs/08-eq2p-senc.md) | Float parameter tables, factory H2S Turbo EQ decoded |
| 09 | [PSMP / NV store](docs/09-psmp-nvds.md) | Persistent settings partition, keys, vendor editor |
| 10 | [AirPods (AAP) emulation](docs/10-aap-airpods.md) | SDP records, HID descriptors, BLE pop-up bytes, XAPL |
| 11 | [ANC & transparency](docs/11-anc-transparency.md) | Live gain commands, why filters are code not data |
| 12 | [Shenju factory flasher](docs/12-shenju-flasher.md) | Vendor tool decompiled: USB & UART boot-ROM paths, PSM editor |
| 13 | [Open-source tooling](docs/13-open-source-tooling.md) | `smartlink_flash`, `sl6806`, OpenPod CFW |
| 14 | [52bluetooth forum sweep](docs/14-52bluetooth.md) | What the Chinese forum has (and doesn't) on Huilian |
| 15 | [CFW roadmap & open questions](docs/15-cfw-roadmap.md) | What is data-only vs code, what's gated, next steps |
| 16 | [Live flash dump](docs/16-live-flash-dump.md) | **The real H3Pro Max3 firmware, read off the buds** via StarFun's own `C0 83` flash-read; first look inside |
| 17 | [Firmware internals](docs/17-firmware-internals.md) | Disassembly of the real image: memory map, boot flow, and exactly what the OTA updater checks (just a CRC) |

## Repo layout

```
docs/                         the wiki (start at 00-start-here.md)
docs/images/                  StarFun screenshots captured from the test device
tools/                        scripts written during the research (see tools/README.md)
data/catalog/                 OTA catalog dumps, Shenju Swagger spec, image index
data/analysis/                format notes, FIRM string dumps (old vs new h2sturbo)
data/tones-h2sturbo/          all 17 voice prompts extracted bit-exact from h2sturbo
data/partitions-h2sturbo/     raw EQ2P and SENC partitions
data/reports/                 HTML write-ups (AAP + ANC/transparency deep dive)
data/52bluetooth/             forum search results and thread dumps
firmware/h3promax3/           the genuine H3Pro Max3 2607061716 image, read from the buds (see docs/16)
data/partitions-h3promax3/    its TONE / EQ2P / SENC partitions, live index, FIRM strings, decoded EQ profiles
firmware/starfun-catalog/     the 24 public .up images (all SL6801-class)
firmware/openpod-sl6801/      OpenPod .up + a full 2 MB raw SL6801 flash dump
vendor/shenju-flashloader/    decompiled Shenju "Flashloader SL-DEV 6.9.5" + RAM loaders + DLLs
reference/starfun-app/        the decompiled StarFun Java that matters (OTA SDK, command config)
```

## Where things stand

Container format, CRCs, the Bluetooth OTA wire protocol, the voice-prompt archive, the EQ tables
and the AirPods emulation layer are all decoded from real images, and a TONE/EQ edit → CRC fix →
re-validate round-trip works offline. The public StarFun catalog only hosts SL6801-generation
firmware (newest June 2025) and the H3Pro Max3 query returns `204 No Content` — so the **genuine
377H3 base image was read directly off the buds** over Bluetooth, using the app's own authenticated
connection and its flash-read command ([docs/16](docs/16-live-flash-dump.md)). It is CRC-valid, uses
the exact same container conventions, and every tool here works on it. Nothing has been or will be
flashed without an explicit go.
