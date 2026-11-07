# Settings store

FIRM accesses the PSMP NV store through string keys and fixed-size buffers. The store holds settings, identity fields, pairing state and sensor calibration, with defaults applied when keys are missing or invalid.

## NV API

| Address | Function | Behavior |
|---|---|---|
| `0xC6E768` | `FUN_00c6e768(key, buf, len)` | Read, return a negative value if the key is missing |
| `0xC6E77C` | `FUN_00c6e77c(key, buf, len)` | Write |
| `0xC6ED54` | `FUN_00c6ed54` | Compact the log-structured store |
| `0xC714AC` | CRC32 accumulator | PSMP record check |
| `0xC451F4` | CRC32 table | Standard reflected CRC32 table |

The [PSMP reference](../reference/psmp.md) describes records and their CRC32. In the live layout, PSMP starts at flash `0xFC000` and occupies `0x4000` bytes. OTAP preserves its index record during updates.

## Keys and lengths

Lengths are bytes. A dash means the source does not supply a length.

| Key | Length | Meaning or default |
|---|---|---|
| `bt_addr`, `bt_addr_backup`, `ble_addr` | 6 each | Bluetooth addresses |
| `addr_backup_flag` | 1 | Whether the backup address is valid |
| `bt_name` | Up to 32 | Rewritten at boot if different from the stack name |
| `bt_vol` | 36 | Per-device volume table |
| `device_id` | 64 | Factory serial field, also read by app auth |
| `authorization_code` | Up to 64 | App authorization data |
| `authorization_code_length` | 4 | Authorization-data length |
| `sn_info`, `sn_l_info`, `sn_r_info` | 12 each | Set, left-bud and right-bud serial fields |
| `product_id`, `date_of_manufacture` | 4 each | Product and production metadata |
| `product_mode` | 15 | Repaired to `H3Pro Max3` at boot if different |
| `paired_flag`, `bootup_flag`, `startup_flag`, `ear_type` | 1 each | Pairing, startup and side state |
| `link_info` | 118 | Last phone link record |
| `link_phone_type` | 5 | Phone-link type record |
| `anc_mode_sel` | 3 | ANC mode, phone-selected mode and extra byte |
| `anc_mode_phone_sel` | 1 | Phone-selected ANC mode |
| `eq_preset_cur_num` | 1 | Current EQ preset |
| `eq_ud_gain` | 56 | User EQ gains |
| `ear_detection_en` | 1 | Defaults to 1 |
| `key_long_left_setting`, `key_long_right_setting` | 1 each | Range 1 to 3, defaults left 2 and right 1 |
| `key_tap2_left_setting`, `key_tap2_right_setting` | 1 each | Range 2 to 5, default 4 |
| `kws_en` | 1 | Keyword-spotting enable |
| `motion_type` | - | Motion configuration |
| `freq_drift` | 2 | Radio/crystal calibration |
| `rfparam` | - | Radio parameters |
| `vc30fx_oscclk_freq` | 16 | Sensor calibration |
| `vc30fx_sc` | - | Sensor calibration |
| `bat_level` | 1 | Battery state |
| `vbus_print` | 1 | VBUS debug output |
| `air_en`, `air_reset`, `air_clean` | - | AirPods-emulation state |
| `air_pair` | 17 | AirPods pairing state |
| `air_link` | 16 | AirPods link state |
| `air_adv_key` | 16 | Key likely used for Continuity advert AES |
| `air_phone_addr` | - | AirPods-layer phone address |
| `air_callctrl_setting`, `air_volumectrl_setting` | - | AirPods call and volume controls |
| `air_audio_setting` | 3 | AirPods audio settings |

The [command tables](command-channel.md) show which keys are exposed through `C0`. Module 4 also provides internal get/set services for the AirPods keys and serial fields.

## Setting semantics

| ANC value | Mode | Prompt |
|---|---|---|
| 0 | Off | `close.mp3` |
| 1 | ANC | `noise.mp3` |
| 2 | Transparency | `pass_those.mp3` |
| 5 | Adaptive | `adpt.mp3` |

`FUN_00c51418` at `0xC51418` maps the mode to its prompt. `C0 69` accepts an index into `{0, 1, 2, 5}` and posts `0xD0000027`. The three bytes persisted as `anc_mode_sel` correspond to live state at `0x834307`, `0x834305` and `0x834306`, in that order.

The adaptive mode value does not establish support for adaptive transparency tuning. The H3Pro catalog comparison lacks the `transparency_adaptive_enable` key found in some other builds.

Gesture setters clamp long-press values to 1 through 3 and double-tap values to 2 through 5. The app's UI strings assign actions to those numbers. No additional per-number meaning is established here.

Game mode passes 0 or 2 to the audio path in event `0xF2000018`. Its `C0 5E` read returns 1 when enabled. The mode at `DAT_0082d3a0`, read by `52` and written by `62`, posts EQ event `0xF3000002`.

Ear detection defaults on and gates the in-ear events from `plxc_proximity_task`. `vbus_print` is writable through `+test=vbusp:<0|1>`, mirrors to the peer and is carried in event `0xC1000004`.

The single-byte controls have `C0` read/write pairs that a companion app can use without a firmware patch. EQ and several identity or link records use larger blocks. [Audio and DSP](audio-and-dsp.md) covers EQ semantics, and [the tone reference](../reference/tone.md) covers prompt data.

## Persistence and peer state

Settings writes are mirrored through `FUN_00c6cdf0`. The [peer opcode table](firm-runtime.md#peer-sync) gives the complete known map.

Before OTA entry, FIRM flushes `link_info`, `link_phone_type` and `bt_name`, then rechecks `product_mode`. Factory reset involves `FUN_00c6ae2c`, `FUN_00c4f014` and `FUN_00c6aac0`.

The vendor flasher can merge device PSM with image PSM, set `restore_factory` and edit keys including `bt_name`, `bt_addr`, `ear_type`, `paired_flag`, `sn_info`, `freq_drift` and `rfparam`. The committed H3Pro `.up` declares PSMP in its index but excludes its contents. See [images and variants](images-and-variants.md#h3pro-container).
