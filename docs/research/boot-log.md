# Boot milestone log patch

[`patches/2607061716/boot-log.json`](../../patches/2607061716/boot-log.json) makes FIRM write a
line into the [debug monitor](debug-monitor.md)'s log ring before each driver-init call of
`task main`, and a line for every I2C transfer made while it initializes. It only writes RAM. It
has been checked in the emulator only and has not been flashed to a bud.

```
python3 -m openhuilian.patch.cfw apply my.up my-log.up patches/2607061716/debug-monitor.json patches/2607061716/boot-log.json
python3 hl --port <mac> ota my-log.up
python3 hl --port <mac> mon log
```

Apply it together with `debug-monitor.json`. Without the monitor there is no ring: the boot log
looks for the monitor header at `0xCAE000`, finds none and logs nothing.

## Log format

One text line per record. All numbers are hex.

| Line | Meaning |
|---|---|
| `b<id> <ms>` | `task main` (`FUN_00c4de78`) is about to make init call `<id>` |
| `i2c <addr> <w or r> <status> <ms>` | An I2C transfer finished. `<addr>` is the 7-bit address, `<status>` is the bus driver's status byte: `00` is success, anything else is a failure such as a NACK |

`<ms>` is six digits of the ROM uptime clock (`0xB6C4(0xB6D8())`, see
[chip peripherals](chip-peripherals.md#timebase)). I2C lines are written from `b01` until `b11`,
at most 8 per boot, so later traffic from a fitted sensor can't push the boot lines out of the
512-byte ring. The ring is not cleared at boot. After a warm reset, the lines of the earlier boot
are still in front of the new ones if the RAM kept its contents.

This is the log from the emulated boot of the stock image. No I2C slave is modelled, so the
probe of address `0x60` is NACKed all three times:

```
b01 00029e
b02 00029e
b03 00029e
b04 0002bc
b05 0002bc
b06 0002bc
b07 0002bc
b08 0002bc
b09 0002bc
b0a 0002bc
b0b 0002bc
b0c 0002bd
b0d 0002bd
b0e 0002bd
b0f 0002bd
b10 0002bd
i2c 60 w 01 0002bd
i2c 60 r 01 0002bd
i2c 60 w 01 0002bd
b11 00033a
```

## Milestones

The id is the position of the call in `FUN_00c4de78`. The functions are not named yet. The
"seen in the emulator" column is what the hardware model observed between that milestone and
the next one.

| Id | Call site | Callee | Seen in the emulator |
|---|---|---|---|
| `b01` | `0xC4DE7E` | `FUN_00c60554(0)` | |
| `b02` | `0xC4DE82` | `FUN_00c6e7a0` | |
| `b03` | `0xC4DE86` | `FUN_00c53720` | 30 ms pass |
| `b04` | `0xC4DE8A` | `FUN_00c6aa8c` | |
| `b05` | `0xC4DE8E` | `FUN_00c6a360` | |
| `b06` | `0xC4DE92` | `FUN_00c4e654` | |
| `b07` | `0xC4DE96` | `FUN_00c5a280` | |
| `b08` | `0xC4DE9A` | `FUN_00c55880` | |
| `b09` | `0xC4DE9E` | `FUN_00c54220` | Creates the `pmu_isr_bh` task |
| `b0a` | `0xC4DEA2` | `FUN_00c558dc` | |
| `b0b` | `0xC4DEA6` | `FUN_00c53480` | |
| `b0c` | `0xC4DEAA` | `FUN_00c508f4` | |
| `b0d` | `0xC4DEAE` | `FUN_00c52520` | Creates the `watchdog` task |
| `b0e` | `0xC4DEB2` | `FUN_00c4eb1c` | |
| `b0f` | `0xC4DEB6` | `FUN_00c5251c` | |
| `b10` | `0xC4DEBA` | `FUN_00c4eb30` | The I2C probe of `0x60` (write, read, write through `FUN_00c59ef0`), then 125 ms pass |
| `b11` | `0xC4DEC0` | `FUN_00c5a298(arg)` | Last call of the function. The audio and TWS tasks are created after it |

## How it fits

| Piece | Where | Notes |
|---|---|---|
| Code | XIP `0xCAE800`, 577 bytes | Second half of the monitor's cave page. `layout.firm_end` is the monitor's `0xAF000`, so the flash layout is the same as with the monitor alone |
| State | RAM `0x8787F0`, 16 bytes reserved | An armed word and the I2C line count, just below the monitor's block. `cfw.py` lowers the heap by another 16 bytes |
| Milestone hooks | the 17 `bl` instructions in `FUN_00c4de78` | Each `bl X` becomes `bl bl_hook`. `bl_hook` saves `r0`-`r3`, `ip` and `lr`, finds the call in a table by its return address, logs, restores all six and jumps to `X` through a stack slot, so `X` starts with every register as `task main` left it and returns straight to `task main` |
| I2C hooks | `0xCA0682` and `0xCA06F0` | The common exits of the bus write helper `FUN_00ca0624` and read helper `FUN_00ca0694`: `rsbs r0, r5, #0` and `pop.w {r3-r9, pc}` become a `b.w` to a stub that logs `r9` (address) and `r5` (status) and then runs the same two instructions |
| Ring | `mon_log` from the monitor header | Called with interrupts masked, so a line is not interleaved with another writer's |

The patch adds no flash access and no peripheral access apart from the ROM reading its uptime
counter.

## Building

The JSON is build output. To change it, edit
[`openhuilian/patch/cave/bootlog.c`](../../openhuilian/patch/cave/bootlog.c) or the call list in
[`build_bootlog.py`](../../openhuilian/patch/cave/build_bootlog.py) and rebuild:

```
uv run --with ziglang==0.13.0 --with pyelftools python3 -m openhuilian.patch.cave.build_bootlog
```

`build_bootlog.py` generates the call table the C code walks from the same list it writes the
`bl` ops from. Each op's `old` bytes are the stock `bl` to the listed callee, so `cfw.py` refuses
the patch if the list doesn't match the image.

## Emulator check

```
OPENHUILIAN_MASK_ROM=... uv run --with unicorn==2.1.1 python3 -m openhuilian.emu.bootlog_check "$OPENHUILIAN_STOCK_UP"
```

[`openhuilian/emu/bootlog_check.py`](../../openhuilian/emu/bootlog_check.py) applies both patches
into a temporary directory and powers the result on in the [hardware model](hardware-model.md),
from the mask ROM reset vector to the idle task's WFI, next to a stock boot. It then reads the
ring back the way `hl mon log` does, with `C0 D4` and `C0 D1` frames through the real C0 handler,
and prints it. It checks the following:

* The patched image reaches idle like stock (3694 ms against 3693 ms) with the same IRQ enabled.
* The patched boot makes the same 12 flash writes as stock, all inside PSMP, and the same I2C
  bus traffic. PSMP ends with the same bytes as after the stock boot and no other flash byte
  changes.
* The log read back through the monitor is the ring in RAM.
* The log holds `b01` to `b11` once each, in order, with rising timestamps.
* The log holds three I2C lines for address `0x60`, all failed, matching the bus model's write,
  read, write.
* With a device answering at `0x60` in the bus model, the three transfers succeed, the log holds
  three lines with status `00`, and the device is sent and asked for the same bytes as under
  stock.
* `boot-log.json` without the monitor boots to idle and writes no ring.

## Not verified

* Nothing has run on a bud. The times and the NACKs are the model's. A real device at
  `0x60` may answer differently from the model's, which acknowledges everything and returns
  `0x5A`, so the number of transfers on a bud may differ.
* The status byte's values other than 0 are not decoded. The model's NACK gives `01`.
* The two I2C helpers are assumed to be the only path to the bus. A driver that drives the
  controller another way would not be logged.
* The heap is 16 bytes smaller than with the monitor alone.
