# 12 · Shenju "Flashloader SL-DEV 6.9.5" — the vendor's factory tool

Shenju (珠海绅聚 / Smartlink, `shenjugroup.com`) is the chip vendor behind the SL68xx parts and the
`ota.shenjugroup.com` host in StarFun. Their Windows production/flashing tool is a PyInstaller bundle that decompiles to readable Python.
It's archived under
[`vendor/shenju-flashloader/`](../vendor/shenju-flashloader/) — see its [README](../vendor/shenju-flashloader/README.md) for provenance and rights (third-party, **not** AGPL):

```
decompiled-src/     Python 3.10 source (some functions marked "Decompyle incomplete")
  burn_service/flash_loader/   up_parser.py, flash_usb_6801.py, flash_uart_6801.py, com_dll.py …
  ui_develop/                  PyQt6 UI incl. the PSM parameter editor (window_param.py)
  verno.py                     full Chinese changelog 6.7.1 → 6.9.5
doc/readme*.txt      official usage notes
ram_run_bin/         RAM-loader / helper binaries the tool pushes to the chip
*.dll                COM.dll (UART), MASSSTORAGE.dll (USB), c_crc.dll (CRC16), psm-nvds.dll (PSMP)
```

## What it confirms

* `.up` = 256-byte `CONFIG` header + verbatim flash image; header CRC16 poly `0x1021` init
  `0xFFFF` over the body (`make_up_header`) — same as [04](04-up-format.md) and [05](05-crc-and-integrity.md).
* Chip is selected **only** from the ASCII name at header offset 0x16 (`sl6801` / `sl6806`);
  `.upex` (tar) files are SL6806 multi-image packs.
* PSMP is an NV key/value store; the tool merges device PSM with PSM in the `.up` on burn, can
  set `restore_factory`, and edits `bt_name`, `bt_addr`, `ear_type`, `paired_flag`, `sn_info`,
  `freq_drift`, `rfparam`… ([09](09-psmp-nvds.md)).
* Board series list `P262 / 247 / TWS206 / TWS208 / MP3_01` → it is the **TWS earbud production
  tool**, not just an MP3-player tool. `247` = 247Youth, same vendor line as 377Youth.
* Writes flash in **4 KiB blocks** with a 64 KiB erase granularity; changelog 6.7.5 fixed "erase
  touching PSM at the end of flash", 6.7.7 fixed zero-padding of the last non-aligned block.

## Two physical paths into the chip

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
UART/boot pins on TWS designs). The byte-level serial protocol is inside `COM.dll`
and the loader binaries and has **not** been disassembled yet.

## Relevance to H3Pro

* This tool knows SL6801 and SL6806 only. "377H3"/"H3Pro" is a newer Huilian generation; whether
  it shares the boot ROM, loader addresses, or even the `HLKJ` layout is unknown.
* The `.up` container, CRC and PSMP conventions are vendor-wide and very likely carried forward.
* **Do not** point this tool (or any SL6801 loader binary) at an H3Pro device.
