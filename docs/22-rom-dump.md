# Dumping mask ROM through C0 (rom-read patch)

The mask ROM is memory-mapped, so code running on the chip can copy it like
any other bytes. `patches/2607061716/rom-read.json` teaches the existing C0
`0x83` read command to do that.

## How it works

Stock `0x83` replies `C0 83 <addr4><len4><data>` with `data` read from SPI
flash via `FUN_0080576c`. The patch reroutes that one call in
`FUN_00c69b3c` (XIP `0xc69d26`) through a 36-byte stub in dead space
(XIP `0xC30032`, FIRM partition offset `0x2c032`):

- addr bit 31 clear: tail-call into `FUN_0080576c` — stock behavior.
- addr bit 31 set: `memcpy` `len` bytes from `addr & 0x7fffffff` into the
  reply buffer. Any mapped address works — ROM, RAM, peripheral registers.

`hl read` needs no changes; the address goes through verbatim and the
reply echoes it:

```
python3 tools/hl --port <mac> read 0x80000000 0x200 rom-head.bin
python3 tools/hl --port <mac> read 0x80008000 0x10000 rom.bin
```

ROM call sites seen so far sit around `0x8000-0x12000`
(`0x8ca4` scheduler, `0xb4f5` SVC, `0xb5a9` SysTick, `0x11044` malloc), so
`0x0`–`0x20000` is the first range to try. Reading an unmapped or
peripheral address can fault the bud; worst case is a reboot, but probe
in small chunks (`--chunk 64`) and stop if replies go quiet.

## Emulator validation spec

The stub is a leaf: `r0=dst`, `r1=addr`, `r2=len`, returns via `bx lr`,
clobbers only `r0`-`r3`.

1. Load a `.up` patched with `rom-read.json` (or patch FIRM in-memory:
   the two ops above are the whole change).
2. Fill the emulated ROM region with a known pattern, e.g. bytes
   `i & 0xff` at `0x0-0x20000`.
3. Call `0xC30032|1` (or `0xC30033` in Thumb) with `r0` = a RAM buffer,
   `r1 = 0x80008000`, `r2 = 0x100`.
   - assert `dst[0:0x100]` equals the pattern at `0x8000`.
   - assert `r3`, `lr` sane and execution returns to the caller.
4. Call again with `r1 = 0x4000` (bit 31 clear) and a stubbed/mocked
   `FUN_0080576c` at `0x0080576c` — assert the stub tail-branches there
   instead of memcpy.
5. Stretch: feed a full fake `0x83` C0 frame into `FUN_00c69b3c`'s
   caller and check the reply bytes.

## What this is for

Pulling the real mask ROM (`0x0-0x20000`) replaces the emulator's
`bx lr` stubs with the actual RTOS kernel, SVC/PendSV handlers and
library calls. Also handy: dumping live RAM state or peripheral
registers over the same path.
