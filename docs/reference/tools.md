# Tools

Everything is Python 3 with the standard library unless noted. Run them from the repo root. The
full table with every option is in [`tools/README.md`](../../tools/README.md).

| Tool | Talks to buds | What it does | Guide |
|---|---|---|---|
| `hl` (`tools/huilian/`) | yes | info, settings, flash read, OTA, updater recovery, live ANC gain dashboard (`dash`), raw commands | [change settings](../how-to/change-settings.md), [flash](../how-to/flash-an-image.md) |
| `webui/` | yes | `hl` in Chrome or Edge over Web Serial. Not run against buds yet | [change settings](../how-to/change-settings.md#in-a-browser-or-a-desktop-panel) |
| `panel/` | yes | desktop control panel on top of `huilian` | [change settings](../how-to/change-settings.md#in-a-browser-or-a-desktop-panel) |
| `flashdump.py` + `.js` | yes, read only | flash read through the StarFun app with Frida | [dump firmware](../how-to/dump-firmware.md) |
| `flashota.py` + `.js` | yes | one-bud OTA through the StarFun app with Frida. Not run against buds yet | [OTA protocol](ota-protocol.md) |
| `build_up.py` | no | wrap a raw flash dump into a `.up`, checking every CRC | [dump firmware](../how-to/dump-firmware.md) |
| `tone_tool.py` | no | list, extract, replace and verify voice prompts | [replace prompts](../how-to/replace-prompts.md) |
| `cfw.py` | no | apply patch files to a `.up` | [apply a patch](../how-to/apply-a-patch.md) |
| `psmp_tool.py` | no | dump, verify and edit a PSMP settings log offline | [PSMP](psmp.md) |
| `pull_ota.py` | server | StarFun catalog login, list and download | [get stock firmware](../how-to/get-stock-firmware.md) |
| `upparts.py` | no | list and extract partitions of any `.up` | [`.up` format](up-format.md) |
| `sdp_hid.py` | no | decode the SDP records and Apple HID descriptors in FIRM | [AirPods emulation](../explanation/airpods-emulation.md) |
| `h3pro_elf.py` | no | wrap FIRM, OTAP and the bootloader as ELFs for Ghidra | [research](../research/README.md) |
| `emu/h3emu.py` | no | Unicorn rehost of FIRM with stubbed mask ROM: boot to the scheduler, or `--call` one function (needs `unicorn`, `capstone`) | [ROM read](../research/rom-read.md), [research](../research/README.md) |
| `repartition.py` | no | move SENC, TONE and EQ2P, grow TONE or FIRM, rewrite the index and CRCs | [memory map](../research/memory-map-and-boot.md#flash-layout) |
| `emu/repart_check.py` | no | check in Unicorn that FIRM follows a moved layout | [memory map](../research/memory-map-and-boot.md#flash-layout) |
| `emu/otap_check.py` | no | run the OTAP updater in Unicorn and flash an image into an emulated bud with `hl ota`'s own code (update, rollback, CRC failure, interrupted transfer) | [updater](../research/updater-otap.md#emulated-end-to-end-update) |
| `cave/build.py` | no | build the debug monitor into its patch file (needs `ziglang`, `pyelftools`) | [debug monitor](../research/debug-monitor.md) |
| `emu/monitor_check.py` | no | run the debug monitor through the real C0 handler in Unicorn | [debug monitor](../research/debug-monitor.md) |
| `flashmap.py` | no | draw `docs/flash-map.png` from a `.up` (needs PIL) | |
| `upfmt.py` | no | shared CRC16 and index helpers, not a CLI | |
