# 09 · PSMP — the persistent settings store (NVDS)

`PSMP` is the 16 KB partition at the end of flash (`0x1FC000` on 2 MB parts, `0x0FC000` on 1 MB)
that holds device identity and user settings. OTA images **declare** it but never ship it, which is
how settings survive an update. It is only visible in a raw flash dump. We have two: `firmware/openpod-sl6801/GN438_sl6801_fulldump.bin`
(an SL6801 MP3 player, not earbuds) and the live H3Pro dump ([16](16-live-flash-dump.md)). The
H3Pro PSMP holds private device data (addresses, auth codes), so it isn't committed.

## What the vendor calls it

The flasher handles PSMP through `psm-nvds.dll` (`pc_psm_init` / `pc_psm_uninit`) — NVDS = the
"non-volatile data storage" naming used by the Bluetooth stack. The Python side only sees a
flattened list of `(name[256], u32 len, value)` (`up_parser.py: psm_dll.get_vars / set_vars`); the
DLL converts between that and the on-flash log. The tool merges PSM from the device with PSM in the
`.up` when burning (changelog 6.9.4) and can add a `restore_factory` variable that the firmware
consumes on next boot.

## On-flash record format

Decoded from the dump (`tools/psmp_tool.py`), 73 records parse back-to-back with zero slack, then
`FF` fill:

```
55 AA            marker
u8   flag        FF = live, FE = superseded (log-structured: new writes append, old record flagged)
u32  check       depends only on key+value (identical key/value → identical check); algorithm NOT
                 yet reproduced (not CRC32/BZIP2/MPEG/POSIX/FNV/djb2 over any field order)
u16  value_len
u16  key_id      small integer, assigned in first-write order (bt_addr=1, device_id=2, …)
u8   key_len
char key[key_len]     ASCII, not NUL-terminated
u8   value[value_len]
```

Live values in the OpenPod dump (`python3 tools/psmp_tool.py <dump>`):

| key | value | meaning |
|---|---|---|
| `bt_addr` | `57 33 00 C1 B2 C0` | BD_ADDR little-endian → `C0:B2:C1:00:33:57` |
| `device_id` | `CBKJ01MP3---MP3-------T90026----------C0B2C100335785…` | 64-char factory serial/SN string incl. the address |
| `freq_drift` | `59 00` | crystal frequency-offset calibration (flasher: `freq_drift`) |
| `language`, `bright`, `offscr`, `scr_clock` | … | MP3-player UI settings |
| `profile`, `pass`, `record`, `music`, `audio_volume`, `voltage` | … | player state |

Because the store is a log, `--all` shows the history (e.g. `audio_volume` written 6 times).

## Keys the factory tool knows for TWS products

`ui_develop/window_param.py` `UP_CFG`:

| key | default / options | label (translated) |
|---|---|---|
| `customer_name` | | customer name |
| `chip_serial_id` | `P262`, `247`, `TWS206`, `TWS208`, `MP3_01` | chip/board series — `247` = the 247Youth line, same vendor family as 377Youth |
| `board_name` | | solution name |
| `bt_name` | | Bluetooth name |
| `bt_addr` | `AA:BB:CC:DD:EE:FF` | Bluetooth address |
| `sn_info` | | serial number |
| `freq_drift` | `0` | frequency-offset calibration |
| `rfparam` | `0` | RF parameters |
| `bootup_flag` | `1`–`4` | power-on method (power key / mid level / 5 V always / vbus out) |
| `paired_flag` | `P` / `U` | TWS paired or unpaired |
| `ear_type` | `L` / `R` | which ear this bud is |
| `bat_level` | `0` | battery level info |
| `en_info`, `baseboard_ver_info`, `customer_ver_info` | | reference-design switch / versions |

## Keys the h2sturbo FIRM reads

55 NV key names appear in the 377 FIRM, including `key_tap2_*` / `key_long_*` (gesture → action
map), `ear_detection_en`, `authorization_code`, `air_*`, `eq_ud_gain`, `eq_preset_cur_num`, `bt_name`,
`bt_addr`, `paired_flag`, `ear_type`. The full list is in
[`data/analysis/firmware_internals.txt`](../data/analysis/firmware_internals.txt).

## Why it matters for CFW

* Gesture mapping, ear-detection, EQ preset and the Apple `authorization_code` live here → many
  "feature" changes may be **settings writes**, not firmware patches.
* The app's `C0` command set and the factory tool both write PSM; a Bluetooth path to set arbitrary
  keys hasn't been tested.
* To write PSMP offline we still need the 4-byte record check; `psm-nvds.dll`
  (`vendor/shenju-flashloader/`) implements it and can be run under Wine / disassembled.
