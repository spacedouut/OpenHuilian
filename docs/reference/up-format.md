# The `.up` container

Derived from all 24 catalog images, then **cross-checked against the vendor's own parser**
(`vendor/shenju-flashloader/decompiled-src/burn_service/flash_loader/up_parser.py`) and two
independent open-source implementations (`smartlink_flash/fwhelper/main.c`, `sl6806/docs`).

## Big picture

```
┌──────────────────────────────┐ 0x000
│ outer header  "CONFIG"       │  256 bytes, describes the file, carries chip name + CRC
├──────────────────────────────┤ 0x100  ← "body" = a verbatim image of flash starting at 0
│ "HLKJ" bootloader/config hdr │
│ …                            │
│ partition index (body+0x3000)│
│ FIRM  SENC  [SEN2]  TONE  EQ2P … zero padding …  OTAP            │
└──────────────────────────────┘
```

Rule that makes everything easy: **`file_offset = flash_address + 0x100`**. The body is literally
what ends up in flash. A raw flash dump (see the OpenPod dump in `firmware/openpod-sl6801/`) starts
directly with `HLKJ`; wrapping it with a 256-byte `CONFIG` header turns it into a `.up`.

## Outer header (file offset 0x000–0x0FF)

| Offset | Size | Field | Notes |
|---|---|---|---|
| 0x000 | 6 | `"CONFIG"` | magic |
| 0x006 | 4 | u32 LE `0x100` | body start (vendor: `int.to_bytes(256, 4, 'little')`) |
| 0x010 | 4 | u32 LE body length | `= filesize − 0x100` |
| 0x014 | 2 | u16 LE CRC16 | CRC16/CCITT-FALSE over the entire body, see [integrity](../explanation/how-updates-are-accepted.md) |
| 0x016 | ≤16 | ASCII chip name | `"SL6801"` in all 24 images. The vendor flasher picks the chip **solely** from this string (`get_up_chip_name_lower()`); `.upex` files are treated as SL6806. |
| 0x0FE | 2 | `55 AA` | terminator |

## Body header (`HLKJ`, file 0x100)

| Body offset | Field |
|---|---|
| 0x000 | `"HLKJ"`, 慧联科技 (Huilian Technology) |
| 0x020 | u32 LE **index offset** (body-relative). `0x3000` in every image → index at file `0x3100`. |

The rest of the first 0x3000 bytes is bootloader/config territory. In the raw SL6801 dump the
partition table sits at `0xD000` and FIRM at `0xE000`, i.e. layouts differ per product; always
follow the pointer at body+0x20, never hardcode 0x3000.

## Partition index

```
u32  count
u32  build version        (YYMMDDhhmm, e.g. 2506281656)
u32  (reserved)
u32  (reserved)
then count × 16 bytes:
   char[4] tag        "FIRM" "SENC" "SEN2" "TONE" "EQ2P" "OTAP" "PSMP"
   u32     flash_addr
   u32     length
   u32     crc         (CRC16 in the low 16 bits; fwhelper reads it at +14 for table ver ≥ 0x30, +12 otherwise)
```

The h2sturbo 2506281656 index, for reference:

```
index @ body+0x3000   count=6   version=2506281656
FIRM  addr 0x00004000  len 0x000B6310 (746,256)  crc 0x406F
SENC  addr 0x000BB000  len 0x00000808 (  2,056)  crc 0x77AA
TONE  addr 0x000BC000  len 0x000144C7 ( 83,143)  crc 0xDFA3
EQ2P  addr 0x000D1000  len 0x000005B2 (  1,458)  crc 0x3437
OTAP  addr 0x001D2000  len 0x00028D50 (167,248)  crc 0x0CAA
PSMP  addr 0x001FC000  len 0x00004000 ( 16,384)  crc 0     , declared, not stored
outer: body length 2,075,984, container CRC 0x7B79, chip "SL6801"
```

## The partitions

