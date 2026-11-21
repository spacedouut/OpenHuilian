# Chip peripherals

Register behavior of the Huilian 377H3 that code polls or depends on, read from the `2607061716` bootloader, FIRM, OTAP and the mask ROM with Hopper through [REA](../how-to/set-up-rea-and-hopper.md). Everything here is static analysis. Nothing was measured on a bud.

The point of this page is the emulator. A register listed with a polled bit hangs [`h3emu.py`](../../openhuilian/emu/h3emu.py) unless a read returns that bit.

## Timebase

| Address | Behavior |
|---|---|
| `0x40082104` | Low word of a free-running 64-bit counter |
| `0x40082108` | High word. ROM `0xB6D8` rereads until the high word is stable across the low-word read |
| RAM `0x801374` | Counter clock in Hz, set by ROM `0xB5E8` |
| RAM `0x801378` | Ticks per microsecond, rounded up |
| RAM `0x801370` | Ticks per millisecond, rounded up |

This corrects two names in [mask ROM](mask-rom.md). ROM `0xB6D8` returns the 64-bit counter and `0xB6C4` divides it by the ticks-per-millisecond word to give uptime in milliseconds. They are a "read the clock" pair, which is why they appear together, and neither masks interrupts. ROM `0xB764` and `0xB73E` are busy-wait delays that loop on `0xB6D8` until a scaled deadline passes.

The bootloader's download wait calls `0xB764(1000)` in a loop and leaves when `0xB6C4` has advanced by more than 10000. A counter that reads as a constant never ends that loop or any delay.

## Clocks

| Address | Behavior |
|---|---|
| `0x40080060`, `0x64`, `0x68` | Clock enable bits, 32 per word. ROM `0x2564` sets a bit, then polls until it reads back set |
| `0x40080070`, `0x74`, `0x78` | Companion bits, set just before the matching enable bit |
| `0x40080000` | ROM `0x27A0` case 2 sets `0xC0010000`, then polls until bit 28 is set. Looks like PLL lock |
| `0x40080080` to `0x4008010C` | One register per clock source. Bit 0 enables, bit 4 or 20 selects, by clock id |

Clock ids seen: `0x45` for the timebase, `0x48` and `0x49` for the two UARTs.

## PMU register bus

The bootloader reaches an 8-bit register file through `0x40085100` to `0x40085110`.

| Step | Read, BOOT `0x8605A0` | Write, BOOT `0x860564` |
|---|---|---|
| 1 | | `0x40085108` = data |
| 2 | `0x40085104` = `0x40000061 \| reg << 8` | `0x40085104` = `0x40000160`, register 1. Other registers are assumed to follow the read encoding |
| 3 | Set bit 31 of `0x40085104`, poll until it clears | Same |
| 4 | Data is the low byte of `0x4008510C` | Failure if `0x40085110 & 0xF000` is non-zero |

`0x40085100` bit 31 is a self-clearing reset, also polled.

| PMU register | Use |
|---|---|
| `0x00` bit 0 and `0x23` bits 7:6 | Download strap. BOOT `0x8605F2` enters the wait loop only when the field is 3 and the bit is 1 |
| `0x21` bit 1 | Set with interrupts off before the bootloader spins. A power-off or reset request |
| `0x01` bit 6 | Set or cleared during boot, purpose unknown |
| `0x03`, `0x4D` | Read during boot, purpose unknown |

## Boot progress

`0x40000100` receives a stage number: 8 and 9 in BOOT `0x860190`, then `0xA` before the strap check and `0xB` before the partition is chosen. It is write-only in this code and makes a free boot trace.

## UARTs

| Base | Clock id | IRQ | Baud in the bootloader's setup struct |
|---|---|---|---|
| `0x40090000` | `0x48` | 16 | 3000000 |
| `0x40091000` | `0x49` | 17 | 1500000 |

## Flash controller

The ROM keeps driver state at RAM `0x800938`. Its first word is the controller base, which was not resolved. ROM `0x804C` runs one transfer.

| Controller offset | Use |
|---|---|
| `+0x10` | Command word. Bit 31 starts the transfer, bit 26 is set around program and erase |
| `+0x14` | Length minus one |
| `+0x18`, `+0x1C` | Buffer and flash address |
| `+0x0C` | Status. Bit 1 is done, cleared by writing 2 |

With state word 6 clear the ROM polls the done bit. Otherwise it waits for the interrupt handler to set state byte `0x48` to 1. That handler is ROM `0x825D`, on IRQ 25 in the FIRM and OTAP vector tables and registered on IRQ 50 by the ROM itself.

OTAP page program `0x82BBD4` and erase `0x82BC40` call ROM `0x83E0`, then poll ROM `0x8418` until bit 1 of the returned status is set, which matches a NOR write-enable latch. A flash model has to latch write-enable and report it.

## Interrupts

ROM `0x2348` is `irq_register(n, handler)`. It writes the handler to slot `n + 16` of the table at `VTOR`, and forces `VTOR` to `0x800000` first if it holds anything else. The live vector table is therefore in RAM at `0x800000`. The table in the FIRM header only supplies the reset state, and only IRQ 25 has a real handler there.

Handlers below come from a scan of direct calls to `0x2348`, with the arguments read from the preceding instructions. Sites that load the number from a variable are left out.

| IRQ | FIRM handler | OTAP handler | Peripheral |
|---|---|---|---|
| 8, 9, 10, 11 | `0x8275A9`, `0x8275B5`, `0x8275C1`, `0x8275CD` | `0x82BED1`, `0x82BEDD`, `0x82BEE9`, `0x82BEF5` | Unknown, four of a kind |
| 16, 17 | | | UARTs, bootloader only |
| 25 | ROM `0x825D` | ROM `0x825D` | Flash controller |
| 26, 27 | `0x81CDD5`, `0x8231C9` | `0x81EC59`, `0x820F39` | Unknown |
| 31 | `0x828D39` | | Unknown |
| 36 | `0x8280A9` | | Unknown |
| 40 | `0x827D79` | | Unknown |
| 41, 42 | Registered by two ROM drivers | | Unknown |
| 44 | ROM `0x4CE71` | | Unknown |
| 47 | `0x80B4BD` | `0x80C2D5` | Unknown |
| 48 | `0x80AD13` | | Unknown |
| 54, 55 | `0x82761D`, `0x827669` | | Unknown |

## Emulator changes these suggest

1. Return a counter that advances with executed instructions from `0x40082104` and `0x40082108`, and rename `0xB6D8` and `0xB6C4` in `ROM_NAMES`. They are stubbed as critical-section calls today, so every caller sees time standing still.
2. Read back written bits from `0x40080060` to `0x40080078`, and report bit 28 of `0x40080000` as set.
3. Model the PMU bus: clear bit 31 of `0x40085104` and `0x40085100` on write, keep a 256-byte register file, serve `0x4008510C`. Registers `0x00` and `0x23` then choose between normal boot and the download loop.
4. Log writes to `0x40000100` as boot stages and bytes written to the UART data registers as console output.
5. Hook ROM `0x2348` to record each handler, keep the table at `0x800000`, and inject an IRQ by number through it. That makes the flash, UART and unknown handlers callable in tests.
6. Make the flash model latch write-enable and raise the done bit, or IRQ 25, when a transfer completes.

## Open

* The flash controller base and the UART register layout.
* Which peripherals sit behind IRQ 8 to 11, 26, 27, 31, 36, 40 to 44, 47, 48, 54 and 55.
* The counter frequency. It is whatever clock id `0x34` resolves to at run time.
