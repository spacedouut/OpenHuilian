# Get buds out of the updater

Buds stay in the updater (OTAP) if a flash was interrupted, or if a tool stopped after the CRC
check without sending the final `04`. They still pair, but they show up as a generic Bluetooth
device, play no audio and give no AirPods pop-up. Power cycling doesn't help, because a flag in
flash tells them to boot into the updater.

## Fix it

```bash
python3 tools/hl --port AA:BB:CC:DD:EE:FF leave-ota
```

It checks whether the bud that answers is in the updater, sends `04` only then, and checks again
after the restart. If one bud is already back in its normal firmware and the other is still in
the updater, it tells you to power one off. Do that by putting the recovered bud in the case and
closing the lid, then run `leave-ota` again.

It's done when `python3 tools/hl --port AA:BB:CC:DD:EE:FF info` shows both buds linked.

## Why it's careful

A bud in the updater that is linked to its partner passes `04` to the partner first. If the
partner is already back in normal firmware, it reads that as "enter the updater" and restarts
into it. So send `04` only when both buds are in the updater together, or when the stuck bud is
alone. `leave-ota` follows that rule, sending `04` by hand with `hl cmd` doesn't.

## Check the flag yourself

```bash
python3 tools/hl --port AA:BB:CC:DD:EE:FF read 0xfb000 4 flag.bin
xxd flag.bin
```

`aa55 0000` means the bud will boot into the updater. `0000 0000` means it will boot normally.

## If a flash failed partway

If `84` reported a CRC failure, the new firmware isn't usable but the buds stay in the updater.
Don't run `leave-ota`, because it would boot the half-written firmware. Flash a good image instead
([flash an image](flash-an-image.md)). Retrying after a real CRC failure hasn't been tested on
hardware yet.
