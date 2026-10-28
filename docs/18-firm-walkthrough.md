# 18 · FIRM walkthrough: dispatcher, command channel, settings, tasks

[17](17-firmware-internals.md) covers how the H3Pro Max3 `2607061716` image boots and how the
updater accepts an image. This page is the rest of FIRM, the 680 KiB program that runs the buds
day to day. Everything here comes from a whole-program Ghidra decompile (4512 functions) of the
`firm.elf` that [`tools/h3pro_elf.py`](../tools/h3pro_elf.py) produces, plus string and
literal-pool cross references. No symbols survive, so functions are named by address. Nothing was
run on or written to a bud.

## Runtime skeleton

FIRM runs on a small RTOS whose kernel core lives in the mask ROM (the SVC and SysTick vectors
point into ROM at `0xB4F5` and `0xB5A9`, PendSV into RAM at `0x827591`). Tasks are created with
`FUN_00829850(entry, arg, name, prio, stack)`.

| Task | Prio | Job |
|---|---|---|
| `task main` | 1 | event loop, runs the dispatcher below |
| `task btc` / `task bth` / `task bleh` / `bt_isr_bh` / `ble_isr_bh` | 9 / 9 / 7 / 19 | BT controller, host, BLE host, interrupt bottom halves |
| `bt audio server`, `amixer`, `tplayer`, `ain`, `audio ui` | 6 / 9 / 9 / 7 / 1 | A2DP/SCO sink, mixer, prompt player, mic input, UI sounds |
| `talk detect` | 8 | voice activity (talk-through / sidetone gating) |
| `tws process`, `tws_manager_task`, `tws_manager_mp_task` | 8 / 1 / 1 | ear-to-ear link and role management |
| `task motion`, `taskB motion` | 10 / 3 | LSM6DSOX IMU (head tracking, tap, motion wake) |
| `plxc_proximity_task`, `plxc_scan_task` | 2 / 1 | in-ear proximity sensor |
| `sensor-hr` | 1 | VC30Fx heart-rate sensor |
| `task siri` | 6 | voice assistant trigger (`AT+BVRA`, `AT+APLSIRI`) |
| `adc data`, `pmu_isr_bh`, `uart_isr_bh`, `spp_ota_bh` | 6 / 3 / 3 / 3 | battery ADC, charger/PMU events, UART console, SPP receive |

Timers go through `FUN_00ca47b4(&handle, name, ticks, callback, ?, periodic, arg)` with
`FUN_00829600(ms)` converting milliseconds. The named ones are `SleepTimer`, `otaStateTimer`,
`AncTimer`, `spaceSyncTimer`, `SeamlessTimer`, `BtSniffTimer`, `tws scan timeout`,
`ble find full timeout`, `motion detect`, `hr_s2`, `air fit timer`, `air motion tx timer`,
`air heartrate tx timer`, `ble air adv open timer` / `close timer`, `juplus restart timer`,
`TestUiTimer`.

ROM helpers FIRM calls into (on top of the ones in [17](17-firmware-internals.md)):
`0xC70` malloc, `0xC74` free, `0xAA2` strlen, `0xAB2` strcmp, `0xB6D8` / `0xB6C4` (always used as a
pair around shared state, so enter and leave critical section), `0xB78C` sleep for N ms.

### Event bus

Everything talks through one event queue. `FUN_00812144(id, payload, len)` posts (also
`FUN_0081232e` / `FUN_0081234c` for the no-payload forms) and `task main` hands each event to the
dispatcher `FUN_00c4fbc0(ev)`, where `ev[0]` is the id, `ev[1]` the length and `ev[2..]` the
payload. The top byte of the id is the source.

| Id family | Source |
|---|---|
| `0x50xxxxxx` | key / touch events |
| `0x80`, `0x81` | BT link state (`0x81000024` = power off request) |
| `0xB0`, `0xB2` | audio and HFP state |
| `0xC0300021` | A2DP/SCO link usage |
| `0xC1` | charger and VBUS (`0xC1000004` carries the `vbus_print` debug flag) |
| `0xD0`, `0xD1`, `0xD2`, `0xD3` | BT host, pairing, TWS link (`0xD000002E` = ANC mode change, `0xD0000027` = ANC set from app) |
| `0xF2`, `0xF3` | audio mode (`0xF2000018` = game mode toggle, `0xF3000002` = EQ change) |
| `0xF6` | app protocol (`0xF600000F` enter OTA, `0xF6000046` re-enter OTA after a slave handshake) |
| `0xF7` | app session (`0xF7000001` app authorized, `0xF7000002` / `3` settings changed) |

