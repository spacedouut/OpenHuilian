# Patch files

How `tools/cfw.py` patch files are built. To apply one, see [apply a patch](../how-to/apply-a-patch.md).

## Format

```json
{
  "name": "Faster head tracking",
  "firmware": 2607061716,
  "partition": "FIRM",
  "about": "why this exists, with a pointer into the docs",
  "ops": [
    {"offset": "0x1234", "old": "2820", "new": "1420", "what": "fixed change"}
  ],
  "settings": [
    {"name": "tx_ms", "offset": "0xa7550", "type": "u8", "stock": 40,
     "default": 20, "min": 10, "max": 100, "what": "what the number means"}
  ]
}
```

* `offset` is relative to the start of the named partition.
* `ops` always apply. `settings` apply with `default` unless overridden with `--set`.
* `type` is `u8`, `u16`, `u32`, `f32` (all little endian) or `bytes` (hex string).
* `stock` is what the untouched firmware has there. It is both the safety check and what a GUI
  would show as the factory value.

A patch that adds code can also carry a `layout` block:

```json
"layout": {"firm_end": "0xaf000", "ram": {"addr": "0x878800", "len": "0x400"}}
```

* `firm_end` grows the FIRM partition so it ends at that flash address. SENC, TONE and EQ2P move
  up behind it, through the same code as [`repartition.py`](../../tools/repartition.py). The new
  bytes start as zero, so ops that place code there use zero `old` bytes.
* `ram` reserves a block at the top of the heap. `cfw.py` lowers FIRM's heap-size literal so the
  heap ends below the lowest reserved block. This only works for builds whose heap literal is
  known to `cfw.py` (`HEAP`).
* With several such patches, FIRM grows to the largest `firm_end`. Reserved RAM blocks must not
  overlap.
* Cave code is position dependent, so each patch fixes its own code and RAM addresses.
  [`tools/cave/build.py`](../../tools/cave/build.py) shows how to build one.

Patches live under `patches/<firmware version>/`. Anything that exposes a knob should say in
`what` which instruction or literal it edits so the next person can check it against
[command channel](../research/command-channel.md).

## Existing patches

| File | What | Knobs |
|---|---|---|
| `2607061716/head-tracking.json` | faster, less laggy head tracking ([command channel](../research/airpods-layer.md#head-tracking)) | `tx_ms` report period (stock 40), `decimate` fusion step every N+1 samples (stock 3), `alpha` smoother blend (stock 0.1) |
| `2607061716/debug-monitor.json` | `C0 D0`-`D4` debug monitor: peek, poke, call, log ring, used with `hl mon` ([debug monitor](../research/debug-monitor.md)). Grows FIRM by one page and reserves 1 KiB of heap RAM. Checked in Unicorn by `tools/emu/monitor_check.py`, not flashed yet | none |
| `2607061716/rom-read.json` | `C0 83` reads raw memory when address bit 31 is set, for dumping the mask ROM ([ROM read](../research/rom-read.md)). Stub checked in Unicorn by `rom-read-selftest.py`, not flashed yet | none |

## Rules

* Never flash a patched image without reading the recovery notes in
  [updater](../research/updater-otap.md) and [command channel](command-channel.md). A failed update does not roll FIRM back,
  and a flash that skips the final `04` leaves both buds in the updater.
* Keep patches version-pinned. Do not loosen the byte checks to make a patch "fit".
* A patch that touches the first 4 KiB of `FIRM` (the block copied to RAM) changes the header
  CRC too. `cfw.py` handles that, other tools may not.
* Nothing in this flow writes PSMP, so your addresses and pairing survive.

## What `cfw.py` checks and fixes

`cfw.py` refuses an image whose container CRC or partition CRCs do not verify, refuses a patch
written for another build, refuses anything that reaches outside its partition, and refuses an op
whose expected bytes are not there. After patching it recomputes the
partition CRCs in the index, the `+0x1C` header CRC of `FIRM` / `OTAP` (CRC16 over
`partition[0x30 : 0x30 + copied_block]`) and the `CONFIG` container CRC. A patched image differs
from stock only at the patched bytes and those CRC fields, unless a patch has a `layout` block.
Then FIRM's length, the moved partitions and the heap-size literal change too, and the result
must still pass the same OTA checks `hl ota` makes.
