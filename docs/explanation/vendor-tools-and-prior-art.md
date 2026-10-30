# Vendor tools and prior art

## The Shenju factory flasher

Shenju (珠海绅聚 / Smartlink, `shenjugroup.com`) is the chip vendor behind the SL68xx parts and the
`ota.shenjugroup.com` host in StarFun. Their Windows production/flashing tool is a PyInstaller bundle that decompiles to readable Python.
It's archived under
[`vendor/shenju-flashloader/`](../../vendor/shenju-flashloader/), see its [README](../../vendor/shenju-flashloader/README.md) for provenance and rights (third-party, **not** AGPL):

```
decompiled-src/     Python 3.10 source (some functions marked "Decompyle incomplete")
  burn_service/flash_loader/   up_parser.py, flash_usb_6801.py, flash_uart_6801.py, com_dll.py …
  ui_develop/                  PyQt6 UI incl. the PSM parameter editor (window_param.py)
  verno.py                     full Chinese changelog 6.7.1 → 6.9.5
doc/readme*.txt      official usage notes
ram_run_bin/         RAM-loader / helper binaries the tool pushes to the chip
*.dll                COM.dll (UART), MASSSTORAGE.dll (USB), c_crc.dll (CRC16), psm-nvds.dll (PSMP)
```

### What it confirms

* `.up` = 256-byte `CONFIG` header + verbatim flash image; header CRC16 poly `0x1021` init
  `0xFFFF` over the body (`make_up_header`), same as [.up format](../reference/up-format.md) and [integrity](how-updates-are-accepted.md).
* Chip is selected **only** from the ASCII name at header offset 0x16 (`sl6801` / `sl6806`);
  `.upex` (tar) files are SL6806 multi-image packs.
* PSMP is an NV key/value store; the tool merges device PSM with PSM in the `.up` on burn, can
  set `restore_factory`, and edits `bt_name`, `bt_addr`, `ear_type`, `paired_flag`, `sn_info`,
  `freq_drift`, `rfparam`… ([PSMP](../reference/psmp.md)).
* Board series list `P262 / 247 / TWS206 / TWS208 / MP3_01` → it is the **TWS earbud production
  tool**, not just an MP3-player tool. `247` = 247Youth, same vendor line as 377Youth.
* Writes flash in **4 KiB blocks** with a 64 KiB erase granularity; changelog 6.7.5 fixed "erase
  touching PSM at the end of flash", 6.7.7 fixed zero-padding of the last non-aligned block.

### Two physical paths into the chip

### USB mass-storage boot ROM
Hold **PB9 low while powering on** → the mask-ROM enumerates as a USB disk; the tool writes via
`MASSSTORAGE.dll` (`flash_usb_6801.py`). Up to 8 devices concurrently. This is how OpenPod flashes
its MP3 player. Earbuds have no USB connector, so for TWS this would need test pads.

### UART boot ROM (`flash_uart_6801.py`, `com_dll.py`)
```
com_device_open(port, idx, baud)
com_device_connect_boot_rom(idx)                     # sync with mask ROM
com_device_update_boot_ram(idx, loader, len, addr)   # push RAM loader
      SL6801: cal_frequent_drift_gyro_ur.bin[1088:]  → 0x850000
      SL6806: mp_uart_6806.bin[0:1024] → 0x874000, then [1088:] → 0x810040
com_device_run_boot_ram(idx, addr)
com_device_connect_startup(idx)                      # re-sync with the loader
com_device_reset_baudrate(idx, baud)                 # user-selected 'bron_uart_bitrate'
com_device_chip_erase_flash(idx)
com_device_write_flash(idx, data, 4096, addr)  × N
com_device_get_check_sum(idx, addr, len, &out)       # device-side CRC compare
```
Extra loaders: `reset_6801.bin` (reboot), `cal_frequent_drift*.bin` (crystal calibration; writes
the `freq_drift` NV key), `base_board.bin` / `6801_intel_flash*.bin` (RF check / flash helpers).

UART is the realistic factory path for earbuds (charging-case contacts routinely double as
UART/boot pins on TWS designs). The PC side of the byte-level protocol (`42 52` frames in
`COM.dll`) is decoded in [research](../research/README.md). The loader binaries are only partly mapped, and
none of it has been tried on H3Pro buds. Which pins carry UART is still unknown.

### Relevance to H3Pro

* This tool knows SL6801 and SL6806 only. "377H3"/"H3Pro" is a newer Huilian generation. It
  keeps the `HLKJ` layout, and its bootloader code is byte-identical to every catalog image's
  ([research](../research/README.md)). Whether it shares the boot ROM and loader addresses is unknown.
