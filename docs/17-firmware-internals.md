# 17 · Inside the H3Pro firmware: memory map, boot, and how updates get accepted

This page covers the disassembly of the H3Pro Max3 `2607061716` image: where things load, how
the bootloader picks what to run, and what the OTA updater checks before it takes an image.

Method: the partitions from [16](16-live-flash-dump.md) were wrapped into ARM ELFs with
[`tools/h3pro_elf.py`](../tools/h3pro_elf.py), then read with Capstone and Ghidra (through REA).
There are no symbols, so functions are named by address (`FUN_0080e770` and so on). All of it is
static analysis. **Nothing was run on, or written to, the buds.**

Short version: **the H3Pro takes any image whose CRC16 matches the CRC the phone announces.** No
signature, no chip-name check, no version or timestamp check, in either the bootloader or the
updater.

## The CPU

ARM Cortex-M (ARMv7-M, Thumb-2). The giveaways: normal Cortex-M vector tables, and a fault
handler that does `mrs msp` / `mrs psp` and pokes the System Control Block at `0xE000ED00`.


There's a mask ROM at address 0 that all three programs call into. The handful we've identified:

| ROM address | What it does |
|---|---|
| `0x83B4` | flash read (`dst, flash_addr, len`) |
| `0x0C54` | `memcmp` |
| `0x0BAA` | `memset` |
| `0x0B2A` | `memcpy` |

## Memory map

| Range | What's there |
|---|---|
| `0x000000` up | mask ROM |
| `0x800000` up | SRAM. FIRM's stack top is `0x879820`, so at least ~490 KiB |
| `0x804C40`..`0x805C40` | FIRM's hot code + vectors, copied from flash by the bootloader |
| `0x805C40`..`0x82CA2C` | FIRM `.data`, copied by FIRM's own startup; `.bss` runs on to the stack |
| `0x860000`..`0x861CF0` | the bootloader, while it's running |
| `0xC00000` up | flash, memory-mapped (XIP). FIRM partition at flash `0x4000` = `0xC04000` |

FIRM mostly runs straight out of flash at `0xC04000`; only the first 4 KiB and its data get
copied to RAM. OTAP is different: the whole updater is linked to run from RAM at `0x804800` and
never touches the XIP window, which makes sense for a program that's about to erase the flash.

FIRM's main task runs on a FreeRTOS-style kernel (`xTaskCreate`-alike at `0x829850` creates
`"task main"`, scheduler start at `0x829A00`).

## The 0x30-byte partition header

FIRM and OTAP both start with the same little header, which is what the bootloader actually reads:

| Offset | Field |
|---|---|
| `+0x00` | header size (`0x30`) |
| `+0x04` | version |
| `+0x10` | RAM load address (`0x804C40`) |
| `+0x14` | entry point (`0x804C41`, Thumb bit set) |
| `+0x18` | bytes to copy (`0x1000`) |
| `+0x1C` | CRC16 of the copied block |
| `+0x30` | the program's vector table (initial SP, reset, ...) |

The copy source is partition `+0x470` (header size + `0x440`).

The `HLKJ` header at flash 0 does the same job for the bootloader: `+0x04` load address
`0x860000`, `+0x0C` header size `0x60`, `+0x10` length `0x1CF0`, `+0x14` CRC16 (`0xA8CB`, checks
out), `+0x20` index offset `0x3000`. The bootloader's own vectors are at flash `0x60`
(SP `0x878DF0`, reset `0x860101`).

## Boot flow (bootloader, `FUN_00860168`)

1. Basic clock/peripheral init.
2. Check a hardware strap (`FUN_008605f2`, reads two status registers). If it's set, drop into a
   download/wait loop instead of booting. Probably the factory UART/USB path from
   [12](12-shenju-flasher.md).
3. Read the partition index from flash `0x3000`.
4. Find `OTAP`, look at the first page right after it (`OTAP.addr + ((OTAP.len >> 12) + 1) * 0x1000`,
   which is flash `0xFB000` on this image). If the word there is `0x000055AA`, boot **OTAP**,
   otherwise boot **FIRM**.
5. Read that partition's 0x30-byte header, copy the block to RAM, jump to the entry.

What the bootloader **doesn't** do: check any CRC on FIRM or OTAP. The CRC16 routine isn't even in
the bootloader (no `0x1021` anywhere in it). The `+0x1C` header CRC is there but nothing here reads
it.

So that `0x55AA` word is the "reboot into the updater" flag, and both sides of it are in the code:

* **FIRM sets it** in `FUN_00C6AD1C`: look up `OTAP` in the index, then write the 4 bytes
  `AA 55 00 00` to `OTAP.addr + ((OTAP.len >> 12) + 1) * 0x1000`. That's the same address the
  bootloader computes, so neither side hard-codes `0xFB000`. It's called from the FIRM event
  dispatcher (`FUN_00C4FBC0`) on event `0xF600000F` with payload byte 1, which is the app's
  "enter OTA" handshake from [06](06-bt-ota-protocol.md); the handler then arms a 5 s
  `otaStateTimer` and the bud reboots into OTAP.
