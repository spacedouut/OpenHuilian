# Debug monitor patch

[`patches/2607061716/debug-monitor.json`](../../patches/2607061716/debug-monitor.json) adds five
`C0` commands to the SPP command channel: read memory, write memory, call a function, and a log
ring that other patches can write to. It is the first patch that adds new code instead of editing
bytes in place. It has been checked in the emulator only and has not been flashed to a bud.

```
python3 tools/cfw.py apply my.up my-mon.up patches/2607061716/debug-monitor.json
python3 tools/hl --port <mac> ota my-mon.up
python3 tools/hl --port <mac> mon info
```

## Commands

Requests are `C0 <cmd> <payload>`. Replies are `C0 <cmd> <len> <status> <data>`, where status is
0 ok, 1 bad request, 2 locked and 3 unknown command. Multi-byte fields are little endian.

| Cmd | Request payload | Reply data | `hl` |
|---|---|---|---|
| `D0` | none | `"HLMN"`, version, handshake flag, state addr, state len, log addr, log size, log head, code addr | `hl mon info` |
| `D1` | addr4, n1 (1 to 200) | addr4, n bytes. n = 1, 2 or 4 at an aligned address is one load of that width, for peripheral registers | `hl mon peek ADDR [LEN] [--out f]` |
| `D2` | addr4, w1, then value4 (w = 1, 2, 4) or bytes (w = 0) | addr4, readback | `hl mon poke ADDR VALUE [--width N]`, `--bytes ADDR HEX` |
| `D3` | addr4, up to four u32 arguments | r0, r1 | `hl mon call ADDR [r0 r1 r2 r3]` |
| `D4` | op1: 0 state, 1 clear, 2 append the rest of the payload | magic, head, size, wraps, log addr | `hl mon log [--clear] [--mark TEXT]` |

`D2` and `D3` answer status 2 until the session has passed the app handshake: FIRM sets the
byte at `0x8343E8` when `C0 02` verifies (`FUN_00c69888(1)`). `hl mon poke` and `hl mon call` run
the handshake first. The handshake is the app's obfuscation, not security, so this only stops
accidents. Anyone who can open the SPP channel and speak the protocol can write memory.

Stock FIRM ignores `C0 D0` to `DF`: neither C0 handler compares against those values, and the
emulator shows stock FIRM sending no reply.

## How it fits

| Piece | Where | Notes |
|---|---|---|
| Code | flash `0xAE000`, XIP `0xCAE000`, 950 bytes | The first page after stock FIRM. The patch's `layout.firm_end` (`0xAF000`) grows the FIRM partition by one page; SENC, TONE and EQ2P move up 4 KiB |
| Hook | `FUN_00c69b3c` entry, XIP `0xC69B3C` | `push.w {r4-r8, lr}` becomes `b.w mon_entry`. Frames `C0 Dx` go to the monitor and return 0. Every other frame replays the push and jumps to `0xC69B40`, so both callers (`FUN_00c4f0cc` SPP/UART demux and the event `0x0E` path at `0xC6E570`) keep stock behavior |
| Replies | `FUN_00c69870(buf, len)` | Same reply post the stock handler uses. It copies the buffer, so the monitor uses a static one |
| State | RAM `0x878800`, 1 KiB reserved | The patch's `layout.ram` makes `cfw.py` lower the heap-size literal at FIRM `+0xAC8` (RAM `0x805298`) from `0x42C00` to `0x423E0`. The heap then ends at `0x878800`. `0x878C00` to `0x879020` stays unused as a guard below the 2 KiB stack |
| Header | `0xCAE000` | `"HLMN"`, version, `mon_entry`, `mon_log`, state address and length, so other cave code can find `mon_log` |

The state is not zeroed at boot, because it sits in RAM that used to be heap. The monitor
initializes it the first time it runs, when the magic word doesn't match.

## Building

The JSON is build output, so applying the patch needs no compiler. To change the monitor, edit
[`tools/cave/monitor.c`](../../tools/cave/monitor.c) and rebuild:

```
uv run --with ziglang==0.13.0 --with pyelftools python3 tools/cave/build.py
```

`build.py` compiles with zig's clang for Cortex-M4 Thumb, links with
[`monitor.ld`](../../tools/cave/monitor.ld) at the cave address, and refuses undefined symbols
and initialized data. Cave code calls FIRM and ROM only through fixed addresses.

## Emulator check

```
uv run --with unicorn==2.1.1 --with capstone==5.0.3 python3 tools/emu/monitor_check.py firmware/h3promax3/h3promax3_2607061716_live.up
```

[`tools/emu/monitor_check.py`](../../tools/emu/monitor_check.py) applies the patch with `cfw.py`,
boots stock and patched FIRM into `task main` and feeds request frames into `FUN_00c69b3c`. It
checks the following:

* The patched boot does the same partition reads, lookups and peripheral writes as stock.
* `C0 05`, `07`, `0A` and `83` answer the same as stock through the hook. `83` returns each
  image's own flash.
* Every monitor command works, and its error paths answer the right status.
* Poke and call are locked until the stock `C0 02` code sets the session flag.
* A `D3` call of the partition lookup finds the moved EQ2P and TONE.
* The log ring wraps correctly.
* `hl mon` itself, driven over an emulated link.

[`tools/emu/repart_check.py`](../../tools/emu/repart_check.py) also passes on a patched image
stacked with `head-tracking.json` and `rom-read.json`.

## Not verified

* Nothing has run on a bud. Repartitioning and the grown FIRM are also untested on hardware.
* Peeking an unmapped address or an unclocked peripheral can fault the bud. A fault reboots it.
* Calling a function with the wrong arguments can do anything that function can do.
* The handler runs in the task that delivers SPP frames. A slow call stalls that task.
* The heap is 2 KiB smaller. How full the heap gets at runtime has not been measured.
* The monitor answers on whichever bud holds the SPP link, normally the master.
