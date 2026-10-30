# 19 · Patching your own firmware: `cfw.py` and patch files

The unit-specific data on a bud (addresses, serials, the app authorization code, your
settings) all lives in the `PSMP` partition. The `.up` the StarFun app dumps leaves it out and
the updater carries it over untouched ([17](17-firmware-internals.md)). The code and data
partitions (`FIRM`, `TONE`, `EQ2P`, `SENC`) are the same bytes for everyone on the same build.
That is what makes a shareable patch possible. A patch says "in this partition, at this offset,
I expect these bytes and I write those", and it only applies when the version and the bytes
match.

## The flow

1. Dump your own firmware with `tools/hl read` ([20](20-hl-cli.md)) or
   [`tools/flashdump.py`](../tools/flashdump.py) ([16](16-live-flash-dump.md)), then wrap it with
   `tools/build_up.py`. You get a `.up`.
2. `python3 tools/cfw.py info my.up` shows the build and checks the CRCs.
3. `python3 tools/cfw.py apply my.up my-cfw.up patches/2607061716/head-tracking.json`
   applies the patch with its defaults. Add `--set name=value` to turn a knob, for example
   `--set tx_ms=25 --set alpha=0.4`.
4. Flash `my-cfw.up` the same way a stock update goes in, over the `55AA` OTA transport from
   [6](06-bt-ota-protocol.md). `tools/hl ota my-cfw.up` does both buds ([20](20-hl-cli.md)) and
   is how the head-tracking patch went onto real buds.

`cfw.py` refuses an image whose container CRC or partition CRCs do not verify, refuses a patch
written for another build, refuses anything that reaches outside its partition, and refuses an op
whose expected bytes are not there. After patching it recomputes the
partition CRCs in the index, the `+0x1C` header CRC of `FIRM` / `OTAP` (CRC16 over
`partition[0x30 : 0x30 + copied_block]`) and the `CONFIG` container CRC. A patched image differs
from stock only at the patched bytes and those CRC fields.

## Patch file format

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

Patches live under `patches/<firmware version>/`. Anything that exposes a knob should say in
`what` which instruction or literal it edits so the next person can check it against
[18](18-firm-walkthrough.md).

## Patches so far

| File | What | Knobs |
|---|---|---|
| `2607061716/head-tracking.json` | faster, less laggy head tracking ([18](18-firm-walkthrough.md#head-tracking-pipeline)) | `tx_ms` report period (stock 40), `decimate` fusion step every N+1 samples (stock 3), `alpha` smoother blend (stock 0.1) |

## Rules

* Never flash a patched image without reading the recovery notes in
  [17](17-firmware-internals.md) and [20](20-hl-cli.md). A failed update does not roll FIRM back,
  and a flash that skips the final `04` leaves both buds in the updater.
* Keep patches version-pinned. Do not loosen the byte checks to make a patch "fit".
* A patch that touches the first 4 KiB of `FIRM` (the block copied to RAM) changes the header
  CRC too. `cfw.py` handles that, other tools may not.
* Nothing in this flow writes PSMP, so your addresses and pairing survive.