* **OTAP clears it** in `FUN_0080FE80`, the same routine with a zero word. The OTA state machine
  calls it on the `04` command that follows `84` finalize, then reboots. If `FUN_00819FD4` says
  to stay in the updater, it arms a 2 s `otaStateTimer` instead and leaves the flag alone.
* The bootloader only reads it.

So the flag is one flash page, set by FIRM on request and cleared by the updater when it's done.
If OTAP never gets that far, the flag stays set and the bud comes back up in the updater. That's
the retry path a half-written FIRM depends on.

## How OTAP takes an update (`FUN_0080e770`)

This is the state machine behind the `55 AA 8x` frames from [06](06-bt-ota-protocol.md). The
command byte picks the branch:

**`80` / `81`** just reply "ok".

**`82` declare.** Saves the CRC16 and total length the phone sends (it only uses the low 16 bits of
the 4-byte CRC field). Then it:
* erases flash from `0x4000` up to `0x3000 + total` (4 KiB sectors to `0x10000`, 64 KiB blocks
  after that, 4 KiB for the tail);
* takes a CRC16 of `flash[0 : 0x3000]` (bootloader + config) and keeps it as a guard.

**`83` data.** Writes the payload at whatever absolute address the frame says, in 256-byte pages.
**There's no bounds check on the address.** One special case: a write to `0x3000` (the index) first
backs up the current index in RAM, then erases the index page and writes the new one.

When the byte count reaches the declared total, it:
1. runs CRC16/CCITT-FALSE over `flash[0x3000 : 0x3000 + total]` (index plus every partition) and
   compares it with the declared CRC;
2. **match:** commits the new index, but copies the `OTAP` and `PSMP` records back in from the old
   one (tags `"OTAPPSMP"` at `0x809600`). So an update can't move or resize the updater or the
   settings store, whatever its index says;
3. **mismatch:** puts the old index back and flags failure;
4. re-checks the guard CRC over `flash[0 : 0x3000]` and flags failure if the bootloader area changed.

**`84` finalize** replies with the result byte (0 = good, 1 = failed), then the bud reboots.

That's the complete acceptance test. The `CONFIG` header, its chip name, the build version and
timestamps never reach the device: the app strips the container and only streams flash contents.

## What this means for custom firmware

* **CRC-only acceptance on H3Pro is now confirmed from the code**, which closes the biggest open
  question in [05](05-crc-and-integrity.md) and [15](15-cfw-roadmap.md). Fix up the partition CRCs
  ([05](05-crc-and-integrity.md)), let the app compute the whole-payload CRC, done.
* **The SL6806-style checks don't exist here.** No `CONFIG` magic, no mark string, no "time is not
  same" check. That also means nothing stops an SL6801 image from being accepted, so rule 2 in
  [00](00-start-here.md#safety--ground-rules) matters even more.
* **A failed update doesn't roll back FIRM.** The old index comes back, but the FIRM area was
  already erased and partly rewritten. Recovery depends on the `0x55AA` flag keeping the bud in
  OTAP so you can retry. Very likely, not yet proven.
* **Writes below `0x3000` are possible** (no address check), and the guard CRC only notices after
  the fact. Never send anything that targets the bootloader area.
* OTAP and PSMP are pinned by the updater, so CFW layouts can only rearrange FIRM / SENC / TONE /
  EQ2P inside `0x4000`..`0xD2000`.

## Handy addresses

| Program | Address | What |
|---|---|---|
| BOOT | `0x860168` | main |
| BOOT | `0x8605F2` | download-mode strap check |
| BOOT | `0x860E70` | index read, OTAP/FIRM pick, copy + jump |
| OTAP | `0x80E770` | OTA frame state machine |
| OTAP | `0x80E4C0` | erase for `82` |
| OTAP | `0x80E538` | final CRC over `0x3000..0x3000+total` |
| OTAP | `0x80E5B8` | write index page |
| OTAP | `0x80E622` / `0x80E6B8` | carry OTAP/PSMP records over from the old index |
| OTAP | `0x80E730` | guard CRC over `0..0x3000` |
| OTAP | `0x82BCA4` / `0x82BCC8` | CRC16 byte / buffer |
| OTAP | `0x82BD48` / `0x82BD9C` | flash page write / erase |
| FIRM | `0x8052A0` | `main`, creates `"task main"` |
| FIRM | `0xC6AD1C` | set the `0x55AA` boot-to-OTAP flag |
| FIRM | `0xC4FBC0` | event dispatcher (`0xF600000F` = enter OTA) |
| FIRM | `0x805444` | partition lookup by tag, returns addr + length |
| FIRM | `0xC714AC` | CRC32 accumulator (PSMP record check, [09](09-psmp-nvds.md)) |
| OTAP | `0x80FE80` | clear the `0x55AA` flag |

## Reproduce it

```bash
python3 tools/h3pro_elf.py firmware/h3promax3/h3promax3_2607061716_live.up out/
# then load out/firm.elf, out/otap.elf, out/boot.elf in Ghidra (ARM Cortex, little endian)
```

## Still open

* What the bootloader's download loop speaks (likely the UART protocol in [12](12-shenju-flasher.md)).
* Whether the flag page survives an OTA that rewrites the index: OTAP erases `0x4000` up to
  `0x3000 + total`, which on a full image stops well below the flag page, but a larger layout
  could reach it.
