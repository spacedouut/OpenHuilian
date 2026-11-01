# ROM read patch

The [mask ROM](mask-rom.md) is memory-mapped, so code running on the chip can copy it like
any other bytes. [`patches/2607061716/rom-read.json`](../../patches/2607061716/rom-read.json) teaches the existing
[C0 `0x83` flash read](command-channel.md#flash-reads) to do that. Apply it like any other patch
([apply a patch](../how-to/apply-a-patch.md)); it has no knobs and has not been flashed to a bud yet.

## How it works

Stock `0x83` replies `C0 83 <addr4><len4><data>` with `data` read from
SPI flash via `FUN_0080576c`. The patch reroutes that one call in
`FUN_00c69b3c` (XIP `0xc69d26`) through a 30-byte stub in dead space
(XIP `0xC30032`, FIRM partition offset `0x2c032`):

- addr bit 31 clear: `b.w FUN_0080576c`, stock behavior. The branch is a
  direct `b.w` rather than a loaded literal and `bx`, which avoids both a
  literal-alignment and a Thumb-bit mistake on the path every normal
  `hl read` takes.
- addr bit 31 set: `memcpy` `len` bytes from `addr & 0x7fffffff` into the
  reply buffer. Any mapped address works, ROM, RAM, peripheral registers.

`hl read` needs no changes. The address goes through verbatim and the
reply echoes it:

```
python3 tools/hl --port <mac> read 0x80000000 0x200 rom-head.bin
python3 tools/hl --port <mac> read 0x80008000 0x10000 rom.bin
```

ROM call sites seen so far sit around `0x8000-0x12000`
(`0x8ca4` scheduler, `0xb4f5` SVC, `0xb5a9` SysTick, `0x11044` malloc), so
`0x0`–`0x20000` is the first range to try. Reading an unmapped or
peripheral address can fault the bud. Worst case is a reboot, but probe
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
   `FUN_0080576c` at `0x0080576c`, assert execution reaches `0x0080576c`
   and that the stub itself copied nothing. Don't assert the destination
   is untouched: once `FUN_0080576c` runs it writes its own output there.
   What it writes is only approximate under stubbed ROM helpers.
5. Stretch: feed a full fake `0x83` C0 frame into `FUN_00c69b3c`'s
   caller and check the reply bytes.

Both paths are covered by [`patches/2607061716/rom-read-selftest.py`](../../patches/2607061716/rom-read-selftest.py),
which runs the stub in Unicorn against a fake ROM and a `bx lr` stand-in
for the flash reader:

```
pip install unicorn
python3 patches/2607061716/rom-read-selftest.py
```

A pass there only means the stub is self-consistent. It says nothing about
whether a real bud survives a read of an unmapped or peripheral address,
and it does not exercise the real `0x83` handler or the reroute site.

## What this is for

Pulling the real mask ROM (`0x0-0x20000`) replaces the `bx lr` stubs in the
Unicorn rehost [`tools/emu/h3emu.py`](../../tools/emu/h3emu.py) with the actual RTOS kernel, SVC/PendSV handlers and
library calls. Also handy: dumping live RAM state or peripheral
registers over the same path.
