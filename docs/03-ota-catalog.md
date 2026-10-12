# 03 · The public StarFun OTA catalog

The public catalog on `ota.starfun.fun` (tenant `yiguo`) has 30 records: 24 firmware images
across 16 product packages, plus APK self-update entries. Every image was downloaded,
`CONFIG`-validated and partition-parsed; they live in
[`firmware/starfun-catalog/`](../firmware/starfun-catalog/). Raw dumps: `data/catalog/`.

**All 24 images declare chip `SL6801`.** There is no `h3promax3`, no `377`, no `h3*` package.

| Package | Catalog version | Internal build | Flash class | Size | Partitions | File |
|---|---|---|---|---|---|---|
| `H2S Ultra` | 2309162000 | 2309161705 | 2 MB | 2,076,240 | FIRM/SENC/TONE/EQ2P/OTAP/PSMP | `h2s_ultra_2309161705.up` |
| `a10` | 2307011403 | 2307011403 | 1 MB | 1,027,664 | FIRM/SENC/TONE/EQ2P/OTAP/PSMP | `a10_2307011403_-_RYEQ.up` |
| `a10` | 2311090956 | 2311090955 | 1 MB | 1,027,664 | FIRM/SENC/TONE/EQ2P/OTAP/PSMP | `a10_2311090955_RYEQ.up` |
| `a10studio` | 2307011403 | 2307011403 | 1 MB | 1,027,664 | FIRM/SENC/TONE/EQ2P/OTAP/PSMP | `a10_studio_2307011403_-_SYEQ.up` |
| `a12pro` | 2410231600 | 2410231555 | 1 MB | 1,027,664 | FIRM/SENC/TONE/EQ2P/OTAP/PSMP | `a12_pro_2410231555.up` |
| `a6pro` | 2307011406 | 2307011406 | 1 MB | 1,027,664 | FIRM/SENC/TONE/EQ2P/OTAP/PSMP | `a6_pro_2307011406.up` |
| `a8` | 2307011406 | 2307011406 | 1 MB | 1,027,664 | FIRM/SENC/TONE/EQ2P/OTAP/PSMP | `a8_2307011406.up` |
| `b24` | 2307011405 | 2307011405 | 1 MB | 1,027,664 | FIRM/SENC/TONE/EQ2P/OTAP/PSMP | `b24_2307011405_-_DQEQ.up` |
| `fit30` | 2209242029 | 2209242029 | 1 MB | 1,027,232 | FIRM/SENC/TONE/EQ2P/OTAP/PSMP | `fit30_2209242029.up` |
| `fit31` | 2307251119 | 2307251119 | 1 MB | 1,027,664 | FIRM/SENC/TONE/EQ2P/OTAP/PSMP | `fit31_2307251119_-_DQEQ.up` |
| `fit40` | 2307011404 | 2307011404 | 1 MB | 1,027,664 | FIRM/SENC/TONE/EQ2P/OTAP/PSMP | `fit40_2307011404_-_RYEQ.up` |
| `fit50` | 2210141125 | 2210141125 | 1 MB | 1,027,232 | FIRM/SENC/TONE/EQ2P/OTAP/PSMP | `fit50_2210141125.up` |
| `h2slim` | 2301172000 | 2301171607 | 1 MB | 1,027,664 | FIRM/SENC/SEN2/TONE/EQ2P/OTAP/PSMP | `h2_slim_2301171607.up` |
| `h2slim` | 2308111648 | 2308111648 | 1 MB | 1,027,664 | FIRM/SENC/SEN2/TONE/EQ2P/OTAP/PSMP | `h2_slim_2308111648_-_DQEQ(1).up` |
| `h2slim` | 2311120942 | 2311120942 | 1 MB | 1,027,664 | FIRM/SENC/SEN2/TONE/EQ2P/OTAP/PSMP | `h2_slim_2311120942(1)_-_DQEQ-6B32-A2698.up` |
| `h2slimc` | 2310241700 | 2310241610 | 1 MB | 1,027,664 | FIRM/SENC/TONE/EQ2P/OTAP/PSMP | `h2slimc_2310241610.up` |
| `h2slimc` | 2311061000 | 2311060931 | 1 MB | 1,027,664 | FIRM/SENC/TONE/EQ2P/OTAP/PSMP | `h2slimc_2311060931.up` |
| `h2spro` | 2308091143 | 2308091143 | 2 MB | 2,076,240 | FIRM/SENC/SEN2/TONE/EQ2P/OTAP/PSMP | `h2spro_2308091143(1).up` |
| `h2spro` | 2311131723 | 2311131723 | 2 MB | 2,076,240 | FIRM/SENC/SEN2/TONE/EQ2P/OTAP/PSMP | `h2spro_2311131723(1)_6B32_A2698.up` |
| `h2sturbo` | 2409211800 | 2409191721 | 2 MB | 2,076,240 | FIRM/SENC/TONE/EQ2P/OTAP/PSMP | `h2s_turbo_2409191721.up` |
| **`h2sturbo`** | **2506281656** | **2506281656** | 2 MB | 2,076,240 | FIRM/SENC/TONE/EQ2P/OTAP/PSMP | **`h2s_turbo_2506281656.up`** ← newest, "377 Super++" |
| `h2sultra` | 2311041607 | 2311041607 | 2 MB | 2,076,240 | FIRM/SENC/TONE/EQ2P/OTAP/PSMP | `h2s_ultra_2311041607.up` |
| `h2sultra` | 2312191611 | 2312191611 | 2 MB | 2,076,240 | FIRM/SENC/TONE/EQ2P/OTAP/PSMP | `h2s_ultra_2312191611(1)[6B34-A3048-61.3.0].up` |
| `h2sultra` | 2401041027 | 2401041027 | 2 MB | 2,076,240 | FIRM/SENC/TONE/EQ2P/OTAP/PSMP | `h2s_ultra_2401041027[6B34-A3048-61.3.0].up` |

## Reading the catalog

* **Silicon generations inside FIRM**: 21 images carry the marker `LHK-SL6800-TEST`
  (2022–2024); `h2sturbo 2506281656` alone carries `377 Super++` and the model string `H2S Turbo`;
  `a12pro 2410231555` and `h2sturbo 2409191721` carry neither. So the catalog straddles Huilian's
  SL6800 → 377 migration while the container header still says `SL6801`. The H3Pro Max3 (377H3)
  is the generation *after* the newest thing here.
* File-name suffixes `RYEQ` / `DQEQ` / `SYEQ` are reseller EQ re-tunes; those images carry the
  "extended" EQ2P page set ([08](08-eq2p-senc.md)).
* `h2slim` and `h2spro` are the only products with a second sensor blob `SEN2`.
* `a10 2311090955_RYEQ` has valid partition CRCs but a **stale outer container CRC** — consistent with
  a re-tune that fixed one checksum and not the other ([05](05-crc-and-integrity.md)).

## Full images, not patches

Every `.up` is a complete image sized to the flash class (≈1.0 MB or ≈2.0 MB) with the whole
partition table; the transport writes raw 512-byte blocks to absolute addresses
([06](06-bt-ota-protocol.md)); and the h2sturbo 2409191721 → 2506281656 diff shows FIRM changed
end-to-end (737,080 → 746,256 bytes). So a published `.up` is a full base image. For the H3Pro we already have one from the buds ([16](16-live-flash-dump.md)).

## Tools

```
export STARFUN_USER=… STARFUN_PASS=…
python3 tools/pull_ota.py a10                    # download + parse newest a10
python3 tools/pull_ota.py h3promax3 2607061716   # "No update returned" so far
```
