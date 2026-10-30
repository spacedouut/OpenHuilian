# OTAP updater

OTAP accepts an update by checking CRC16 over the announced flash payload and preserving two records from the old index. It runs from RAM and has no image signature, encryption, chip-name or version gate.

## State machine

`FUN_0080e770` at `0x80E770` handles exactly `80`, `81`, `82`, `83`, `84` and `04` in the `55 AA` frame family. No additional updater command appears in its switch.

| Command | Action |
|---|---|
| `80` | Reply with success while already in OTAP |
| `81` | Reply with success |
| `82` | Save declared CRC and total length, erase the payload area and save a guard CRC |
| `83` | Write data at the frame's absolute flash address, then validate when the byte count reaches the declared total |
| `84` | Reply with the result byte, `0` for success or `1` for failure |
| `04` | Clear the boot-to-OTAP flag and reboot, with peer exit coordination for a linked master |

The transport sequence is `80` enter, `81` prepare, `82` declare, `83` data, `84` finalize, `04` leave. The documented sender uses 512-byte data chunks and sends the index last. OTAP splits writes into 256-byte flash pages.

The service-image discussion calls `81` “prepare (erase)”. The OTAP audit confirms the detailed state-machine analysis, which places the erase in `82`, while `80` and `81` only acknowledge. This page follows that audited handler behavior.

See the [OTA protocol](../reference/ota-protocol.md) for frame encoding and [command channel](command-channel.md#entering-ota-from-firm) for the `80` behavior before OTAP starts.

## Declare and erase

`82` saves the total length and only the low 16 bits of the four-byte CRC field supplied by the phone.

| Range or size | Use |
|---|---|
| `flash[0x4000 : 0x3000 + total]` | Erase range |
| 4 KiB | Erase sectors up to `0x10000` and for the tail |
| 64 KiB | Erase blocks after `0x10000` |
| `flash[0 : 0x3000]` | Bootloader and config guard CRC |

The guard is CRC16. It detects a change only after writes have happened.

## Data, CRC and index handling

`83` accepts the absolute address in the frame without a bounds check. It can address flash below `0x3000`. The guard CRC does not prevent such writes.

A write to `0x3000` has special handling. OTAP saves the current index in RAM, erases the index page and writes the new index.

When the received byte count reaches the declared total, OTAP performs these steps.

1. Compute CRC16/CCITT-FALSE over `flash[0x3000 : 0x3000 + total]`, including the index and all streamed partition bytes. The polynomial is `0x1021` and the initial value is `0xFFFF`.
2. Compare it with the announced CRC16.
3. On a match, commit the new index but copy the OTAP and PSMP records from the old index. The tag string `OTAPPSMP` is at `0x809600`.
4. On a mismatch, restore the old index and mark failure.
5. Recompute the guard over `flash[0 : 0x3000]` and mark failure if the bootloader/config area changed.

An update cannot move or resize OTAP or PSMP through its replacement index. FIRM, SENC, TONE and EQ2P can be rearranged inside `0x4000` to `0xD2000` for this layout.

## Finalize, leave and failure

`84` reports the result and leaves the bud in OTAP. Command `04` calls `FUN_0080fe80` to clear the flag and reboot.

If `FUN_00819fd4` identifies a linked master, OTAP first relays exit with peer opcode `0x0E` and starts a 2 s `otaStateTimer`. It then clears the flag and reboots. See [the flag lifecycle](memory-map-and-boot.md#the-0x55aa-flag).

A failed CRC restores the old index only. FIRM has already been erased and partly rewritten, so there is no FIRM rollback. Recovery relies on the flag keeping the bud in OTAP for another transfer.

Hardware confirms that omitting `04` leaves the buds in OTAP across power cycles. They continue to answer a limited set of `C0` reads. A retry after a genuine CRC failure is unverified. The standard full-image erase range stops below the flag page, but a larger announced layout could reach it.

## What is checked

| Item | Behavior |
|---|---|
| Whole streamed payload | CRC16 comparison against the phone's declared value |
| Bootloader/config area | Guard CRC before and after the transfer |
| OTAP and PSMP index records | Restored from the old index |
| Image signature | None |
| Image encryption | None |
| OTAP software AES | None |
| `CONFIG` magic and chip name | Never reach this handler |
| Mark string | No SL6806-style check |
| Version or timestamp | No check, including no “time is not same” check |
| Absolute write address | No bounds check |

The app removes the outer `CONFIG` container and streams flash contents. Neither its chip name nor its build metadata reaches the updater. The `.up` integrity mechanism is CRC16 only. FIRM's [software AES](airpods-layer.md#software-aes) serves Continuity adverts and is separate from update acceptance.

The lack of a chip check also permits acceptance of an incompatible SL6801 payload if its CRC matches. Acceptance does not establish hardware compatibility. CRC-only acceptance works on H3Pro hardware with stock and patched images. Patch tooling repairs partition CRCs and the sender computes the whole-payload CRC.

## OTAP-mode C0 commands

OTAP has its own 1,196-byte dispatcher at `FUN_00810914`. The table distinguishes code presence from observed replies. Command names shared with FIRM are described in the [FIRM command tables](command-channel.md).

| Command | Handler present for | Hardware observation or gate |
|---|---|---|
| `01` | App auth step 1 | Requires auth-enabled flag `*PTR_DAT_00810ce0` and channel/type argument `0x40` |
| `02` | App auth step 2 | Requires channel/type `0x40` and its own verification checks |
| `04` | Model | Replies observed |
| `05` | Version, 11 characters | Replies observed |
| `06` | Bluetooth address | Role or peer-state gating can apply |
| `07` | `device_id` | Present, reply not established by the observed subset |
| `09` | Battery, three bytes | Replies observed |
| `10` | Side, `11` or `22` | Present, reply not established by the observed subset |
| `11` | Command shared with FIRM | Present, gated behavior |
| `12` | Link state | Role or peer-state gating can apply |
| `13` | Command shared with FIRM | Present, gated behavior |
| `50`, `51`, `53`, `54` | Read-command group also present in FIRM | Only `51` is in the observed four-command reply subset |
| `60`, `61`, `63`, `64` | Write-command group also present in FIRM | Present, gated behavior |
| `83` | Flash read, maximum 200 bytes | Working read path |

The observed reply subset is `04`, `05`, `09`, `51`, plus `83` flash reads. Handler presence alone does not establish a usable recovery command. [tools/hl](../../tools/hl) supports the working reads and the [recovery guide](../how-to/unstick-buds.md) covers leaving OTAP.

## Function map

| Address | Name or role |
|---|---|
| `0x809600` | `OTAPPSMP` tag string |
| `0x80E4C0` | Erase for `82` |
| `0x80E538` | Final CRC over `0x3000` through `0x3000 + total` |
| `0x80E5B8` | Write index page |
| `0x80E622` | Preserve OTAP/PSMP records |
| `0x80E6B8` | Preserve OTAP/PSMP records |
| `0x80E730` | Guard CRC over `0` through `0x3000` |
| `0x80E770` | `FUN_0080e770`, OTA frame state machine |
| `0x80FE80` | `FUN_0080fe80`, clear the flag |
| `0x810914` | `FUN_00810914`, OTAP `C0` dispatcher |
| `0x810CE0` | `PTR_DAT_00810ce0`, pointer used for the auth-enabled flag |
| `0x819FD4` | `FUN_00819fd4`, linked-master check |
| `0x82BCA4` | CRC16 byte helper |
| `0x82BCC8` | CRC16 buffer helper |
| `0x82BD48` | Flash page write |
| `0x82BD9C` | Flash erase |
