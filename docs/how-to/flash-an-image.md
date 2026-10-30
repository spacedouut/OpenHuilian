# Flash an image

`hl ota` writes a `.up` to both buds over Bluetooth. It works with stock images and with images
built by `tone_tool.py` or `cfw.py`.

**Before you start:**

* Only flash images built for the H3Pro. Never send an SL6801 image from `firmware/starfun-catalog/`.
  The buds don't check the chip, and there's no tested way back from a wrong image.
* Run `python3 tools/tone_tool.py verify <image>` and make sure it says `ALL CRCs VALID`.
* Charge the buds. The firmware refuses to enter the updater on a low battery.
* Keep a stock image around. `firmware/h3promax3/h3promax3_2607061716_live.up` is the stock 2607061716
  build.

## Flash

```bash
python3 tools/hl --port AA:BB:CC:DD:EE:FF ota custom.up
```

What happens:

1. **Enter (`80`).** Both buds restart into the updater and the connection drops. The tool
   reconnects to whichever bud answers first.
2. **Prepare and declare (`81`, `82`).** The tool sends the image's length and CRC, and the bud
   erases the area it will write. The tool gives `81` up to 30 seconds to answer.
3. **Write (`83`).** About 4 KB/s, so 3 to 4 minutes per bud. The partition index goes last.
4. **Check (`84`).** The bud checks the CRC of everything it received. On a failure it puts the old
   index back and the tool stops.
5. **Leave (`04`).** The bud clears its "stay in the updater" flag and restarts into the new
   firmware.
6. The tool reconnects and flashes the second bud the same way.

`--side one` stops after the first bud. Your settings, pairing and serials aren't touched, because
nothing is ever written to PSMP.

## If the buds don't come back

* After the last bud they may not reconnect on their own. Put both in the case, close the lid for
  about 10 seconds, then take them out.
* If they pair but show up as a generic Bluetooth device with no AirPods pop-up and no music, they
  are still in the updater. Follow [get buds out of the updater](unstick-buds.md).
* If `84` reported a failure, flash again. The buds stay in the updater until a flash completes.

The frame-by-frame protocol is in [OTA protocol](../reference/ota-protocol.md).
