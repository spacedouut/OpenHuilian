# Memory map and boot

The H3Pro Max3 uses an ARM Cortex-M CPU with ARMv7-M Thumb-2 code, SRAM, mask ROM and memory-mapped flash. The bootloader chooses FIRM or OTAP from a flash flag and copies the selected program's startup block into RAM.

## CPU and address spaces

Cortex-M vector tables identify the architecture. The fault handler uses `mrs msp` and `mrs psp` and accesses the System Control Block at `0xE000ED00`.

| Address or range | Contents |
|---|---|
| `0x000000` upward | Mask ROM shared by FIRM, OTAP and BOOT |
| `0x800000` upward | SRAM, at least about 490 KiB from FIRM's stack top at `0x879820` |
| `0x804800` upward | OTAP's RAM-linked program |
| `0x804C40` to `0x805C40` | FIRM hot code and vectors, copied by the bootloader |
| `0x805C40` to `0x82CA2C` | FIRM `.data`, copied by its startup code |
| After `.data` toward `0x879820` | FIRM `.bss` and stack space |
| `0x860000` to `0x861CF0` | Bootloader while it runs |
| `0xC00000` upward | Flash XIP window |
| Flash `0x4000`, CPU `0xC04000` | FIRM partition |

Most FIRM code runs directly from flash. Only its first 4 KiB code block and its data move into RAM. OTAP runs wholly from RAM at `0x804800` and does not use the XIP window while it erases and writes flash.

The kernel is FreeRTOS-style. FIRM `main` at `0x8052A0` creates `task main` through the task-create helper at `0x829850`, then starts the scheduler at `0x829A00`. See [FIRM runtime](firm-runtime.md) and [mask ROM](mask-rom.md).

## Flash layout

The live image is a complete, CRC-valid read of a 1 MiB-class device, `0x100000` bytes. The partition index is at flash `0x3000`, uses 16-byte records and contains six entries. Its version is `0x9B649AD4`, decimal `2607061716`.

| Region | Flash address | Length | Stored CRC16 | Notes |
|---|---|---|---|---|
| HLKJ header, bootloader and config | `0x000000` | Through `0x3000` | Bootloader body `0xA8CB` | Index follows |
| Index | `0x003000` | Index page | Whole OTA CRC includes it | Six partition records |
| FIRM | `0x004000` | `0x0A9C54`, 695,380 B | `0x6BC3` | Runtime firmware |
| SENC | `0x0AE000` | `0x000808`, 2,056 B | `0x77AA` | Same size and CRC as H2S Turbo SENC |
| TONE | `0x0AF000` | `0x014BA7`, 84,903 B | `0x6386` | 18 prompts |
| EQ2P | `0x0C4000` | `0x00104C`, 4,172 B | `0xACF5` | Seven profiles |
| OTAP | `0x0D2000` | `0x028D50`, 167,248 B | `0xC5DD` | RAM updater |
| OTA flag page | `0x0FB000` | One flash page | No partition CRC listed | Computed from OTAP address and length |
| PSMP | `0x0FC000` | `0x004000`, 16,384 B | `0` | Runtime NV store, declared in the image index |

All five stored partition CRCs recompute with CRC16/CCITT-FALSE. The gap after FIRM is filled with `00`. The gap after OTAP is erased `FF`. PSMP occupies the last 16 KiB.

TONE is packed to its full 84,903-byte partition length, with about 1 KiB before EQ2P. About 4.7 KiB separate the end of OTAP from PSMP. There are also about 53 KB of `00` padding between EQ2P and OTAP. The padding can be used by repartitioning FIRM, SENC, TONE and EQ2P within `0x4000` to `0xD2000`. OTAP and PSMP stay pinned.

The earlier flash-space description says there is essentially no free flash. That excludes the claimable EQ2P-to-OTAP padding, so it is incomplete. [Images and variants](images-and-variants.md) describes the reconstructed container and [the updater](updater-otap.md) describes the layout constraints.

## The 0x30-byte partition header

FIRM and OTAP have the same header structure. The values below describe FIRM where a value is shown.

