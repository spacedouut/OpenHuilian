# AirPods layer

FIRM implements an Apple Accessory Protocol server, accessory HID services, Continuity advertising and Apple HFP extensions. Module 4 connects those services to NV settings, peer state, battery readings, motion data and heart rate.

## Service structure

Module 4's handler `FUN_00c54da8` provides about 40 internal service types. They include state getters, battery, peer relays and get/set operations for `air_link`, `air_adv_key`, `air_pair`, `air_reset`, `air_clean`, `air_phone_addr`, `air_en` and serial fields.

The phone-facing protocol runs over L2CAP PSM `0x1001`. The same L2CAP event dispatcher also handles `0x1007` and `0x1F`.

| Address | Function | Role |
|---|---|---|
| `0xC54CC0` | `FUN_00c54cc0` | Broadcast AAP connection-state changes |
| `0xC54DA8` | `FUN_00c54da8` | Internal module-4 service dispatch |
| `0xCA4BE0` | `FUN_00ca4be0` | Connection-object lookup/create helper |
| `0xCA4C48` | `FUN_00ca4c48` | Connection-object lookup/create helper |
| `0xCA4C6C` | `FUN_00ca4c6c` | Connection-object lookup/create helper |
| `0xCA6900` | `FUN_00ca6900` | Disconnect confirmation |
| `0xCA696E` | `FUN_00ca696e` | Connect confirmation |
| `0xCA738C` | `FUN_00ca738c` | Cleanup |
| `0xCA73D2` | `FUN_00ca73d2` | Disconnect indication |
| `0xCA832C` | `FUN_00ca832c` | Connect indication |
| `0xCA87D4` | `FUN_00ca87d4` | Phone-facing AAP opcode switch, 966 bytes |
| `0xCA8BC0` | `FUN_00ca8bc0` | L2CAP data indication, event-dispatch case 9 |
| `0xCA8C04` | `FUN_00ca8c04` | L2CAP events, cases 0 through `0xB` for connect, disconnect and data |
| `0xCAB92C` | `FUN_00cab92c` | Continuity advert builder |
| `0xCABE28` | `FUN_00cabe28` | AAP connection state machine, cases 1 through 5, controls adverts and peer sync |

The source also contains a statement that the wire opcode switch is unlocated. Its concrete `FUN_00ca8bc0` to `FUN_00ca87d4` mapping and opcode table supersede that statement. The completeness of this implementation compared with real AirPods is still unknown.

## AAP opcodes

After the SDP exchange, L2CAP data indication `FUN_00ca8bc0` passes AAP frames to `FUN_00ca87d4`. The opcode is frame byte 4. Dispatch structure is directly read from code. Semantic names remain likely where the operation has no independent mapping.

| Opcode | Dispatch behavior |
|---|---|
| `0x00` | Inspect byte 0. `02` sets connection state 3 and applies a battery gate before `FUN_00c8b1c4`. `03` sets a flag |
| `0x01` | Require `00 00 04 00`, then connection transition 0 and `FUN_00ca503c`, likely session open/negotiate |
| `0x09` | Inspect byte 6 using the subcommand table below |
| `0x10` | `FUN_00ca80d0(..., 0x10, ...)` |
| `0x12` | Pass a six-byte payload to `FUN_00c6a60c` |
| `0x14` | Connection transition `0x40` |
| `0x17` | `FUN_00ca78b4` and `FUN_00ca5138` |
| `0x1A` | NUL-terminated string with u16 length at byte 7, module-4 post `0x17`, likely name/notification text |
| `0x1E` | Inspect byte 6. `01` selects transition `0xB5`, `06` selects `0xB6`, `0x23` selects `0xB7` |
| `0x1F` | Subdispatch on bytes 6 and 7, including `02` and `01`. Remaining semantics unspecified |
| `0x21` | Remember the connection through `DAT_00ca8bb8` and call `FUN_00ca5090` |
| `0x22` | Check `FUN_00ca910c` and `FUN_00ca90a4`. State in 3 through 5 or `0xA1` leads to `FUN_00ca761c(0xC0)` |
| `0x24` | `FUN_00ca953c(3, byte8 & 0xDF)` |
| `0x25` | `FUN_00ca953c(4, byte7)` and battery-gated `FUN_00ca65b8` |
| `0x26` | `FUN_00ca9610(byte7)` and battery-gated `FUN_00ca65e8` |
| `0x28` | `FUN_00ca9624(byte7)` and battery-gated `FUN_00ca6618` |
| `0x31` | `FUN_00ca9f08(frame + 0xB)` on the AES path, then `FUN_00ca6680` |
| `0x39` | `FUN_00ca9688(byte7)` |
| `0x4B` | Require `03 00 03` and either `00 00` or `01 02` at bytes 9 and 10, then module-4 post `0x3A`. Likely noise-control/listen-mode command |
| `0x4D` | `FUN_00ca928c(conn, 0x81)` and `FUN_00ca879c` |
| `0x4F` | `FUN_00ca53f8` |

