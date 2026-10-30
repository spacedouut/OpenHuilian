# Mask ROM

FIRM, OTAP and BOOT call a mask-ROM library beginning at address zero. FIRM alone references 467 distinct ROM call targets, including the RTOS core, memory helpers, flash services and much of the Bluetooth stack.

## Call-surface scope

The inventory combines a Capstone Thumb-2 direct-BL sweep over all three programs with decompiled `func_0x...` and `thunk_EXT_FUN_...` references. The 467-target count applies to FIRM alone.

The `0x11000` to `0x31000` band is called from Bluetooth stack code. Much of the vendor BT stack lives in ROM, with glue in FIRM. These services are callable by patched FIRM code through the same interfaces.

## Named entries

Counts are the reported call counts from the static sweep. A dash means no count is supplied.

| ROM address | Calls | Name or role |
|---|---|---|
| `0x0AA2` | - | `strlen` |
| `0x0AB2` | - | `strcmp` |
| `0x0B2A` | 235 | `memcpy` |
| `0x0BAA` | 231 | `memset` |
| `0x0C54` | 163 | `memcmp` |
| `0x0C70` | 57 | `malloc` |
| `0x0C74` | 56 | `free` |
| `0x1A90` | 90 | Queue/event post |
| `0x2A7C` | 76 | Timer/queue helper |
| `0x83B4` | - | Flash read, arguments `dst, flash_addr, len` |
| `0x9E3C` | 58 | RTOS helper used by task creation |
| `0xB4F5` | - | SVC vector target, Thumb address |
| `0xB514` | 55 | Flash write wrapper |
| `0xB534` | 60 | Flash read wrapper |
| `0xB5A9` | - | SysTick vector target, Thumb address |
| `0xB6C4` | 218 | Exit critical section |
| `0xB6D8` | 278 | Enter critical section |
| `0xB78C` | 110 | Sleep for N milliseconds |
| `0xC096` | 19 | `printf` family |
| `0xC0DC` | 25 | `printf` family |
| `0x11044` | 80 | Bluetooth host helper |
| `0x110C0` | 52 | Bluetooth host helper |
| `0x48268` | 63 | Flash helper |
| `0x4B29C` | 121 | Bluetooth helper, A2DP/RF glue |
| `0x404132` | 42 | Audio/DSP helper |

`0xB6D8` and `0xB6C4` appear as a pair around shared state. `FUN_0080576c` uses the flash-wrapper surface. FIRM's PendSV target is RAM `0x827591`, separate from the SVC and SysTick ROM targets.

## Reproduction and limits

The full generated target list is named `rom_surface.txt` and is not committed. The [reproduction workflow](README.md#reproduce-it) lists `oh_dump_lib.py` for decompile references and `romscan.py` for direct BL targets.

The table above preserves every named entry in the sources. It does not assign names or behavior to the remaining targets. [UART boot ROM](uart-boot-rom.md) covers the download protocol surface, and [FIRM runtime](firm-runtime.md) covers the task and event APIs that use ROM.