Anything the dispatcher does not recognise falls through to `FUN_00c4e68c`, which handles the
remaining BT and audio ids and forwards some to the other bud with peer opcode `0x20`.

A second queue, `FUN_00827564(module, 0, type, len, data)`, hands buffers to specific modules.
Module 7 is the SPP / UART transport (type 1 = `05` frames, 2 = `55AA` frames, 3 = reply to send).
Module 4 is the AirPods emulation ("air") layer.

## Flash and the partition index

`FUN_00805444(name, &len)` looks a four-letter partition name up in the RAM copy of the flash
index (count at `0x831efc`, 16-byte entries at `0x831f1c` holding name, address and length) and returns its
flash address. `FUN_0080576c(dst, addr, len)` reads flash, `FUN_008286a0(src, addr, len, 1, 0)`
writes it. FIRM uses them for `EQ2P` (EQ presets), `OTAP` (the boot-to-OTAP flag, see
[17](17-firmware-internals.md)) and for the `C0 83` flash-read command.

## NV store (PSMP) from FIRM's side

`FUN_00c6e768(key, buf, len)` reads a key and returns negative when it is missing.
`FUN_00c6e77c(key, buf, len)` writes. The store is log structured and compacted by
`FUN_00c6ed54`. The record format and its CRC32 check are in [09](09-psmp-nvds.md). Keys FIRM
touches, with the length it reads or writes and the default it falls back to.

| Key | Len | Notes |
|---|---|---|
| `bt_addr`, `bt_addr_backup`, `ble_addr` | 6 | `addr_backup_flag` (1) says whether the backup is valid |
| `bt_name` | up to 32 | rewritten at boot if it does not match the stack's name |
| `bt_vol` | 36 | per-device volume table |
| `device_id` | 64 | factory serial string, also read by the app auth check |
| `authorization_code`, `authorization_code_length` | up to 64, 4 | app channel unlock, see below |
| `sn_info`, `sn_l_info`, `sn_r_info` | 12 | serials for the set and each bud |
| `product_id`, `date_of_manufacture` | 4 | |
| `product_mode` | 15 | self-heals to `H3Pro Max3` at boot if different |
| `paired_flag`, `bootup_flag`, `startup_flag`, `ear_type` | 1 | |
| `link_info` | 118 | last phone link record |
| `link_phone_type` | 5 | |
| `anc_mode_sel` | 3 | ANC mode, phone-selected mode, extra byte |
| `anc_mode_phone_sel` | 1 | |
| `eq_preset_cur_num` | 1 | |
| `eq_ud_gain` | 56 | user-defined EQ gains |
| `ear_detection_en` | 1 | default 1 |
| `key_long_left_setting`, `key_long_right_setting` | 1 | values 1..3, defaults L=2, R=1 |
| `key_tap2_left_setting`, `key_tap2_right_setting` | 1 | values 2..5, default 4 |
| `kws_en` | 1 | keyword spotting enable |
| `motion_type`, `freq_drift` (2), `rfparam`, `vc30fx_oscclk_freq` (16), `vc30fx_sc`, `bat_level` (1), `vbus_print` (1) | | sensor and radio calibration, debug |
| `air_en`, `air_reset`, `air_clean`, `air_pair` (17), `air_link` (16), `air_adv_key` (16), `air_phone_addr`, `air_callctrl_setting`, `air_volumectrl_setting`, `air_audio_setting` (3) | | AirPods emulation state |

## The command channel

### Receive demux (`FUN_00c4f0cc`)

Every SPP (and UART) frame lands here. First byte `C0`, `05` or `55` goes to the StarFun handler
`FUN_00c69b3c`. `E0` and `A0..AF` frames are dropped. Anything else is tried as a text command
beginning with `+test=`.

| Command | Effect | Reply |
|---|---|---|
| `+test=recover` | factory reset (`FUN_00c6ae2c`, `FUN_00c4f014`, `FUN_00c6aac0`) | `-recover\r` |
| `+test=version` | | `-version=<version>\r` |
| `+test=shutdown` | posts `0x81000024` | `-shutdown\r` |
| `+test=encen` / `+test=encdis` | toggles ENC / sidetone paths (`FUN_00c602f8`, `FUN_00c60324`) | `-encdis\r` |
| `+test=getaddr` | | `-getaddr=<l|r|0>_<6 bytes hex>` |
| `+test=pair_<l|r><12 hex>` | sets the peer address for TWS pairing (`FUN_00c6ad78`) | |
| `+test=vbusp:<0|1>` | NV `vbus_print`, mirrored to the peer | |

