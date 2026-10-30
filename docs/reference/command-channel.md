# Command channel (`C0`)

The buds take commands over Bluetooth SPP, RFCOMM channel 3. Frames start with `C0` for
normal commands and `55 AA` for the updater ([OTA protocol](ota-protocol.md)). Only one SPP
connection is allowed at a time. `tools/hl` implements all of this, and `hl cmd <hex>` sends a raw
frame.

## Frames

Request `C0 <cmd> <payload>`, reply `C0 <cmd> <len> <payload>`. Multi-byte values are
little-endian. Writes to settings are copied to the other bud by the firmware.

## Authorization

`C0 01` sends a 64-byte challenge and `C0 02` a 64-byte verify. Both are scrambled with a 16-bit
LFSR (`s = rotl16(s, 1) ^ (s & 0x8000 ? 0xD103 : 0)`, clocked once per input bit, XOR keystream).
It is obfuscation, not a cipher. `tools/huilian/proto.py` implements both sides. A unit whose
PSMP `authorization_code` doesn't descramble to `APP` never answers `C0 01`, so any reply means
the unit is authorized. `hl auth` runs the exchange. The `55 AA` updater frames don't need it.

## Commands

### Identity, serials and flash read


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
| `83` | read | flash read, `addr(4) len(4)`, up to 200 bytes per frame, no address check (this is what [device](device.md) uses) |

Frames starting `05` and `55` are handed to module 7 as type 1 and 2, which is where the
`55AA 8x` OTA frames from [OTA protocol](ota-protocol.md) go while FIRM is still running.

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

### Status and settings

Reads reply with one byte unless noted.

| Cmd | What |
|---|---|
| `04` | model string, literal `H3Pro Max3` |
| `08`, `13` | constant 3 |
| `09` | battery, 3 bytes: left, right, case |
| `0A` | in-ear state |
| `0B`, `0D`, `0E`, `0F`, `11`, `16`, `17` | constant 1 (capability flags) |
| `0C` | constant `0xA1` |
| `10` | which bud answers, `0x11` left, `0x22` right |
| `12` | link state, 0 both buds, 1 one bud, 2 no peer |
| `52` / `62` | read / write a one-byte mode, write posts `0xF3000002` (EQ) |
| `55` / `65` | `ear_detection_en` (peer `0x32`) |
| `56` / `66`, `57` / `67`, `58` / `68` | three more one-byte settings (`0x33`, `0x34`, `0x35`), writes post `0xF7000003` / `0xF7000002` |
| `59` / `69` | ANC mode read / set. Set takes an index into `{0, 1, 2, 5}` = off, ANC, transparency, adaptive and posts `0xD0000027` |
| `5A` / `6A`, `5B` / `6B` | long-press action left / right (`0x36`, `0x37`) |
| `5C` / `6C`, `5D` / `6D` | double-tap action left / right (`0x38`, `0x39`) |
| `5E` / `6E` | game (low latency) mode, read returns 1 when on, write posts `0xF2000018` |
| `76`, `77`, `85`, `86`, `87`, `EE` | AirPods-emulation flags 5, 6, 7 (a 9-byte flag block handed to module 4) |
| `90` | EQ preset block (loaded from the `EQ2P` partition, current preset from `eq_preset_cur_num`) |
| `92`, `93`, `94`, `A4` | user EQ block (`eq_ud_gain`), its 4-byte header, per-band read, and write (peer `0x3C`) |
| `A0` | one-byte EQ related write (peer `0x3A`) |

### In the updater

A bud in the updater (OTAP) only answers `C0 04`, `05`, `09`, `51` and the `83` flash read. It
doesn't answer `C0 0A` or the serial reads.

## The `+test=` console

Frames that start with `C0`, `05` or `55` go to the normal command handlers. `E0` and `A0..AF` frames are dropped. Anything else is tried as a text command
beginning with `+test=`.

| Command | Effect | Reply |
|---|---|---|
| `+test=recover` | factory reset | `-recover\r` |
| `+test=version` | | `-version=<version>\r` |
| `+test=shutdown` | posts `0x81000024` | `-shutdown\r` |
| `+test=encen` / `+test=encdis` | toggles ENC / sidetone paths | `-encdis\r` |
| `+test=getaddr` | | `-getaddr=<l|r|0>_<6 bytes hex>` |
| `+test=pair_<l|r><12 hex>` | sets the peer address for TWS pairing | |
| `+test=vbusp:<0|1>` | NV `vbus_print`, mirrored to the peer | |

Firmware addresses for every handler are in [research: command channel](../research/command-channel.md).
