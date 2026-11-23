# Tools

Python commands run from the repo root as `python3 -m openhuilian.<package>.<module>`.
Use `./hl` for the device CLI; no stock images or ROMs are bundled. The
package layout and examples are in [`openhuilian/README.md`](../../openhuilian/README.md).

| Tool | Talks to buds | What it does | Guide |
|---|---|---|---|
| `hl` (`openhuilian/device/`) | yes | info, settings, flash read, OTA, updater recovery, live ANC gain dashboard (`dash`), raw commands | [change settings](../how-to/change-settings.md), [flash](../how-to/flash-an-image.md) |
| `ui.webui` | yes | `hl` in Chrome or Edge over Web Serial. Not run against buds yet | [change settings](../how-to/change-settings.md#in-a-browser-or-a-desktop-panel) |
| `ui.panel` | yes | desktop control panel on top of `openhuilian.device` | [change settings](../how-to/change-settings.md#in-a-browser-or-a-desktop-panel) |
| `format.build_up` | no | wrap a raw flash dump into a `.up`, checking every CRC | [dump firmware](../how-to/dump-firmware.md) |
| `format.tone_tool` | no | list, extract, replace and verify voice prompts | [replace prompts](../how-to/replace-prompts.md) |
| `patch.cfw` | no | apply patch files to a `.up` | [apply a patch](../how-to/apply-a-patch.md) |
| `format.psmp_tool` | no | dump, verify and edit a PSMP settings log offline | [PSMP](psmp.md) |
| `device.pull_ota` | server | StarFun catalog login, list and download | [get stock firmware](../how-to/get-stock-firmware.md) |
| `format.upparts` | no | list and extract partitions of any `.up` | [`.up` format](up-format.md) |
| `format.sdp_hid` | no | decode the SDP records and Apple HID descriptors in FIRM | [AirPods emulation](../explanation/airpods-emulation.md) |
| `format.h3pro_elf` | no | wrap FIRM, OTAP and the bootloader as ELFs for Ghidra | [research](../research/README.md) |
| `emu.h3emu` | no | Unicorn rehost of FIRM with stubbed mask ROM: boot to the scheduler, or `--call` one function (needs `unicorn`, `capstone`) | [ROM read](../research/rom-read.md), [research](../research/README.md) |
| `patch.repartition` | no | move SENC, TONE and EQ2P, grow TONE or FIRM, rewrite the index and CRCs | [memory map](../research/memory-map-and-boot.md#flash-layout) |
| `emu.repart_check` | no | check in Unicorn that FIRM follows a moved layout | [memory map](../research/memory-map-and-boot.md#flash-layout) |
| `emu.otap_check` | no | run the OTAP updater in Unicorn and flash an image into an emulated bud with `hl ota`'s own code (update, rollback, CRC failure, interrupted transfer) | [updater](../research/updater-otap.md#emulated-end-to-end-update) |
| `patch.cave.build` | no | build the debug monitor into its patch file (needs `ziglang`, `pyelftools`) | [debug monitor](../research/debug-monitor.md) |
| `emu.monitor_check` | no | run the debug monitor through the real C0 handler in Unicorn | [debug monitor](../research/debug-monitor.md) |
| `patch.cave.build_bootlog` | no | build the boot milestone log into its patch file (needs `ziglang`, `pyelftools`) | [boot log](../research/boot-log.md) |
| `emu.bootlog_check` | no | boot the image with the boot log patch on the hardware model and read the log back (needs `unicorn`, `OPENHUILIAN_MASK_ROM`) | [boot log](../research/boot-log.md) |
| `format.flashmap` | no | draw `docs/flash-map.png` from a `.up` (needs PIL) | |
| `format.upfmt` | no | shared CRC16 and index helpers, not a CLI | |