* The `.up` container, CRC and PSMP conventions are vendor-wide and very likely carried forward.
* **Do not** point this tool (or any SL6801 loader binary) at an H3Pro device.

## Public SL68xx projects

Three public GitHub projects target the same Shenju/SmartLink silicon family as the StarFun
catalog images. None of them touch earbuds or 377H3, but together they independently confirm the
container format, the CRC, and, most importantly, that the bootloader does not check a
signature.

### `ilyakurdyukov/smartlink_flash`, USB boot-ROM dumper/writer (C, Linux/MSYS2)

<https://github.com/ilyakurdyukov/smartlink_flash>

* Talks to the mask-ROM USB mass-storage mode (`301a:2800`, inquiry `SMTLINK DEVICE 2.00`) via
  SCSI vendor commands; supports SL6801 and SL6806; read/erase/write whole flash.
* Boot key varies per device; card-reader mode `301a:2801` `SMTLINK CARDREADER`.
* `fwhelper/main.c` parses `CONFIG` + `HLKJ` containers and converts a raw dump to `.up`,
  **independent confirmation of [.up format](../reference/up-format.md)** (`file_offset = flash_addr + 0x100`,
  index at body `0x20` → `0x3000`).
* SL6806 is the MP3-player chip (YP3 / "云P3", Jointbees); SL6801 is what all 24 StarFun images
  and OpenPod's player use.

### `take-cheeze/sl6806`, Arduino-style framework + bootloader RE (docs/)

<https://github.com/take-cheeze/sl6806>

Its `docs/BOOTLOADER.md`, `FLASHING.md`, `DUMPING.md` read the 61 KB `HLKJ` bootloader end to end.
Key facts:

* Boot flow: mask ROM → boot-mode pin check (~1 s) → load HLKJ to `0x0081FC00`, enter
  `0x00820000` → main chooses *update from PC* (USB), *forced restore* (`restore.up`),
  *sdupdate* (`update.up`), or *load FIRM*.
* `.up` acceptance by the bootloader = `memcmp("CONFIG")` → `header pass`; `memcmp(+0x16, "SL6806")`
  → `mark pass`; build-timestamp differs → `time is not same` → proceed. Then a CRC16
  **write-verify** (`crc cmp %x %x`) computed by the bootloader itself, both sides init `0xFFFF`.
* **"Nothing in the payload has to be signed or checksummed in advance."** The only unresolved
  check is a `loadCrc` log string for the FIRM header at boot, whose code was not located.
* USB download mode is in mask ROM → the chip is recoverable over USB regardless of flash contents.

Caveat: this is SL6806. The StarFun images are SL6801 (same vendor, same container; the mark
string there is `SL6801`). On the H3Pro the updater doesn't check a mark string at all ([updater](../research/updater-otap.md)).

### `zeroproj/OpenPod`, a shipped custom firmware on SL6801

<https://github.com/zeroproj/OpenPod> · <https://zeroproj.github.io/OpenPod/>

* Rewrites the UI of the Iigenai GN-438 MP3 player (yp3_2.0.43 base) as an iPod-nano clone.
  Distributed as `.up` binaries; RE notes and tools are **not public**.
* Proves the method on this silicon: dump → patch FIRM → fix CRCs → flash via the vendor tool (only checked on the GN-438).
* Two files from its git history are archived here:
  * Shenju's `SetupFlashloaderSL-DEV(6.9.5).exe` → [vendor tools](vendor-tools-and-prior-art.md)
  * `GN438_sl6801_fulldump.bin`, a raw 2 MiB SL6801 flash image with bootloader, partition table
    and a **live PSMP log** → [`firmware/openpod-sl6801/`](../../firmware/openpod-sl6801/), used by
    [PSMP](../reference/psmp.md) / `tools/psmp_tool.py`.

### What transfers to the H3Pro Max3, and what doesn't

| Transfers (same vendor conventions) | Does not (yet) |
|---|---|
| `.up` container, `HLKJ` table, CRC16, PSMP NV store | any base image (377H3 vs SL6801) |
| no signature (H3Pro is even looser: CRC only, no mark string, see [updater](../research/updater-otap.md)) | boot ROM addresses, loader binaries, USB IDs |
| Shenju flasher's `.up`/PSM logic | a physical write path, buds have no USB |
| BT OTA ([OTA protocol](../reference/ota-protocol.md)) as the intended field update route, now used on real H3Pro buds ([command channel](../reference/command-channel.md)) | |