### StarFun `C0` commands, part 1 (`FUN_00c69b3c`)

Frame is `C0 <cmd> <payload>`, reply is `C0 <cmd> <len> <payload>` sent with
`FUN_00c69870(buf, len + 3)`. `FUN_00824b24()` returns 1 for the master bud and 2 for the slave.
Settings writes are mirrored to the other bud with `FUN_00c6cdf0(opcode, data, len)`.

| Cmd | Direction | What |
|---|---|---|
| `01` | auth step 1 | 64-byte challenge, reply `3D 'S' 'L'` + 59 scrambled bytes (only if the unit is authorized, see below) |
| `02` | auth step 2 | 64-byte verify, reply 61 bytes, marks the session verified and posts `0xF7000001` |
| `03` | read | marketing model string (table below) |
| `05` | read | firmware version as 11 decimal chars (`0x9B649AD4` = `2607061716`, baked into code) |
| `06`, `53` | read | BT address, reversed |
| `07` | read | `device_id` (64) |
| `14`, `15` | read | `product_id`, `date_of_manufacture` |
| `50` / `60` | read / write | `air_en`, mirrored with opcode `0x18` |
| `51`, `70`, `71` | read | `sn_info`, `sn_l_info`, `sn_r_info` |
| `54` | read | BT name |
| `61`, `80`, `81` | write | `sn_info`, `sn_l_info`, `sn_r_info` (opcodes `0x19`, `0x40`, `0x41`) |
| `63` | write | BT address from payload (opcode `0x1B`) |
| `64` | write | BT name, up to 31 chars |
| `83` | read | flash read, `addr(4) len(4)`, up to 200 bytes per frame, no address check (this is what [16](16-live-flash-dump.md) uses) |

Frames starting `05` and `55` are handed to module 7 as type 1 and 2, which is where the
`55AA 8x` OTA frames from [06](06-bt-ota-protocol.md) go while FIRM is still running.

The model string for `03` comes from a 16-byte name FIRM gets through module 7 (`sn_info`
style), compared against a table, with a `product_id` fallback.

| Stored name | Reply |
|---|---|
| `H2S Ultra` | `277` |
| `H2S Turbo` | `277Pro Max` |
| `H3sProMax` | `377H3` |
| `H3Pr` / `H3Pro` / `H3Pro Max3` | `H3Pro` |
| `377Super PRO3` | `Super2026+` |
| `product_id` `0x247`, `0x277`, `0x247B`, `0x206`, `0x200`, `0x200E`, `0x247C` | `247`, `277`, `247B`, `247C` style codes |

So the same FIRM is built to answer for several Huilian generations. The literal `H3Pro Max3`
appears in the `product_mode` self-heal, the `C0 04` reply and the TWS name exchange, so this build
is pinned to the H3Pro Max3 even though it knows the other names.

### StarFun `C0` commands, part 2 (`FUN_00c52e4c`)

Reached through `FUN_00c53260` case 0. Reads reply with one byte unless noted.

| Cmd | What |
|---|---|
| `04` | model string, literal `H3Pro Max3` |
| `08`, `13` | constant 3 |
| `09` | battery, 3 bytes: left, right, case (`FUN_00c538e4`) |
| `0A` | in-ear state |
| `0B`, `0D`, `0E`, `0F`, `11`, `16`, `17` | constant 1 (capability flags) |
| `0C` | constant `0xA1` |
| `10` | which bud answers, `0x11` left, `0x22` right |
| `12` | link state, 0 both buds, 1 one bud, 2 no peer |
| `52` / `62` | read / write a one-byte mode (`DAT_0082d3a0`), write posts `0xF3000002` (EQ) |
| `55` / `65` | `ear_detection_en` (peer `0x32`) |
| `56` / `66`, `57` / `67`, `58` / `68` | three more one-byte settings (`0x33`, `0x34`, `0x35`), writes post `0xF7000003` / `0xF7000002` |
| `59` / `69` | ANC mode read / set. Set takes an index into `{0, 1, 2, 5}` = off, ANC, transparency, adaptive and posts `0xD0000027` |
| `5A` / `6A`, `5B` / `6B` | long-press action left / right (`0x36`, `0x37`) |
| `5C` / `6C`, `5D` / `6D` | double-tap action left / right (`0x38`, `0x39`) |
| `5E` / `6E` | game (low latency) mode, read returns 1 when on, write posts `0xF2000018` |
| `76`, `77`, `85`, `86`, `87`, `EE` | AirPods-emulation flags 5, 6, 7 (a 9-byte flag block handed to module 4) |
| `90` | EQ preset block (`FUN_00c52630`, loaded from the `EQ2P` partition, current preset from `eq_preset_cur_num`) |
| `92`, `93`, `94`, `A4` | user EQ block (`eq_ud_gain`), its 4-byte header, per-band read, and write (peer `0x3C`) |
| `A0` | one-byte EQ related write (peer `0x3A`) |

