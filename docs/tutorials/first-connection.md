# Tutorial: talk to your buds and back up their firmware

By the end of this page you will have read your buds' model and battery, changed a setting, and
saved a full copy of their flash. Nothing on this page writes firmware, so it's safe to follow on
your only pair.

You need:

* An H3Pro Max3 pair (it says `H3Pro Max3` under "More" in the StarFun app)
* A Linux computer with Bluetooth and Python 3 (Windows and macOS work too, see
  [Connect over a serial port](../how-to/change-settings.md#other-operating-systems))
* This repo checked out

## 1. Pair the buds with the computer

Turn off Bluetooth on your phone. The buds only accept one control connection at a time, and the
phone will grab it if it can.

Take the buds out of the case and pair them from a terminal:

```bash
bluetoothctl
scan on            # wait until the buds show up
pair AA:BB:CC:DD:EE:FF
trust AA:BB:CC:DD:EE:FF
quit
```

Use the address `bluetoothctl` printed in place of `AA:BB:CC:DD:EE:FF` in every command below.

## 2. Ask the buds who they are

```bash
python3 tools/hl --port AA:BB:CC:DD:EE:FF info
```

You should see the model (`H3Pro Max3`), the firmware version (`2607061716` on the build this
repo knows), the battery of each bud and the case, which bud answered, and whether both buds are
linked.

If it hangs or times out, check that the phone's Bluetooth is really off, then try again.

## 3. Change a setting

Read the noise-control mode, switch to transparency, then read it back:

```bash
python3 tools/hl --port AA:BB:CC:DD:EE:FF get anc_mode
python3 tools/hl --port AA:BB:CC:DD:EE:FF set anc_mode 2
python3 tools/hl --port AA:BB:CC:DD:EE:FF get anc_mode
```

You should hear the transparency prompt in your ears. `0` is off, `1` is noise cancelling, `2` is
transparency and `5` is adaptive. The buds copy the change to each other on their own. The full
list of settings is in [Change settings](../how-to/change-settings.md).

## 4. Back up the firmware

Read the whole 1 MiB flash into a file. This takes a while, so leave the buds out of the case and
near the computer.

```bash
python3 tools/hl --port AA:BB:CC:DD:EE:FF read 0x0 0x100000 flash.bin
```

Turn the raw dump into a `.up` image and check it:

```bash
python3 tools/build_up.py flash.bin my-buds.up
python3 tools/tone_tool.py verify my-buds.up
```

`verify` should end with `ALL CRCs VALID`. Keep `flash.bin` somewhere private. It contains data
that is unique to your pair (Bluetooth addresses, serials, pairing keys). `my-buds.up` leaves
that part out.

## What you did

You talked to the buds without the StarFun app, changed a setting, and made a backup of the
firmware you can compare against later. Next, try
[your first custom image](first-custom-image.md).
