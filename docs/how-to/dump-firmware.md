# Dump your buds' firmware

Use this to back up a pair before you flash anything, or to get the image for a build this repo
doesn't have yet. Reading never writes to the buds.

## With `hl` (no phone needed)

Pair the buds with the computer and turn off the phone's Bluetooth first
([first connection](../tutorials/first-connection.md)).

```bash
python3 tools/hl --port AA:BB:CC:DD:EE:FF read 0x0 0x100000 flash.bin
python3 tools/build_up.py flash.bin my-buds.up
python3 tools/tone_tool.py verify my-buds.up
```

* `read` takes a start address, a length and an output file. The buds answer with at most 200
  bytes per request, and `--chunk` can only make that smaller.
* `build_up.py` checks every partition CRC and refuses to write the `.up` if one is wrong. A wrong
  CRC almost always means a bad read, so read again.
* To read just the partition index, use `read 0x3000 200 index.bin`.

## Through the StarFun app (Frida)

This older route reuses the app's own connection. You need a rooted Android phone with StarFun
**2.0.7.016** (2.0.7.017 rejects these buds) and Frida **16.5.9** on both sides. Frida 17 drops
the agent and kills the app.

```bash
adb forward tcp:27042 tcp:27042
FRIDA_HOST=127.0.0.1:27042 python3 tools/flashdump.py 0x0 0x100000 flash.bin 200
python3 tools/build_up.py flash.bin my-buds.up
```

It runs at about 1.1 KB/s, so the full 1 MiB takes about 16 minutes. The only command it sends is
the `C0 83` flash read.

## The mask ROM

`C0 83` only reads SPI flash. With the `rom-read` patch flashed, an address with bit 31 set reads
raw memory instead, so `hl read 0x80000000 0x20000 rom.bin` pulls the mask ROM. The patch has not
been run on buds yet, and reading an unmapped address can reboot a bud. Details and probing advice
are in [ROM read](../research/rom-read.md).

## Keep the raw dump private

`flash.bin` contains the PSMP settings partition, which holds your Bluetooth addresses, serials,
the app authorization code and Apple pairing keys. The `.up` that `build_up.py` writes stops before
PSMP, so it's safe to share. Details are in [PSMP](../reference/psmp.md).
