# Change settings

`hl get` and `hl set` read and write the buds' user settings over Bluetooth. The buds copy every
change to each other, so you only talk to one of them.

```bash
python3 tools/hl --port AA:BB:CC:DD:EE:FF get anc_mode
python3 tools/hl --port AA:BB:CC:DD:EE:FF set anc_mode 2
```

## Settings

| Name | Values |
|---|---|
| `anc_mode` | `0` off, `1` noise cancelling, `2` transparency, `5` adaptive |
| `ear_detect` | `0` / `1` |
| `game_mode` | `0` / `1`, low-latency mode |
| `eq_mode` | one byte, the EQ mode |
| `air_en` | `0` / `1`, AirPods emulation |
| `long_press_left`, `long_press_right` | action ID `1` to `3` |
| `double_tap_left`, `double_tap_right` | action ID `2` to `5` |
| `bt_name` | Bluetooth name, up to 31 characters |

`hl get` with an unknown name lists everything it knows, including read-only values such as
`device_id`, `product_id`, `dom` (date of manufacture), the serials and `bt_addr`. The StarFun app
shows what each gesture action ID does.

## Other operating systems

`--port` takes a Bluetooth address on Linux, or a serial port anywhere. The serial forms need
`pip install pyserial`.

| OS | Setup | `--port` |
|---|---|---|
| Linux | pair and trust with `bluetoothctl`, nothing else | `AA:BB:CC:DD:EE:FF` |
| Linux (serial) | `rfcomm bind /dev/rfcomm0 <address> 3` | `/dev/rfcomm0` |
| Windows | pairing creates an "Outgoing" COM port | `COM6` |
| macOS | a `/dev/cu.*` device appears after pairing | `/dev/cu.H3Pro-SPP` |

Use channel 3. Channel 1 is the buds' hands-free channel and answers with `AT` commands.

## In a browser or a desktop panel

* `tools/webui/index.html` does the same in Chrome or Edge through Web Serial. Serve it with
  `python3 -m http.server 8000 -d tools/webui` and open `http://localhost:8000`. It hasn't been
  run against buds yet.
* `python3 tools/panel/server.py --port AA:BB:CC:DD:EE:FF`, then open `http://127.0.0.1:8765`.
  It shows live status and more settings than `hl`. The extra ones come from the app's source and
  are marked unverified in the panel.