| Partition offset | Field | FIRM value or meaning |
|---|---|---|
| `+0x00` | Header size | `0x30` |
| `+0x04` | Version | Program version |
| `+0x10` | RAM load address | `0x804C40` |
| `+0x14` | Entry point | `0x804C41`, Thumb bit set |
| `+0x18` | Copy length | `0x1000` |
| `+0x1C` | Header CRC16 | CRC over `partition[0x30 : 0x30 + copy length]`, init `0xFFFF` |
| `+0x30` | Vector table | Initial SP, reset and other vectors |
| `+0x470` | Copy source | Header size plus `0x440` |

The header CRC starts at the vector table. It covers different bytes from the block copied from `+0x470`. Any description that assigns the `+0x1C` CRC to that copied block is incorrect. [cfw.py](../../tools/cfw.py) computes the vector-table range, which matches the stored FIRM and OTAP values.

The bootloader reads the header to copy and jump. It does not check the FIRM or OTAP CRC, does not read the `+0x1C` CRC field and has no CRC16 routine or `0x1021` polynomial constant.

## HLKJ boot header

| Flash offset | Field | Value |
|---|---|---|
| `+0x00` | Magic | `HLKJ` |
| `+0x04` | Load address | `0x860000` |
| `+0x0C` | Header size | `0x60` |
| `+0x10` | Body length | `0x1CF0` |
| `+0x14` | CRC16 | `0xA8CB`, verified |
| `+0x20` | Index offset | `0x3000` |
| `+0x60` | Bootloader vectors | SP `0x878DF0`, reset `0x860101` |

See the [update-format reference](../reference/up-format.md) for the outer `CONFIG` wrapper.

## Boot selection

| BOOT function | Role |
|---|---|
| `FUN_00860168`, `0x860168` | Main boot flow |
| `FUN_008605f2`, `0x8605F2` | Download-mode strap check |
| `0x860E70` | Read index, choose OTAP or FIRM, copy and jump |

1. Initialize clocks and basic peripherals.
2. Read two status registers through `FUN_008605f2`. A set strap enters a download/wait loop. This is likely the factory UART or USB path.
3. Read the partition index from flash `0x3000`.
4. Find OTAP and inspect the word at `OTAP.addr + ((OTAP.len >> 12) + 1) * 0x1000`.
5. Choose OTAP if that word is `0x000055AA`. Otherwise choose FIRM.
6. Read the selected partition's 0x30-byte header, copy its block into RAM and jump to its entry.

No signature, chip-name, version or timestamp check appears in this boot path. The download loop's protocol remains unverified. See [UART boot ROM](uart-boot-rom.md).

## The 0x55AA flag

The formula above resolves to flash `0xFB000` in this image. FIRM and BOOT both calculate it from the OTAP record rather than hard-coding that address.

| Program | Function | Action |
|---|---|---|
| FIRM | `FUN_00c6ad1c`, `0xC6AD1C` | Write `AA 55 00 00` to the flag page |
| FIRM | `FUN_00c4fbc0`, `0xC4FBC0` | Handle `0xF600000F` with payload byte 1, set the flag and arm a 5 s `otaStateTimer` for reboot |
| BOOT | `0x860E70` | Read the flag to select the program |
| OTAP | `FUN_0080fe80`, `0x80FE80` | Clear the flag with a zero word |
| OTAP | `FUN_00819fd4`, `0x819FD4` | Determine whether exit needs linked-master peer handling |

OTAP clears the flag on command `04` after `84` finalize. A linked master first relays exit to its peer with opcode `0x0E` and arms a 2 s `otaStateTimer`, then clears and reboots. Finalize alone leaves the flag set.

A set flag survives ordinary power cycles and keeps both buds in the updater. This supports retries when FIRM is partly written. Retry after a real CRC failure is still unverified. Whether the flag survives a larger layout whose erase range reaches its page is also open.

## Flash-class configuration

Across 24 catalog images plus the OpenPod dump, the first `0x3000` bytes contain byte-identical bootloader code. Exactly three configuration bytes distinguish the 1 MB and 2 MB classes.

| Flash offset | 1 MB class, H3Pro, fit30, a10, h2slim | 2 MB class, h2sturbo, h2sultra, h2spro |
|---|---|---|
| `0x1D` | `00` | `04` |
| `0x5C` | `8C` | `7C` |
| `0x5D` | `0F` | `40` |

Fit30 and H3Pro use the same bootloader bytes. Flash class is configuration data. These three bytes need to remain consistent with the target flash class when comparing or constructing images.