### App authorization

At boot `FUN_00c698c4` reads `device_id`, `authorization_code_length` (max 64) and
`authorization_code`, runs the code through the scrambler `FUN_00c71492(0x756, buf, len)` and
requires bytes 13..15 of the result to read `APP`. Only then does the bud answer `C0 01`. The
scrambler is `FUN_00c7144c`, a 16-bit LFSR (`s = rotl16(s, 1) ^ (s & 0x8000 ? 0xD103 : 0)`) clocked
once per input bit, so it is obfuscation rather than cryptography. `C0 01` seeds it from two
challenge bytes XOR `0x3098` and returns 59 bytes, `C0 02` runs four passes with seeds derived
from the challenge (`^ 0x1728`, a byte sum, `^ 0x358`) and XOR mixes in the challenge. This matches
`CMDConfig.verificationCmd` in the app ([02](02-starfun-app.md)) and is the only gate on the
command channel. OTA frames do not go through it.

### Entering OTA from FIRM (`FUN_00c4ecc4`)

When a `55AA 80` frame completes, FIRM replies with status 0, or 3 when the battery level
(`FUN_00c6bd90`) is below 2, and the answering side (`0x11` / `0x22`). The master then tells the
slave with peer opcode `0x0E` and starts `otaStateTimer` (2 s, retried twice by `FUN_00c4ebd4`
before giving up and entering alone). The slave, or the master once the slave is ready, posts
`0xF600000F` with payload 1. The dispatcher then flushes `link_info`, `link_phone_type` and
`bt_name` to NV, shuts down the AirPods layer (`FUN_00c5522c`), re-checks `product_mode`, writes
the `0x55AA` flag (`FUN_00c6ad1c`, [17](17-firmware-internals.md)), drops the BT links
(`FUN_00c8df50`) and reboots.

### Peer sync opcodes (`FUN_00c6cdf0`)

Settings changes travel to the other bud as `opcode + bytes`. `0x0E` OTA enter, `0x15` ANC state (4 bytes),
`0x18` `air_en`, `0x19` / `0x40` / `0x41` serials, `0x1A` mode `62`, `0x1B` BT address, `0x1F` AirPods
advert key, `0x20` forwarded events, `0x32`..`0x3C` the one-byte settings above, `0x46` OTA
state, `0x4B` / `0x4C` link records. Each handler is a small function that stores the byte and,
on the master, calls `FUN_00c6cdf0`, so adding a setting is mechanical.

## Settings semantics

* ANC mode byte values are 0 off, 1 ANC, 2 transparency, 5 adaptive. `FUN_00c51418` maps them to the
  prompts `close.mp3`, `noise.mp3`, `pass_those.mp3`, `adpt.mp3` ([07](07-tone-sfx.md)).
  The three `anc_mode_sel` bytes are the live state at `0x834307`, `0x834305`, `0x834306`.
* Gesture values are clamped by their setters to 1..3 for long press and 2..5 for double tap. The UI strings in
  the app give the meaning of each number.
* Game mode is a 0/2 value posted as `0xF2000018` into the audio path.
* Ear detection defaults on and gates the in-ear events from `plxc_proximity_task`.

## AirPods emulation layer