| Tag | What it is | Size | Notes |
|---|---|---|---|
| `FIRM` | Main application + DSP image, ARM **Thumb-2** | 0.7–0.75 MB | 0x30-byte wrapper then a load descriptor; entry `0x00804C41` (Thumb bit set); image base ≈ `0x7FFE14` for h2sturbo. 24/24 unique. Contains the Bluetooth stack, AAP server, ANC code, NV key names, and a software AES used for Continuity adverts, not for image checks ([integrity](../explanation/how-updates-are-accepted.md), [research](../research/README.md)). |
| `SENC` | Sensor / call-mic parameter table | 2,056 B constant | `[u16 group][u16 idx][f32]` records; pages 21–32 ([EQ2P](eq2p-senc.md)) |
| `SEN2` | Second sensor table | - | only h2slim, h2spro |
| `TONE` | Voice prompts + UI clicks archive | 83–94 KB | `[u32 size][name\0]…` directory, then raw MP3/WAV ([TONE](tone.md)) |
| `EQ2P` | EQ profiles, magic `SLEQ` | ~1.5 KB | plain float table ([EQ2P](eq2p-senc.md)) |
| `OTAP` | OTA updater stub | **exactly 167,248 B in all 24 images** | 23 distinct blobs despite fixed size; in h2sturbo only the first 4 KB changed between builds. No crypto strings found. |
| `PSMP` | Persistent settings (NV key/value store) | 16 KB at end of flash | declared with crc 0 and address beyond EOF, **not shipped in OTAs** so user settings survive. Present in raw dumps. Editable with the vendor's `psm-nvds.dll` or offline with `tools/psmp_tool.py` ([PSMP](psmp.md)). |

## Flash classes

| Class | OTAP @ | PSMP @ | `.up` size |
|---|---|---|---|
| 1 MB | `0x0D2000` | `0x0FC000` | 1,027,232 / 1,027,664 B |
| 2 MB | `0x1D2000` | `0x1FC000` | 2,076,240 B |

In 2 MB images the span ≈0x0D2000–0x1D2000 (~1 MB, right after EQ2P) is zero padding, free space that a CFW could
use, e.g. for a bigger TONE partition (index address+length rewrite).

## Shared vs per-product payloads (sha256 across the 24 images)

FIRM 24 distinct · OTAP 23 · SENC 11 · TONE 10 · EQ2P 10 · SEN2 2.
Tone/EQ/sensor packs are shared assets reused across product families; FIRM and OTAP are per build.

## Related raw-dump format

A raw flash dump (`firmware/openpod-sl6801/GN438_sl6801_fulldump.bin`, 2 MiB) begins with `HLKJ`.
`smartlink_flash/fwhelper` scans it as: HLKJ @0, partition table @`0xD000`, `FIRM` @`0xE000`
(0x192570 B), `TONE` @`0x1A1000`, `PSMP` @`0x1FC000` (0x4000 B, with live `bt_addr`, `device_id`
records). `fwhelper flash.bin dump2fw out.up` rebuilds a `.up` from a dump.

## CRCs

### The algorithm

**CRC16/CCITT-FALSE**: polynomial `0x1021`, initial value `0xFFFF`, no reflection, no final XOR.

Derived by brute-matching the stored values across the catalog, then found verbatim in the
vendor flasher:

```python

### Where CRCs live

| CRC | Covers | Stored at |
|---|---|---|
| **Partition CRC** | the partition payload (`file[addr+0x100 : addr+0x100+len]`) | low 16 bits of the `crc` u32 in that partition's index record |
| **Container CRC** | the entire body `file[0x100:]` | outer header offset `0x14` |
| **OTA whole-payload CRC** | everything the app streams (partitions + index) | sent in the `55AA82` frame before data ([OTA protocol](ota-protocol.md)) |
| **Per-frame CRC8** | each Bluetooth OTA frame | CRC8/Maxim (Dallas), appended to the frame |

`PSMP` has crc 0 because it isn't shipped.

### Across the catalog

* Partition CRCs: **match in 24/24 images** (5 or 6 partitions each).
* Container CRC: **match in 23/24**. The exception, `a10_2311090955_RYEQ.up`, has correct
  partition CRCs and a stale outer CRC, looks like a reseller EQ re-tune that fixed the inner
  checksum but not the outer one, and StarFun still serves it as `types: all`. The buds never
  see the container header. The app strips it and the `82` CRC is computed from the bytes it
  sends ([updater](../research/updater-otap.md)), so the outer CRC only matters for the vendor flasher
  and the tools here.
* `smartlink_flash/fwhelper scan` independently reproduced both mismatches on that file.
* The OpenPod `B27_251112.up` also reports a FIRM CRC mismatch under `fwhelper`, a modified/test
  artifact or table-version quirk; not generalised.

Why the CRC is the only check, and what that means, is in [how updates get accepted](../explanation/how-updates-are-accepted.md).
