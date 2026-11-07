# Command channel

FIRM routes SPP and UART traffic to the StarFun binary protocol or a hidden text console. Two `C0` handlers expose identity, settings and flash reads, while a 16-bit LFSR implements the app challenge/response.

## Receive demux and text console

Every SPP and UART frame reaches `FUN_00c4f0cc` at `0xC4F0CC`.

| First byte | Destination |
|---|---|
| `C0`, `05`, `55` | `FUN_00c69b3c` |
| `E0`, `A0` through `AF` | Drop |
| Anything else | Try a text command beginning with `+test=` |

| Text command | Action | Reply |
|---|---|---|
| `+test=recover` | Factory reset through `FUN_00c6ae2c`, `FUN_00c4f014` and `FUN_00c6aac0` | `-recover\r` |
| `+test=version` | Read version | `-version=<version>\r` |
| `+test=shutdown` | Post `0x81000024` | `-shutdown\r` |
| `+test=encen`, `+test=encdis` | Toggle ENC/sidetone paths through `FUN_00c602f8` and `FUN_00c60324` | `-encdis\r` |
| `+test=getaddr` | Read address and side | `-getaddr=<l|r|0>_<6 bytes hex>` |
| `+test=pair_<l|r><12 hex>` | Set the TWS peer address through `FUN_00c6ad78` | Not specified |
| `+test=vbusp:<0|1>` | Store `vbus_print` and mirror it to the peer | Not specified |