Module 4 is the "air" layer from [10](10-aap-airpods.md). This build carries six Apple identities,
stored XOR `0x59` at `0xC4A9E0`..`0xC4BC80` (flash `0x4A9E0`). They are AirPods `A2031` and `A2564`,
AirPods 3 `A3054` / `A3057`, AirPods Max `A2096` and AirPods Pro `A3048`, each with name, model,
`Apple Inc.`, a serial, version string, `com.apple.accessory.updater.app[.multiasset]`, a firmware
build number (`6619472`, `8454768`, `5507184`) and two Unix timestamps. The model list
`2031 2564 3054 3057 2096 3048` sits right after it. The plaintext identity blob and the SDP
Device-ID records (nine Apple PIDs, `0x200A`..`0x2027`) that [10](10-aap-airpods.md) describes are
also present, and the Continuity advert template is at `0xC4BF58` (flash `0x4BF58`) with model bytes `0E 20`.
Which identity is advertised is picked at runtime by the air layer, not by a build constant.

The layer has its own timers (`air fit timer`, `air motion timer`, `air heartrate tx timer`,
`air resp timer`, `ble air adv open/close timer`) and feeds head-tracking frames
(`devmotion6`, `H2HTransformation`) from the IMU task and heart rate from `sensor-hr`. HFP side strings are
`AT+XAPL=0042-0887-0100,2`, `AT+IPHONEACCEV=1,1,8`, `AT+APLSIRI`, `AT+BAC=1,2` (CVSD and mSBC),
`AT+BRSF=157` / `159`.

## Hardware blocks

| Base | Block | How we know |
|---|---|---|
| `0x40000000` | PMU / power and reset | boot, sleep and interrupt-state helpers |
| `0x40009000` | SYSCTRL, clock gates and dividers | `FUN_00ca32bc` toggles per-peripheral enable bits and dividers at `0x40009134`..`0x400092B8` |
| `0x40030000`, `0x40037000`, `0x40038000` | BT baseband and BLE | used by `task btc` / `task bleh` code |
| `0x40036000` | radio (RF calibration) | the calibration code near `0xC97000`..`0xC9A000` only touches this block |
| `0x40097000` | audio I2S / TDM | strings `6wire mode`, `bclk1 slot num`, `bclk1 slot width`, `LR1 pol`, `gpio cfg sd7` |
| `0xE000Exxx` | Cortex-M SCB / NVIC | |

Sensors are an LSM6DSOX IMU (strings `6dsox`), a VC30Fx optical heart-rate sensor (`vc30fx_*` NV
keys, `HeartRateService`), PLXC proximity for in-ear detection.

Factory audio tuning goes over AT. `AT+MICTEST=`, `AT+ANCTEST=`, `AT+ANCFFG=` / `ANCFBG=` / `ANCAG=` /
`ANCDG=` set feed-forward, feedback, ambient and a fourth ANC gain live, which is the hook behind
[11](11-anc-transparency.md).

## What this gives a CFW

* Every user-facing setting is a one-byte NV key with a `C0` read and write pair, so a companion
  app needs no firmware change. The gate is the `C0 01` / `02` handshake, which is a reproducible
  LFSR, and OTA frames bypass it anyway.
* `C0 83` reads any flash address. The matching write is the OTA path only.
* Model and identity strings are data in FIRM, with two literal `H3Pro Max3` sites that would need
  patching to rebrand.
* The AirPods identity table is plain data (XOR `0x59`) and could be swapped without touching code.

## Handy addresses

| Address | What |
|---|---|
| `0xC4FBC0` | event dispatcher |
| `0xC4E68C` | dispatcher fallthrough (BT / audio ids, peer forward) |
| `0xC4F0CC` | SPP / UART receive demux and `+test=` console |
| `0xC69B3C` | StarFun `C0` handler, part 1 |
| `0xC52E4C` | StarFun `C0` handler, part 2 |
| `0xC69870` | send a `C0` reply |
| `0xC698C4` / `0xC69958` / `0xC699A6` | authorization check, `C0 01`, `C0 02` |
| `0xC71492` / `0xC7144C` | LFSR scrambler |
| `0xC4ECC4` | `55AA 80` enter-OTA handling |
| `0xC6CDF0` | send to the other bud |
| `0xC6E768` / `0xC6E77C` | NV read / write |
| `0x805444` / `0x80576C` / `0x8286A0` | partition lookup, flash read, flash write |
| `0x829850` / `0xCA47B4` | task create, timer create |
| `0x812144` / `0x827564` | post event, post to module |
| `0xC51418` | ANC prompt map |
| `0xCA32BC` | clock gate driver |