| `0x09` byte-6 subcommand | Behavior |
|---|---|
| `0x16` | `FUN_00ca953c(1, nib)` |
| `0x0C` | `FUN_00ca953c(2, nib)` |
| `0x0D` | Module-4 post `0x1A` and `FUN_00ca7e74` |
| `0x12` | `FUN_00ca9370` |
| `0x10` | `FUN_00ca953c(0, b)` and `FUN_00ca80a8` |
| Default | Module-4 post `0x12`, then a `0x5DD`-tick freshness window and `FUN_00ca4d54(..., 0x906)` when battery is greater than 1 |

`FUN_00ca953c(slot, value)` is a shared AAP state setter. The source calls it “4 slots, 0-4”, which is internally inconsistent. The opcode calls explicitly use slot arguments 0, 1, 2, 3 and 4.

## Peer AAP transport

| Address | Function | Behavior |
|---|---|---|
| `0xC87724` | `FUN_00c87724` | Send AAP frame with first header byte `0x20` |
| `0xC87760` | `FUN_00c87760` | Send AAP frame with first header byte `0x40` |
| `0xC87798` | `FUN_00c87798` | Send AAP frame with first header byte `0x10` |
| `0xC87834` | `FUN_00c87834` | Parse ear-to-ear AAP sync types `0x10`, `0x20`, `0x30`, `0x40`, `0x50` |

