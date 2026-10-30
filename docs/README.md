# OpenHuilian docs

Docs for reading, changing and flashing the firmware on H3Pro Max3 earbuds (Huilian 377H3 chip,
sold as an AirPods Pro replica, controlled by the StarFun app).

**Safety first.** Flashing works, and it can also leave you with buds that don't boot. Only flash
images built for the H3Pro, always let a flash finish, and read
[flash an image](how-to/flash-an-image.md) before your first one. There's no tested wired
recovery.

## New here

1. [Talk to your buds and back up their firmware](tutorials/first-connection.md). Read only, safe.
2. [Flash your first custom image](tutorials/first-custom-image.md). Swap a voice prompt and flash it.

## How-to guides

* [Dump your buds' firmware](how-to/dump-firmware.md)
* [Change settings](how-to/change-settings.md)
* [Replace voice prompts](how-to/replace-prompts.md)
* [Edit the EQ](how-to/edit-eq.md)
* [Apply a firmware patch](how-to/apply-a-patch.md)
* [Flash an image](how-to/flash-an-image.md)
* [Get buds out of the updater](how-to/unstick-buds.md)
* [Get stock firmware](how-to/get-stock-firmware.md)

## Reference

* [Device](reference/device.md): identity, flash layout, what's in the stock image
* [`.up` container](reference/up-format.md): header, partition index, CRCs
* [Bluetooth OTA protocol](reference/ota-protocol.md): the `55 AA` frames
* [Command channel](reference/command-channel.md): every `C0` command, the auth handshake
* [TONE](reference/tone.md), [EQ2P and SENC](reference/eq2p-senc.md), [PSMP](reference/psmp.md): the data partitions
* [Patch files](reference/patch-files.md): the `cfw.py` format
* [Tools](reference/tools.md): every script in `tools/`

## Explanation

* [How updates get accepted](explanation/how-updates-are-accepted.md): why a CRC is the only check
* [AirPods emulation](explanation/airpods-emulation.md)
* [ANC and transparency](explanation/anc-and-transparency.md)
* [The StarFun app and its servers](explanation/the-app-and-servers.md), including the public catalog
* [Vendor tools and prior art](explanation/vendor-tools-and-prior-art.md)
* [Roadmap and open questions](explanation/roadmap.md)

## Research

[Firmware internals by subsystem](research/README.md): memory map and boot, the updater, the FIRM
runtime, the command channel, the settings store, the AirPods layer, audio and DSP, the mask ROM,
the UART boot ROM, and an address index. Written for people and agents working on the firmware
itself.

## Glossary

| Term | Meaning |
|---|---|
| Huilian / 慧联 / HLKJ | The chip and firmware vendor. `HLKJ` is the magic at the start of every image. |
| Smartlink / SL6801 / SL6806 | Older chip family names. Every image in the public catalog says `SL6801`. |
| 377 / 377H3 / H3Pro | The newer chip generation in these buds. The buds report chip `H3Pro`. |
| Shenju / 绅聚 | Company behind the factory flasher and a second OTA server. |
| StarFun | The phone app (`com.fun.app`). Use version 2.0.7.016, 2.0.7.017 rejects these buds. |
| `.up` | A firmware image file. A full image, not a patch. |
| FIRM, TONE, EQ2P, SENC, OTAP, PSMP | The partitions: firmware, voice prompts, EQ, sensor and mic tuning, updater, settings. |
| OTAP / the updater | The small program that writes new firmware. Buds in it show up as a generic Bluetooth device. |

## Old page numbers

| Old | Now |
|---|---|
| 00 Start here | this page |
| 01 Device | [reference/device.md](reference/device.md) |
| 02 StarFun app, 03 OTA catalog | [explanation/the-app-and-servers.md](explanation/the-app-and-servers.md) |
| 04 `.up` format | [reference/up-format.md](reference/up-format.md) |
| 05 CRCs and integrity | [reference/up-format.md#crcs](reference/up-format.md#crcs), [explanation/how-updates-are-accepted.md](explanation/how-updates-are-accepted.md) |
| 06 Bluetooth OTA | [reference/ota-protocol.md](reference/ota-protocol.md) |
| 07 TONE, 08 EQ2P/SENC, 09 PSMP | [reference/tone.md](reference/tone.md), [reference/eq2p-senc.md](reference/eq2p-senc.md), [reference/psmp.md](reference/psmp.md) |
| 10 AAP, 11 ANC | [explanation/airpods-emulation.md](explanation/airpods-emulation.md), [explanation/anc-and-transparency.md](explanation/anc-and-transparency.md) |
| 12 Shenju flasher, 13 open-source tooling | [explanation/vendor-tools-and-prior-art.md](explanation/vendor-tools-and-prior-art.md) |
| 15 Roadmap | [explanation/roadmap.md](explanation/roadmap.md) |
| 16 Live flash dump | [how-to/dump-firmware.md](how-to/dump-firmware.md), [reference/device.md](reference/device.md) |
| 17, 18, 21 Firmware internals | [research/](research/README.md) |
| 19 CFW patching | [how-to/apply-a-patch.md](how-to/apply-a-patch.md), [reference/patch-files.md](reference/patch-files.md) |
| 20 hl CLI | [how-to/change-settings.md](how-to/change-settings.md), [how-to/flash-an-image.md](how-to/flash-an-image.md), [reference/command-channel.md](reference/command-channel.md) |
