# Firmware research reference

This section describes what the H3Pro Max3 `2607061716` firmware does and where its code and data live. It is a subsystem reference for agents and RE contributors, based mainly on static analysis with hardware observations called out where they matter.

![Flash and address-space map](../flash-map.png)

## Index

| Page | Contents |
|---|---|
| [Memory map and boot](memory-map-and-boot.md) | CPU, address spaces, flash layout, partition headers, boot selection and flash classes |
| [OTAP updater](updater-otap.md) | Update acceptance, CRC ranges, index handling, failure behavior and the OTAP command surface |
| [FIRM runtime](firm-runtime.md) | Tasks, timers, event IDs, modules, partition access, peer messages and hardware |
| [Command channel](command-channel.md) | Receive demux, text console, both FIRM `C0` handlers, app auth and OTA entry |
| [Settings store](settings-store.md) | NV API, key lengths, defaults and setting semantics |
| [AirPods layer](airpods-layer.md) | AAP opcodes, identity data, SDP/HID, adverts, AES, heart rate and head tracking |
| [Audio and DSP](audio-and-dsp.md) | EQ2P and SENC readers, ANC controls, DSP tables and verified patch offsets |
| [Mask ROM](mask-rom.md) | The 467-target call surface and named ROM services |
| [ROM read patch](rom-read.md) | `rom-read` patch: C0 `0x83` with address bit 31 set copies raw memory, the mask-ROM dump path, its Unicorn selftest |
| [UART boot ROM](uart-boot-rom.md) | Vendor loader sequence, `42 52` frames, USB entry and unresolved hardware details |
| [Images and variants](images-and-variants.md) | Catalog differences, H3Pro image contents, `zero_ota.bin` and OpenPod |
| [Addresses](addresses.md) | One table of named functions, data locations and related address ranges |

For formats and operating instructions, use the [device reference](../reference/device.md), [tools reference](../reference/tools.md), [update format](../reference/up-format.md), [OTA protocol](../reference/ota-protocol.md), [flashing guide](../how-to/flash-an-image.md) and [recovery guide](../how-to/unstick-buds.md).

## Scope and confidence

Addresses refer to H3Pro Max3 `2607061716` unless a row names another image. FIRM is about 680 KiB. Symbols do not survive, so names such as `FUN_0080e770` are address-based decompiler names. Address case does not change the location.

The analysis uses ARM ELFs, Capstone Thumb-2 disassembly, Ghidra decompilation, strings, literal pools and cross references. The original whole-program FIRM decompile contains 4,512 functions. Ghidra 12.2 auto-analysis finds 3,864. A pass over branch targets and Thumb pointer references adds 44 FIRM functions, 20 OTAP functions and one BOOT function. Indirectly reached functions such as `FUN_00c4f0cc` and `FUN_00c52e4c` need that recovery.

CRC-only update acceptance works on hardware with stock and patched images through `tools/hl ota`. Hardware also confirms that omitting `04` after `84` leaves the buds in OTAP across power cycles. A retry after a real CRC failure remains unverified.

## Reproduce it

Run from the repository root. The output directory must exist before calling [h3pro_elf.py](../../tools/h3pro_elf.py).

```bash
mkdir -p out
python3 tools/h3pro_elf.py firmware/h3promax3/h3promax3_2607061716_live.up out/
```

Load `out/firm.elf`, `out/otap.elf` and `out/boot.elf` in Ghidra as ARM Cortex, little endian, Thumb-2. The Ghidra language is `ARM:LE:32:Cortex`. Use the ELF memory mappings rather than assigning one raw-image base. [Memory map and boot](memory-map-and-boot.md) describes the RAM and XIP segments.

The documented headless workflow uses Ghidra 12.2 with PyGhidra. Its scripts are under `~/tmp/oh-scripts/`, and raw outputs are under `~/tmp/oh-dump/` on the analysis machine.

| Script | Work |
|---|---|
| `oh_dump_lib.py` | Full decompile, strings, cross references, call graph and ROM surface |
| `oh_fixfuncs.py` | Recover functions from branch targets and Thumb pointers |
| `oh_mkfunc.py` | Create and decompile a function at an explicit address |
| `romscan.py` | Capstone direct-BL sweep |
| `catalog_sweep.py` | Per-image reports and string comparisons |

The sources do not document a `DumpAll` invocation. The named PyGhidra scripts describe the available headless workflow. ReVa-assisted analysis supplies the 4,512-function baseline, while the script-based workflow supplies the Ghidra 12.2 results.

[upparts.py](../../tools/upparts.py) lists and extracts partitions and dumps strings. [sdp_hid.py](../../tools/sdp_hid.py) decodes SDP/HID data. [flashmap.py](../../tools/flashmap.py) generates the flash and address-space diagram from the image, including boot flow, the `.up` wrapper, acceptance rules and command channels. [cfw.py](../../tools/cfw.py) repairs partition CRCs when applying patches. [emu/h3emu.py](../../tools/emu/h3emu.py) rehosts FIRM in Unicorn with stubbed ROM: it boots to the scheduler, and `--call ADDR` runs a single function with `--reg`, `--poke` and `--peek`. See [apply a patch](../how-to/apply-a-patch.md) for the operating workflow.

## Open questions

- What does the bootloader download loop speak, and which H3Pro pads expose UART or the boot strap? H3Pro compatibility with the SL6801 ROM protocol and loader addresses is unverified.
- Can a larger OTA layout erase the flag page, and does retry work after a real CRC failure?
- Which OTAP role and channel states permit the gated `C0` handlers to reply beyond the observed read subset?
- What replaces or wraps `zero_ota.bin` to make a valid H3Pro update? Its partition target and recovery use are unverified.
- What are the remaining AAP opcode semantics and compatibility gaps? Opcode `0x4B` likely controls listen mode. The exact use of `air_adv_key` for post-pairing AES content still needs confirmation.
- Can the factory ANC commands be reached over SPP, and what argument ranges are valid? Which h2sturbo profile binds to transparency versus ANC-on, and what do the partly decoded SENC parameters mean?
- What are the precise roles of the likely compressor tables, EQ2P `0xFC` field and extra page-0 filter block?
- What chip-name string belongs in an official H3Pro `CONFIG` header? No official H3Pro `.up` supplies one.
- Does exposing the app's dormant local-file picker work on hardware? Its code path exists, but that route is unverified.

The [roadmap](../explanation/roadmap.md) covers possible work. [Update acceptance](../explanation/how-updates-are-accepted.md), [AirPods emulation](../explanation/airpods-emulation.md), [ANC and transparency](../explanation/anc-and-transparency.md) and [the app and servers](../explanation/the-app-and-servers.md) explain the behavior without the address-level detail.
