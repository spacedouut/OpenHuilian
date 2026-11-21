# Dump your buds' firmware

Back up before flashing. Reading never writes to the buds. No stock images are distributed.

Pair the buds with the computer and turn off the phone's Bluetooth first
([first connection](../tutorials/first-connection.md)). Create a private output directory
outside the checkout, then:

```bash
./hl --port AA:BB:CC:DD:EE:FF read 0x0 0x100000 ~/stock/flash.bin
python3 -m openhuilian.format.build_up ~/stock/flash.bin ~/stock/my-buds.up
python3 -m openhuilian.format.tone_tool verify ~/stock/my-buds.up
export OPENHUILIAN_STOCK_UP="$HOME/stock/my-buds.up"
```

The example reads a 1 MiB H3Pro Max3. Confirm sizes for other hardware.
`read` takes a start address, length and output file; the default chunk is 100 bytes.
`--chunk N` accepts 1..200. The builder checks every partition CRC and refuses
invalid dumps unless forced. A mismatch usually means a bad read, so read again.
Use `read 0x3000 200 ~/stock/index.bin` to read just the partition index.

## Mask ROM

`C0 83` normally reads only SPI flash. With the experimental `rom-read` patch,
bit 31 selects raw memory: `hl read 0x80000000 0x20000 ~/stock/rom.bin`.
The patch has not been run on buds; unmapped reads can reboot a bud.
See [ROM read](../research/rom-read.md) for probing advice and range limitations.
Set `OPENHUILIAN_MASK_ROM` to your own dump for experiments requiring real ROM code.

## Keep dumps private

Raw flash contains PSMP: Bluetooth addresses, serials, app authorization and Apple pairing keys.
The builder normally stops before PSMP, but inspect outputs before sharing.
See [PSMP](../reference/psmp.md). Keep dumps outside the checkout; dump extensions are ignored.
