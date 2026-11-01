# The StarFun app and its servers

StarFun is the generic control app for Huilian TWS products. Two builds were decompiled with
JADX; the parts that matter are archived in [`reference/starfun-app/`](../../reference/starfun-app/).

## Versions

| Version | Behaviour with H3Pro Max3 | Catalog note (from the app's own update feed) |
|---|---|---|
| **2.0.7.016** | Works: connects, shows device info, fires the OTA check | `匹配377H3机型使用`, "for 377H3 models" |
| 2.0.7.017 | "This device is not supported, please replace it" | `增加EQ调节（仅支持个别机型）`, "adds EQ adjust (only some models)" |

The app self-update endpoint pushes .017 as "suggested". Stay on .016 for these buds.

## Servers and endpoints

| Host | Purpose | Auth |
|---|---|---|
| `https://ota.starfun.fun` | Firmware/APK catalog. `POST /api/v1/authentication/user` → JWT; `GET /api/v1/_/appversions` (list, 30 records); `GET /api/v1/_/appversions/update?package=&version=&deviceid=` (per-device check) | Tenant login baked into the APK (`OtaPresenter.getUserToken`). Tenant name `yiguo` appears in every download URL path. |
| `https://api.starfun.fun` | Main app API (accounts etc.) | user JWT |
| `https://info-api.starfun.fun` | New in .017: `/api/client/query?id=`, unused, returns empty for everything | none |
| `https://ota.shenjugroup.com` | Shenju OTA v2. Public Swagger at `/v2/api-docs` (saved as [`data/catalog/shenju_api.json`](../../data/catalog/shenju_api.json)). Endpoints: `release/auth`, `release/last`, `release/report`. No list endpoint; keyed by `firmware_id`. The IDs hardcoded in the app belong to a smartwatch (`w10_watch_2.0.4.up`). | app_id/app_secret from APK, no user login |

Download URLs look like
`https://ota.starfun.fun/api/data/update/yiguo/<package>/up/<file>.up` and need the JWT (the catalog
returns `http://`; `tools/pull_ota.py` upgrades it to `https://` before sending the token).
Directory listing on the CDN is 403; guessing `h3promax3` paths gives 404.

> The tenant username/password are **not** in this repo. `tools/pull_ota.py` reads
> `STARFUN_USER` / `STARFUN_PASS` from the environment. They can be recovered from the APK
> (`OtaPresenter.getUserToken`) if needed.

## The hidden local-file OTA path

Both .016 and .017 ship a **dormant** route to flash a `.up` from local storage, not wired to any
visible button:

```java
// com/sjbt/base/ui/SettingMoreActivity.java
private void chooseFile() {
    Intent intent = new Intent("android.intent.action.GET_CONTENT");
    intent.addCategory(Intent.CATEGORY_OPENABLE);
    intent.setType("*/*");
    startActivityForResult(Intent.createChooser(intent, getString(R.string.choose_file)), 100);
}
// onActivityResult(100, …) reads the picked .up, preserves the device's EQ/TONE data,
// and hands it to BtOtaHelper, the same transport used for server OTAs.
```

See `reference/starfun-app/2.0.7.017/SettingMoreActivity.java` around lines 613–651.
So the H3Pro `.up` rebuilt from the live dump ([device](../reference/device.md)) could be pushed with the app's own transport by a one-line patch
that exposes `chooseFile()`, with no server involved. That's read from the code; nobody has tried it.

## Command channel security

`CMDConfig.java` has `encryptData` / `verificationCmd`: a challenge/response, implemented in a
native `.so`, that unlocks the `C0` command channel. It is **not** a check on the firmware image.
The native code is the same 16-bit LFSR scrambler FIRM uses, so it's obfuscation, not a keyed
cipher, and `tools/huilian/proto.py` reproduces it ([command channel](../research/command-channel.md),
[research](../research/README.md)). OTA frames skip it. `tools/hl ota` flashes the buds without running the
handshake at all.

## Interesting command IDs seen

| Cmd | Meaning |
|---|---|
| `C0 04` | read product model (→ `proModel_04`) |
| `C0 09` | battery poll (sent every 2 s during OTA) |
| `C0 83` | flash read, app uses it to pull EQ2P/TONE off the buds before an OTA |
| `55AA 80–84` | OTA frames, see [OTA protocol](../reference/ota-protocol.md) |

The firmware side of the whole `C0` set, about sixty commands, is tabled in
[command channel](../research/command-channel.md).

## Data model hints

* `Eq2ItemType` reserves page IDs **51–57** for ANC / talk-through filter pages (never populated
  in any public image, [ANC](anc-and-transparency.md)). The H3Pro FIRM never asks for them either
  ([research](../research/README.md)).
* Local EQ store has scheme families `TYPE_EQ=1, TYPE_ANC=2, TYPE_ENC=3, TYPE_ANC_2=4`, and
  `EqScheme.isAnc`, explains the duplicated profile in EQ2P ([EQ2P](../reference/eq2p-senc.md)).
* `AncCalRespParam`, `CurveAncAssist`, `CurveAncReference` and `EqCoeffAnc` model classes exist,
  holding frequency lists, amplitude/phase curves and biquad coefficients. There's an ANC
  calibration UI somewhere in the vendor's world.

## The public catalog

The public catalog on `ota.starfun.fun` (tenant `yiguo`) has 30 records: 24 firmware images
across 16 product packages, plus APK self-update entries. Every image was downloaded,
`CONFIG`-validated and partition-parsed; they live in
[`firmware/starfun-catalog/`](../../firmware/starfun-catalog/). Raw dumps: `data/catalog/`.

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

### Reading the catalog

* **Silicon generations inside FIRM**: 21 images carry the marker `LHK-SL6800-TEST`
  (2022–2024); `h2sturbo 2506281656` alone carries `377 Super++` and the model string `H2S Turbo`;
  `a12pro 2410231555` and `h2sturbo 2409191721` carry neither. So the catalog straddles Huilian's
  SL6800 → 377 migration while the container header still says `SL6801`. The H3Pro Max3 (377H3)
  is the generation *after* the newest thing here.
* File-name suffixes `RYEQ` / `DQEQ` / `SYEQ` are reseller EQ re-tunes; those images carry the
  "extended" EQ2P page set ([EQ2P](../reference/eq2p-senc.md)).
* `h2slim` and `h2spro` are the only products with a second sensor blob `SEN2`.
* `a10 2311090955_RYEQ` has valid partition CRCs but a **stale outer container CRC**, consistent with
  a re-tune that fixed one checksum and not the other ([integrity](how-updates-are-accepted.md)).

### Full images, not patches

Every `.up` is a complete image sized to the flash class (≈1.0 MB or ≈2.0 MB) with the whole
partition table; the transport writes raw 512-byte blocks to absolute addresses
([OTA protocol](../reference/ota-protocol.md)); and the h2sturbo 2409191721 → 2506281656 diff shows FIRM changed
end-to-end (737,080 → 746,256 bytes). So a published `.up` is a full base image. For the H3Pro there is already one from the buds ([device](../reference/device.md)).

### Tools

```
export STARFUN_USER=… STARFUN_PASS=…
python3 tools/pull_ota.py a10                    # download + parse newest a10
python3 tools/pull_ota.py h3promax3 2607061716   # "No update returned" so far
```
