# UART boot ROM

The vendor's COM.dll speaks `42 52` frames to a boot ROM and then to a RAM loader. The PC-side frame formats and SL6801/SL6806 loader sequence are documented, while H3Pro pin assignments and loader compatibility remain unverified.

## Vendor implementation

Shenju, 珠海绅聚 or Smartlink, supplies the SL68xx production tool and the `ota.shenjugroup.com` service. Flashloader SL-DEV 6.9.5 is a Windows PyInstaller bundle with Python 3.10 code and a PyQt6 UI.

The archive is [vendor/shenju-flashloader](../../vendor/shenju-flashloader/). Its [README](../../vendor/shenju-flashloader/README.md) records provenance and third-party licensing.

| Archive path | Contents |
|---|---|
| `decompiled-src/burn_service/flash_loader/` | `up_parser.py`, `flash_usb_6801.py`, `flash_uart_6801.py`, `com_dll.py` |
| `decompiled-src/ui_develop/` | UI and PSM editor `window_param.py` |
| `decompiled-src/verno.py` | Chinese changelog covering 6.7.1 through 6.9.5 |
| `doc/readme*.txt` | Vendor usage notes |
| `ram_run_bin/` | RAM loaders and helper programs |
| `COM.dll` | UART implementation, x86, 914 decompiled functions |
| `MASSSTORAGE.dll` | USB mass-storage implementation |
| `c_crc.dll` | CRC16 |
| `psm-nvds.dll` | PSMP handling |

Some Python functions are marked `Decompyle incomplete`. The source lists boards `P262`, `247`, `TWS206`, `TWS208` and `MP3_01`. `247` is the 247Youth line, related to 377Youth, so the tool includes TWS production support.

## 42 52 frames

`42 52` is ASCII `BR`. Multibyte addresses in the documented write frames are little-endian 24-bit fields.

| Operation | Frame layout | Notes |
|---|---|---|
| Sync/hello | `42 52 00 02 <crc16 LE>` | Up to 150 retries, 20 ms timeout |
| Write RAM | `42 52 02 87 <addr LE24> 80 00 <128 B data> <crc16 LE>` | CRC over the `0x87` bytes after `BR` |
| Run RAM | Same frame family, address is the entry | Exact complete frame is not supplied |
| Write flash | `42 52 05 00 <addr LE24> 00 04 <1024 B data> <crc16 LE>` | 1 KiB chunks |
| Chip erase | `42 52 08 06 00 00 00 00 <sum16 LE>` | Plain byte sum |

RAM transfers use 128-byte chunks. Flash transfers on this wire path use 1 KiB chunks. The Python layer drives them through COM.dll.

## Loader sequence

The documented `flash_uart_6801.py` and `com_dll.py` flow is as follows.

```text
com_device_open(port, idx, baud)
com_device_connect_boot_rom(idx)
com_device_update_boot_ram(idx, loader, len, addr)
com_device_run_boot_ram(idx, addr)
com_device_connect_startup(idx)
com_device_reset_baudrate(idx, baud)
com_device_chip_erase_flash(idx)
com_device_write_flash(idx, data, 4096, addr)
com_device_get_check_sum(idx, addr, len, &out)
```

`connect_startup` resynchronizes with the RAM loader. The baud-rate setting is named `bron_uart_bitrate`. The last call obtains a device-side checksum for comparison. The 4,096-byte write call repeats across the image and is broken into smaller wire chunks.

| Target | Loader bytes | RAM destination |
|---|---|---|
| SL6801 | `cal_frequent_drift_gyro_ur.bin[1088:]` | `0x850000` |
| SL6806, first stage | `mp_uart_6806.bin[0:1024]` | `0x874000` |
| SL6806, second stage | `mp_uart_6806.bin[1088:]` | `0x810040` |

The SL6801 loader is a 197-function program. It has `CPU0_ADDR` and `PC 0x...` fault-dump strings and its own command dispatch. Its internals are only partly mapped.

| Helper | Purpose |
|---|---|
| `reset_6801.bin` | Reboot |
| `cal_frequent_drift*.bin` | Crystal calibration, writes `freq_drift` |
| `base_board.bin` | RF-check helper |
| `6801_intel_flash*.bin` | Flash helpers |

The production tool writes 4 KiB blocks with 64 KiB erase granularity. Its 6.7.5 fix concerns erases touching PSM at the end of flash. Its 6.7.7 fix concerns zero-padding of a final unaligned block.

## USB entry

Holding PB9 low during power-on makes the documented mask ROM enumerate as a USB disk. `flash_usb_6801.py` uses MASSSTORAGE.dll and supports up to eight devices concurrently. OpenPod uses this path for its MP3 player.

Earbuds have no USB connector, so applying this route to them would require accessible test pads. UART is a likely factory route because TWS charging-case contacts can double as UART or boot pins, but that is not a verified H3Pro pin mapping.

## Container and settings behavior

The vendor parser describes a `.up` as a 256-byte `CONFIG` header followed by the flash image. `make_up_header` computes body CRC16 with polynomial `0x1021` and init `0xFFFF`.

The flasher selects the chip solely from the ASCII header name at `+0x16`, `sl6801` or `sl6806`. `.upex` files are tar-based SL6806 multi-image packages.

The tool merges device PSM with PSM from the image, can set `restore_factory` and edits NV keys such as `bt_name`, `bt_addr`, `ear_type`, `paired_flag`, `sn_info`, `freq_drift` and `rfparam`. See [settings store](settings-store.md).

## H3Pro compatibility and unknowns

The tool recognizes SL6801 and SL6806. H3Pro/377H3 is a different Huilian generation whose HLKJ, index, CRC and PSMP conventions match these images. Its bootloader code is byte-identical across the catalog, but that does not establish an identical mask ROM or valid loader addresses.

The H3Pro bootloader's strap check at `FUN_008605f2` enters a download/wait loop after reading two status registers. Its connection to the documented UART or USB protocol is likely and remains unverified.

The H3Pro UART pins, physical strap, ROM response and suitability of the vendor loader binaries are unknown. None of this loader path is verified on H3Pro buds. The PC-side frames provide enough detail to attempt an open implementation, once hardware access and compatibility are established.

See [vendor tools and prior art](../explanation/vendor-tools-and-prior-art.md) for broader context.