The general peer transport also carries advert keys with opcode `0x1F`. See [peer sync](firm-runtime.md#peer-sync).

## Identity data

The H3Pro carries six Apple identities stored XOR `0x59` at CPU `0xC4A9E0` through `0xC4BC80`, beginning at flash `0x4A9E0`.

| Identity group | Models |
|---|---|
| AirPods | `A2031`, `A2564` |
| AirPods 3 | `A3054`, `A3057` |
| AirPods Max | `A2096` |
| AirPods Pro | `A3048` |

Each record includes a name, model, `Apple Inc.`, a serial field, a version string, `com.apple.accessory.updater.app` or its `.multiasset` form, a firmware build number and two Unix timestamp fields. The listed firmware build numbers are `6619472`, `8454768` and `5507184`. No per-unit field values are reproduced here.

The model list `2031 2564 3054 3057 2096 3048` follows the table. Runtime state selects the advertised identity. The table can be replaced as XOR-encoded data without changing its code.

H3Pro also has a plaintext identity blob and SDP Device-ID records for nine Apple product IDs within `0x200A` through `0x2027`. Its identity plist uses a shared hardcoded serial field and a different `CFG#` from h2sturbo. The identity data does not supply a unique serial per device.

## SDP and HID descriptors

The detailed SDP offsets below refer to `h2s_turbo_2506281656.up`, the 377-generation SL6801 build. Its SDP region is FIRM-relative `0x55000` through `0x55930`. They are not H3Pro CPU addresses.

| Record | Identity | Transport or attribute |
|---|---|---|
| AAP Server | Service UUID `74ec2172-0bad-4d01-8f77-997b2be0722a`, profile UUID `4b6f7c74-07f4-49de-b0b9-ab4304728f29`, version 1.0 | L2CAP PSM `0x1001` |
| Device ID/PnP | Apple vendor `0x004C`, products `0x2014`, `0x200F`, versions `0xE415`, `0xD415` | SDP attribute |
| Accessory identity blob | Vendor `0x05AC`, shared `SerialNumber`, `CFG# B768/MP/2430RYUK/*/*`, `ProtectedAccess`, `ProtUpdate`, `PrimaryVendorUsages 0xFF0C/0x0D`, `H2HTransformation`, `LocationID` | SDP attribute `0xA001` |

| Descriptor | Size and maximum report | Fields |
|---|---|---|
| `devmotion6` | 96-byte descriptor, maximum report 191 B | Report 1 input has a 64-bit field on page `0xFF15`, usage 4, plus a 1,456-bit vendor field `0xFF0C/0x0D` |
| `devmotion6` | Same descriptor | Report 2 input uses `0xFF0C/0x0E` |
| `devmotion6` | Same descriptor | Feature reports use Sensors page `0x20`, usages `0x030E`, `0x031B`, `0x031A` |
| `devmotion6` | Same descriptor | Report `0xFF` contains a 224-byte vendor feature blob |
| `AVClient` | 67-byte descriptor, maximum report 70 B | Report 1 input is 552 bits. Reports 2, 3 and 4 are 8, 16 and 8 bits |
| `AVClient` | Same descriptor | Feature `0x030E` is 32 bits on reports 1 and 2 |

The 191-byte maximum and 224-byte vendor feature size are both recorded in the descriptor analysis. The source does not resolve their relationship.

The 377 build contains `devmotion6`, while the compared SL6800 build does not. Both have the AAP server, SDP, XAPL, Siri and the proximity advert. H3Pro contains the `devmotion6` AccessoryService plist, HID descriptor and the 2007 Apple copyright string.

[sdp_hid.py](../../tools/sdp_hid.py) is the decoder. The detailed static report is [aap_anc_body.html](../../data/reports/aap_anc_body.html).

## Continuity adverts

The H3Pro template is at CPU `0xC4BF58`, flash `0x4BF58`. `FUN_00cab92c` fills battery nibbles, the lid counter and status at runtime.

```text
1E FF 4C00 07 19 01 0E20 75 00 00 31 00 10 00...00
```

| Field | Value or role |
|---|---|
| AD length | `0x1E`, 30 |
| AD type | `0xFF`, manufacturer-specific data |
| Company ID | `0x004C`, Apple |
| Continuity type | `0x07`, proximity pairing |
| Payload length | `0x19`, 25 |
| Prefix | `0x01` |
| Model bytes | `0E 20`, described as `0x0E20`, AirPods Pro generation 1 |
| Status | Runtime status byte |
| Battery | Left/right nibbles and case battery/charging fields |
| Lid | Lid-open counter |
| Color | Color field |
| Final 16-byte area | Zero in the template, likely AES ciphertext at runtime |

The same template appears at FIRM-relative `0x591E0` in both compared h2sturbo builds. The model bytes select iOS pop-up artwork and name. The string table has `AirPods`, `AirPods Pro` and `AirPods Pro2`, and SDP product `0x2014` identifies Pro 2, while the advert still selects Pro generation 1.

Changing that selection is a two-byte data patch. Changes to post-pairing advert content need the AES path and the device's `air_adv_key`. The exact relationship between that key and the final 16-byte area is likely rather than verified.

## Software AES

FIRM contains a software AES implementation used by the Continuity advertising layer. OTAP has no software AES, and the `.up` image has no signature or encryption.

| Address | Function or data | Role |
|---|---|---|
| `0xC4BFC6` | AES S-box | Byte-verified |
| `0xC4C0E7` | Second AES table | Table used by the AES implementation |
| `0xCA9C84` | `FUN_00ca9c84` | AES caller in the air message path |
| `0xCA9F08` | `FUN_00ca9f08` | AES-path entry called by AAP opcode `0x31` |
| `0xCA9F4C` | `FUN_00ca9f4c` | AES caller in the air message path |
| `0xCAB8D8` | `FUN_00cab8d8` | AES caller in the air message path |
| `0xCAC106` | `FUN_00cac106` | AddRoundKey-style XOR loop |
| `0xCAC12E` | `FUN_00cac12e` | `xtime`, GF(2^8) multiply by 2 with `0x1B` reduction |
| `0xCAC140` | `FUN_00cac140` | SubBytes/mix step |
| `0xCAC1B8` | `FUN_00cac1b8` | 336-byte key schedule |

`FUN_00ca9c84`, `FUN_00ca9f4c` and `FUN_00cab8d8` build 16-, 32- and 54-byte messages, consult battery level and communicate with module 4. Post-pairing Continuity encryption likely uses the 16-byte PSMP `air_adv_key`.

The constant scan identifies no TEA, XTEA, SHA, MD5 or RC4 constants. The table at `0xC451F4` is standard reflected CRC32 for the [settings store](settings-store.md), not evidence of image signing. A claim that FIRM has no AES conflicts with the verified S-box and these callers.

## Heart-rate HID

H3Pro exposes `com.apple.hid.heartrate-access`, with `HeartRate`, `HeartRateService` and `air heartrate tx timer` strings. `sensor-hr` supplies data from the VC30Fx optical sensor. The associated calibration keys include `vc30fx_oscclk_freq` and `vc30fx_sc`.

This heart-rate-over-AAP stack is exclusive to H3Pro within the catalog collection examined. It does not establish exclusivity outside that collection.

## Head tracking

The sensor is an ST LSM6DSV16BX at I2C address `0x6A`. The probe expects `WHO_AM_I = 0x71`. The `6dsox` string is a driver name.

| Stage | Function or data | Behavior |
|---|---|---|
| IMU setup | `FUN_00c589bc`, table `0xC34450`, `FUN_00c58bd4`, `FUN_00c5896c` | Accel and gyro at 240 Hz, `CTRL1 = 0x27`, `CTRL2 = 0x07`, ±2 g and 500 dps |
| FIFO setup | Same setup path | Continuous mode, both streams batched at 240 Hz, watermark two samples, interrupts on INT1 |
| FIFO task | `FUN_00c59298`, `task motion` | Wake on interrupt |
| FIFO read | `FUN_00c58a5c` | Pull up to ten entries, each with one tag read and one six-byte I2C read, then queue for `taskB motion` |
| Per-entry processing | `FUN_00c68924` | Process each entry but step orientation every fourth entry, about 60 Hz pose updates |
| Low-pass stages | `FUN_00c6739c` | Per-axis 100 Hz and 10 Hz filters |
| Motion classifier | `FUN_00c68600` | Pick the blend factor from motion level |
| Exponential smoother | `FUN_00c68284` | Base factor 0.1 |
| Filter plugin slot | `0x82DB5C` | Empty, no vendor fusion library linked |
| Filter output | `0x833D1C` | Three Euler angles as integer degrees |
| Transmit timer | `FUN_00cab53c` | `air motion tx timer`, 40 ms period `0x28` |
| Transmit callback | `FUN_00caaab0` | Convert angles to quaternion, derive angular velocity from the previous tick, timestamp with BT clock and send `devmotion6` HID |
| Slave relay | Peer opcode `0x4B` | Send angles to master every 200 ms |

The orientation filter is implemented in FIRM. The phone receives 25 reports per second derived from one-degree-quantized angles, a 10 Hz low-pass stage and a 0.1 smoother. Sampling, decimation, smoothing and transmit constants are literals. [Audio and DSP](audio-and-dsp.md#verified-patch-offsets) lists the verified patch locations.

The layer also uses `air fit timer`, `air motion timer`, `air resp timer` and BLE advert open/close timers. `H2HTransformation` describes the head-to-head transform in the accessory data.

## HFP and compatibility limits

| String | Meaning |
|---|---|
| `AT+XAPL=0042-0887-0100,2` | Feature bit 1 only, battery reporting |
| `+APLSIRI:1`, `AT+APLSIRI`, `AT+BVRA` | Siri and voice-assistant handling |
| `AT+IPHONEACCEV=1,1,8` | Apple accessory event string |
| `AT+BAC=1,2` | CVSD and mSBC |
| `AT+BRSF=157`, `AT+BRSF=159` | HFP feature strings |

The XAPL feature value has no case-battery or other feature bits set. The compared h2sturbo build has no string/descriptor evidence for conversation awareness, adaptive audio or loud-sound reduction. H3Pro has no `spatial`, `conversation` or `adaptive` strings in the cited scan, despite its motion pipeline and an adaptive ANC mode value.

The h2sturbo analysis has no identified Control Center listen-mode handler. H3Pro opcode `0x4B` is a likely mapping, with semantics still unverified. See [AirPods emulation](../explanation/airpods-emulation.md) for the product-level behavior.