The factory ANC AT parser is a separate [audio surface](audio-and-dsp.md#factory-anc-controls). Reaching it over H3Pro SPP through this console is likely but unverified.

## C0 framing and routing

Requests use `C0 <cmd> <payload>`. Ordinary replies use `C0 <cmd> <len> <payload>` and are sent by `FUN_00c69870(buf, len + 3)`.

`FUN_00824b24()` returns 1 for the master bud and 2 for the slave. Settings writes use `FUN_00c6cdf0(opcode, data, len)` to mirror changes.

Frames starting with `05` and `55` go to module 7 as types 1 and 2. This includes `55AA 8x` OTA frames while FIRM is running. The [runtime module map](firm-runtime.md#module-dispatch) describes the dispatch APIs.

## C0 handler part 1

`FUN_00c69b3c` at `0xC69B3C` handles these commands.

| Command | Direction | Behavior |
|---|---|---|
| `01` | Auth step 1 | Accept a 64-byte challenge and reply with `3D 'S' 'L'` plus 59 scrambled bytes, if the device authorization check passes |
| `02` | Auth step 2 | Verify 64 bytes, reply with 61 bytes, mark the session verified and post `0xF7000001` |
| `03` | Read | Marketing model string from the name table below |
| `05` | Read | Firmware version as 11 decimal characters, code constant `0x9B649AD4` means `2607061716` |
| `06`, `53` | Read | Reversed Bluetooth address |
| `07` | Read | `device_id`, 64 bytes |
| `14`, `15` | Read | `product_id`, `date_of_manufacture` |
| `50`, `60` | Read, write | `air_en`, peer opcode `0x18` |
| `51`, `70`, `71` | Read | `sn_info`, `sn_l_info`, `sn_r_info` |
| `54` | Read | Bluetooth name |
| `61`, `80`, `81` | Write | `sn_info`, `sn_l_info`, `sn_r_info`, peer opcodes `0x19`, `0x40`, `0x41` |
| `63` | Write | Bluetooth address from payload, peer opcode `0x1B` |
| `64` | Write | Bluetooth name, up to 31 characters |
| `83` | Read | Flash address and length as two four-byte fields, up to 200 bytes per reply, no address check |

`03` obtains a 16-byte name through module 7 in the style of `sn_info`, compares it with a table, then falls back to `product_id`.

| Stored name or product ID | Reply |
|---|---|
| `H2S Ultra` | `277` |
| `H2S Turbo` | `277Pro Max` |
| `H3sProMax` | `377H3` |
| `H3Pr`, `H3Pro`, `H3Pro Max3` | `H3Pro` |
| `377Super PRO3` | `Super2026+` |
| `product_id` in `0x247`, `0x277`, `0x247B`, `0x206`, `0x200`, `0x200E`, `0x247C` | `247`, `277`, `247B`, `247C`-style codes, exact per-ID mapping unspecified |

This table supports several Huilian product names. The build still uses literal `H3Pro Max3` in `product_mode` repair, the `C0 04` reply and TWS name exchange. Rebranding requires changes to the relevant code literals as well as identity data. The source identifies two literal sites as patch targets.

## C0 handler part 2

`FUN_00c52e4c` at `0xC52E4C` is reached through case 0 of `FUN_00c53260`. Read replies contain one byte unless the table says otherwise.

| Command | Behavior |
|---|---|
| `04` | Literal model string `H3Pro Max3` |
| `08`, `13` | Constant 3 |
| `09` | Three battery bytes, left, right and case, through `FUN_00c538e4` |
| `0A` | In-ear state |
| `0B`, `0D`, `0E`, `0F`, `11`, `16`, `17` | Constant 1, capability flags |
| `0C` | Constant `0xA1` |
| `10` | Answering side, `0x11` left or `0x22` right |
| `12` | Link state, 0 for both buds, 1 for one bud, 2 for no peer |
| `52`, `62` | Read/write one-byte mode at `DAT_0082d3a0`. Write posts EQ event `0xF3000002` and uses peer `0x1A` |
| `55`, `65` | Read/write `ear_detection_en`, peer `0x32` |
| `56`, `66` | Read/write another one-byte setting, peer `0x33` |
| `57`, `67` | Read/write another one-byte setting, peer `0x34` |
| `58`, `68` | Read/write another one-byte setting, peer `0x35` |
| `59`, `69` | Read/set ANC mode. Setter indexes `{0, 1, 2, 5}` for off, ANC, transparency and adaptive, then posts `0xD0000027` |
| `5A`, `6A` | Read/write left long-press action, peer `0x36` |
| `5B`, `6B` | Read/write right long-press action, peer `0x37` |
| `5C`, `6C` | Read/write left double-tap action, peer `0x38` |
| `5D`, `6D` | Read/write right double-tap action, peer `0x39` |
| `5E`, `6E` | Read/write game mode. Read returns 1 when enabled. Write posts `0xF2000018` |
| `76`, `77`, `85`, `86`, `87`, `EE` | AirPods flags 5, 6 and 7 in a nine-byte flag block passed to module 4 |
| `90` | EQ preset block through `FUN_00c52630`, loaded from EQ2P with current preset from `eq_preset_cur_num` |
| `92`, `93`, `94`, `A4` | User EQ block `eq_ud_gain`, its four-byte header, per-band read and write, peer `0x3C` |
| `A0` | One-byte EQ-related write, peer `0x3A` |

Writes to the `56/66`, `57/67` and `58/68` setting group post `0xF7000003` or `0xF7000002`. The source does not assign each event to an individual pair. See [settings semantics](settings-store.md#setting-semantics).

## Flash reads

`C0 83` uses a normal type-1 command without CRC8.

```text
C0 83 <flash address, u32 LE> <length, u32 LE>
C0 83 <address> <length> <data...>
```

The second line is the documented flash-read reply shape. The device returns at most 200 bytes per frame, regardless of the requested length. There is no address-range restriction.

Stock FIRM always reads SPI flash through `FUN_0080576c`. The [ROM read patch](rom-read.md) reroutes that call so an address with bit 31 set is copied straight from memory instead, which reaches the mask ROM, RAM and peripheral registers.

The app's `OtaCmdConfig.getReadFlashCmdArray()` reads 200 bytes from index address `0x3000`, also named `INDEX_START_ADDRESS = 12288`, then reads TONE and EQ2P in 100-byte blocks to preserve them for an update. `CMDConfig.getReadFlashCmdArray(addr,len)` is the entry used by [flashdump.js](../../tools/flashdump.js), which sends through `BtClient.sendBytes(cmd, 1)` and receives through `BtBase.notifyUI`.

[tools/hl](../../tools/hl) can authenticate and read over a plain RFCOMM socket. The command has no matching general flash-write command in this FIRM surface. OTA supplies the write path. The [command-channel reference](../reference/command-channel.md) covers use, and [OTA protocol](../reference/ota-protocol.md) covers update framing.

## Firmware authorization

At boot, `FUN_00c698c4` reads `device_id`, `authorization_code_length` and `authorization_code`. The authorization length is capped at 64. It runs `FUN_00c71492(0x756, buf, len)` and requires decoded bytes 13 through 15 to contain `APP`. Only then does the device answer `C0 01`.

| Address | Role |
|---|---|
| `0xC698C4` | `FUN_00c698c4`, boot authorization check |
| `0xC69958` | `C0 01` handler |
| `0xC699A6` | `C0 02` handler |
| `0xC7144C` | `FUN_00c7144c`, LFSR scrambler |
| `0xC71492` | `FUN_00c71492`, scrambler entry used by the authorization check |

The state is 16 bits and advances once per input bit.

```text
s = rotl16(s, 1) ^ (s & 0x8000 ? 0xD103 : 0)
```

`C0 01` derives the seed from two challenge bytes XOR `0x3098` and returns 59 scrambled bytes. `C0 02` makes four passes with challenge-derived seeds, including XOR `0x1728`, a byte sum and XOR `0x358`, and XOR-mixes the challenge into the result.

This matches the app's `CMDConfig.verificationCmd`. The LFSR is reproducible obfuscation and is the app-session gate on the command channel. OTA frames bypass it. `tools/hl ota` does not need the handshake.

## Native library

The StarFun `2.0.7.016` APK contains `lib/arm64-v8a/libuparser-lib.so`. The APK is downloadable from the OTA CDN without auth.

| JNI export | Native implementation | Behavior |
|---|---|---|
| `BtUtils.encryptData` | `SmartLinkCore::CLFSR::Encrypt_Data` then `Encrypt_OneByte` | Same 16-bit LFSR as FIRM |
| `BtUtils.getCrc` | `SmartLinkCore::CLFSR::get_crc` | CRC16/CCITT-FALSE, polynomial `0x1021`, MSB-first |
| `BtUtils.crc8Maxim` | `SmartLinkCore::CLFSR::crc8_maxim` | CRC8/Maxim, polynomial `0x31`, reflected form `0x8C` |

`Encrypt_OneByte` clocks the LFSR eight times per byte and XORs the keystream in place. Its byte output matches [huilian/proto.py](../../tools/huilian/proto.py), which implements the handshake used by `hl auth`. This mechanism does not verify firmware images.

## Entering OTA from FIRM

`FUN_00c4ecc4` handles a completed `55AA 80` frame. It replies with status 0, or status 3 if `FUN_00c6bd90` reports battery below 2, and includes the answering side `0x11` or `0x22`.

1. The master sends peer opcode `0x0E` and starts a 2 s `otaStateTimer`.
2. `FUN_00c4ebd4` retries twice. If the slave does not become ready, the master enters alone.
3. The slave, or the master once the slave is ready, posts `0xF600000F` with payload byte 1.
4. `FUN_00c4fbc0` flushes `link_info`, `link_phone_type` and `bt_name` to NV.
5. It shuts down the AirPods layer through `FUN_00c5522c`, rechecks `product_mode` and sets the `0x55AA` flag through `FUN_00c6ad1c`.
6. It drops Bluetooth links through `FUN_00c8df50` and reboots. The dispatch path arms a 5 s `otaStateTimer`.

The 2 s peer timer and 5 s reboot timer belong to different stages. [Memory map and boot](memory-map-and-boot.md#the-0x55aa-flag) covers selection of OTAP at reboot. [OTAP updater](updater-otap.md) covers the mandatory `04` exit and its separate `C0` dispatcher.
