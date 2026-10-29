# C0 command census (H3Pro / 377H3)

Sources: FIRM C0 dispatcher `FUN_00ca32bc` (case list extracted to
`c0_cases.json`), the StarFun app's `CMDConfig.java` (2.0.7.016), and the
hardware-verified commands in `tools/huilian/cli.py`.

- 108 command IDs have a handler case in the FIRM dispatcher.
- 65 are named by the app; the rest are app-unnamed and only reachable via
  `hl cmd` / the panel's raw console (candidates for live probing).
- Read/write pairs are mostly `read cmd` and `read cmd + 0x10`.
- Discrepancies to verify on hardware: `hl` calls 0x52 `eq_mode` and 0x50
  `air_en`, but the app names them `voice_wake` and `dialog_op`.

| cmd | in FIRM dispatcher | name (app / hl) |
|---|---|---|
| 0x03 | no | chip_model / product |
| 0x04 | no | product_model / model |
| 0x05 | no | sw_version / version |
| 0x06 | no | bt_address / bt_addr |
| 0x07 | no | device_id / device_id |
| 0x08 | no | product_type |
| 0x09 | no | power_status / battery |
| 0x0a | no | bt_status / in_ear |
| 0x0b | no | bt_check |
| 0x0c | no | bt_anc |
| 0x0d | no | bt_space |
| 0x0e | no | low_delay |
| 0x0f | no | game_space |
| 0x10 | yes | side |
| 0x11 | yes | work_status |
| 0x12 | yes | lr_version / link |
| 0x13 | yes | support_ota |
| 0x14 | no | product / product_id |
| 0x15 | no | product_date / dom |
| 0x16 | no | hear_help |
| 0x19 | yes | ? |
| 0x1d | yes | ? |
| 0x1e | yes | ? |
| 0x1f | yes | ? |
| 0x20 | yes | ? |
| 0x22 | yes | ? |
| 0x29 | yes | ? |
| 0x2a | yes | ? |
| 0x2b | yes | ? |
| 0x2d | yes | ? |
| 0x2e | yes | ? |
| 0x2f | yes | ? |
| 0x30 | yes | ? |
| 0x31 | yes | ? |
| 0x32 | yes | ? |
| 0x33 | yes | ? |
| 0x34 | yes | ? |
| 0x35 | yes | ? |
| 0x36 | yes | ? |
| 0x37 | yes | ? |
| 0x38 | yes | ? |
| 0x39 | yes | ? |
| 0x3a | yes | ? |
| 0x3d | yes | ? |
| 0x3e | yes | ? |
| 0x3f | yes | ? |
| 0x40 | yes | ? |
| 0x41 | yes | ? |
| 0x42 | yes | ? |
| 0x43 | yes | ? |
| 0x44 | yes | ? |
| 0x45 | yes | ? |
| 0x46 | yes | ? |
| 0x47 | yes | ? |
| 0x48 | yes | ? |
| 0x49 | yes | ? |
| 0x4a | yes | ? |
| 0x4b | yes | ? |
| 0x4c | yes | ? |
| 0x4d | yes | ? |
| 0x4e | yes | ? |
| 0x4f | yes | ? |
| 0x50 | yes | dialog_op / air_en(?) |
| 0x51 | yes | sn_code / serial |
| 0x52 | yes | voice_wake / eq_mode(?) |
| 0x53 | yes | bt_addr2 |
| 0x54 | yes | bt_name / bt_name |
| 0x55 | yes | check_in_ear / ear_detect |
| 0x56 | yes | auto_type |
| 0x57 | yes | game_model |
| 0x58 | yes | audio_space |
| 0x59 | yes | noise_control(anc_mode) / anc_mode |
| 0x5a | yes | long_press_left / long_press_left |
| 0x5b | yes | long_press_right / long_press_right |
| 0x5c | yes | double_click_left / double_tap_left |
| 0x5d | yes | double_click_right / double_tap_right |
| 0x5e | yes | game_space_mode / game_mode |
| 0x60 | yes | dialog_op_w |
| 0x61 | yes | ? |
| 0x62 | yes | voice_wake_w |
| 0x64 | no | bt_name_w |
| 0x65 | yes | auto_check_w |
| 0x66 | yes | audio_type_w |
| 0x67 | yes | game_check_w |
| 0x68 | yes | space_audio_w |
| 0x69 | yes | noise_control_w(anc) |
| 0x6a | yes | long_press_left_w |
| 0x6b | yes | long_press_right_w |
| 0x6c | yes | double_click_left_w |
| 0x6d | yes | double_click_right_w |
| 0x6e | yes | game_space_w |
| 0x6f | yes | ? |
| 0x70 | yes | serial_l |
| 0x71 | yes | serial_r |
| 0x72 | yes | read? |
| 0x73 | yes | ? |
| 0x74 | yes | ? |
| 0x75 | yes | read? |
| 0x76 | yes | read? |
| 0x77 | yes | read? |
| 0x78 | yes | ? |
| 0x79 | yes | ? |
| 0x7a | yes | ? |
| 0x7b | yes | ? |
| 0x7c | yes | ? |
| 0x7d | yes | ? |
| 0x7e | yes | ? |
| 0x7f | yes | ? |
| 0x80 | yes | ota_prepare |
| 0x81 | yes | ota |
| 0x82 | yes | ota |
| 0x83 | yes | flash_read / flash_read |
| 0x84 | yes | ota_end |
| 0x85 | yes | custom_volume_w |
| 0x86 | yes | talk_sensitive_w |
| 0x87 | yes | low_high_vol_w |
| 0x8a | yes | ? |
| 0x8b | yes | ? |
| 0x8c | yes | ? |
| 0x8d | yes | ? |
| 0x8e | yes | ? |
| 0x8f | yes | ? |
| 0x90 | yes | ? |
| 0x91 | yes | ? |
| 0x92 | yes | ? |
| 0x93 | no | ? |
| 0x94 | no | ? |
| 0xa0 | no | ? |
| 0xa3 | no | ? |
| 0xa4 | no | ? |

Machine-readable: `c0-census.json` next to this file.
