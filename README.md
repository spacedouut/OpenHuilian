# OpenHuilian: firmware notes for H3Pro Max3 (Huilian 377H3) earbuds

Docs and tools for the firmware on **H3Pro Max3** earbuds. They use a Huilian **377H3** chip, are sold as an
AirPods-Pro-style replica, and are controlled by the **StarFun** app. The older SL6801 images in the
public catalog use the same container, so they're covered too.

Nothing here has been flashed to a bud yet. Read [Safety](docs/00-start-here.md#safety) first.

## Wiki index

Start at **[docs/00-start-here.md](docs/00-start-here.md)**. Each page stands on its own.

| # | Page | One-liner |
|---|---|---|
| 00 | [Start here](docs/00-start-here.md) | Overview, glossary, safety, status board |
| 01 | [The device: H3Pro Max3](docs/01-device.md) | Identity, the OTA check, where firmware can come from |
| 02 | [StarFun app](docs/02-starfun-app.md) | Versions, servers, auth, hidden local-file OTA path |
| 03 | [OTA catalog](docs/03-ota-catalog.md) | The 24 public firmware images |
| 04 | [`.up` container format](docs/04-up-format.md) | Header, HLKJ body, partition index, flash map |
| 05 | [CRCs & integrity model](docs/05-crc-and-integrity.md) | CRC16/CCITT-FALSE, no signing |
| 06 | [Bluetooth OTA protocol](docs/06-bt-ota-protocol.md) | `55AA80..84` frames, 512-byte writes, per-ear sequence |
| 07 | [TONE / sound effects](docs/07-tone-sfx.md) | Voice-prompt archive, replace + repack |
| 08 | [EQ2P & SENC tables](docs/08-eq2p-senc.md) | Float parameter tables, decoded factory EQ |
| 09 | [PSMP / NV store](docs/09-psmp-nvds.md) | Persistent settings partition, record format, keys |
| 10 | [AirPods (AAP) emulation](docs/10-aap-airpods.md) | SDP records, HID descriptors, BLE pop-up bytes, XAPL |
| 11 | [ANC & transparency](docs/11-anc-transparency.md) | Live gain commands, why filters are code not data |
| 12 | [Shenju factory flasher](docs/12-shenju-flasher.md) | Vendor tool: USB & UART boot-ROM paths, PSM editor |
| 13 | [Open-source tooling](docs/13-open-source-tooling.md) | `smartlink_flash`, `sl6806`, OpenPod CFW |
| 15 | [CFW roadmap & open questions](docs/15-cfw-roadmap.md) | What's data-only vs code, what's open |
| 16 | [Live flash dump](docs/16-live-flash-dump.md) | Reading flash over Bluetooth with `C0 83`, and what's in the 2607061716 image |
| 17 | [Firmware internals](docs/17-firmware-internals.md) | Memory map, boot flow, what the OTA updater checks (just a CRC) |
| 18 | [FIRM walkthrough](docs/18-firm-walkthrough.md) | Event dispatcher, full `C0` command table, app auth handshake, NV keys, tasks, AirPods identity table |
||||||| 449b79a
| 18 | [FIRM walkthrough](docs/18-firm-walkthrough.md) | Event dispatcher, full `C0` command table, app auth handshake, NV keys, tasks, AirPods identity table |
| 19 | [Patching your own firmware](docs/19-cfw-patching.md) | `cfw.py`, version-pinned patch files with knobs, first patch: faster head tracking |

## Repo layout

```
docs/                         the wiki
tools/                        scripts (see tools/README.md)
data/catalog/                 OTA catalog dumps, Shenju Swagger spec, image index
data/analysis/                format notes, FIRM string dumps (old vs new h2sturbo)
data/tones-h2sturbo/          the 17 voice prompts extracted from h2sturbo
data/partitions-h2sturbo/     raw EQ2P and SENC partitions
data/reports/                 HTML write-ups (AAP + ANC/transparency)
firmware/h3promax3/           H3Pro Max3 2607061716 image, read off the buds (docs/16)
data/partitions-h3promax3/    its TONE / EQ2P / SENC partitions, index, FIRM strings, decoded EQ profiles
firmware/starfun-catalog/     the 24 public .up images (all SL6801-class)
firmware/openpod-sl6801/      OpenPod .up + a full 2 MB raw SL6801 flash dump
vendor/shenju-flashloader/    decompiled Shenju "Flashloader SL-DEV 6.9.5" + RAM loaders + DLLs
reference/starfun-app/        the decompiled StarFun Java that matters (OTA SDK, command config)
```

## Where things stand

The container format, CRCs, Bluetooth OTA protocol, voice prompts, EQ tables and the AirPods layer
are decoded, and TONE/EQ edits round-trip offline. StarFun's server has no H3Pro Max3 firmware, so
the 2607061716 image in `firmware/h3promax3/` was read off the buds with the app's own flash-read
command ([16](docs/16-live-flash-dump.md)). It's CRC-valid and every tool here works on it. The bud's
updater accepts any image whose CRC matches ([17](docs/17-firmware-internals.md)). No modified image
has been tried on hardware.
