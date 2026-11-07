# firmware/h3promax3/rom/

`mask_rom_0x00000-0x5ffff.bin`: the H3Pro mask ROM, raw from address `0x0`, 393,216 bytes
(`0x60000`). It was read off the owner's buds with the `rom-read` patch
([ROM read](../../../docs/research/rom-read.md)) applied to the image flashed on 2026-10-31, in three
128 KiB reads. The parts were recovered from quasar `~/romread` and archived on the NAS under
`private/projects/openhuilian/romread-recovered/` (`rom.bin`, `rom2.bin`, `rom3.bin`).

| Range | sha256 of the 128 KiB part |
|---|---|
| `0x00000-0x1ffff` | `077c290178e720846ae36a9bb10403f810a06c72af07a2cb664bdbdcbbafec95` |
| `0x20000-0x3ffff` | `8ed1e7ffd471672b7309df6a76278d08be745817df00488f81d909c2ef568622` |
| `0x40000-0x5ffff` | `968a64e64b6c3a0a9aab925c562b018411f664600f57b62849c4e75a326e2224` |

Whole file: CRC32 `8b562124`, sha256 `81f733395d0aa7402541dcc004d65070a998c484d058d6ddf41688e199eec8df`.

Sanity checks:

* The vector table has initial SP `0x00806000` and reset `0x41`. The reset handler at `0x40`
  clears the registers.
* The ROM entry points FIRM calls ([mask ROM](../../../docs/research/mask-rom.md),
  [addresses](../../../docs/research/addresses.md)) disassemble as real Thumb functions:
  `0x8ca4` scheduler start, `0xb4f4` SVC context restore (`ldm r0!, {r4-r11, lr}`), `0xb5a8`,
  `0x11044` malloc, `0xb6c4` and `0xb6d8` critical sections.
* The three parts are all different, so the ROM doesn't alias at 128 KiB. Code runs to about
  `0x5c000`, and `0x5c000-0x5ffff` is all `00`. Nothing above `0x60000` has been read.

The mask ROM is the same on every chip, so it holds no per-device data. It is vendor code,
under the same "look, don't ship" terms as the rest of `firmware/`
([vendor README](../../../vendor/shenju-flashloader/README.md)).
