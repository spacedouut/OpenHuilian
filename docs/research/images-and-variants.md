# Images and variants

The comparison set contains 24 catalog images and an OpenPod dump, with H3Pro Max3 `2607061716` as the main reference. They share container and boot conventions but differ in audio layouts, AirPods services and product-specific firmware.

## Catalog sweep

[upparts.py](../../tools/upparts.py) lists partitions, extracts them and dumps strings. The sweep covers every catalog image and the OpenPod dump. Per-image reports compare unique strings against H3Pro and both h2sturbo references.

These strings occur in other builds and are absent from H3Pro `2607061716`. Counts refer to builds in the collection.

| String | Builds | Interpretation |
|---|---|---|
| `transparency_adaptive_enable` | 7 | Adaptive-transparency NV key |
| `transparency_param` | 3 | Transparency tuning block |
| `air_hangup_setting` | 10 | Additional AirPods setting |
| `audioRoutingRequestID2` | 19 | Audio-routing hook |
| `space_open.mp3`, `space_hold.mp3` | 2 | Spatial-audio prompts, while H3Pro only has `space_close.mp3` |
| `version_error.mp3` | 3 | Version-mismatch rejection prompt |
| `hardware EQ config to %d. // 0: None, 1: pop, 2: rock...` | 1 | Named hardware EQ presets |
| `sensor motion active timer` | 5 | Motion tuning timer |

H3Pro-exclusive strings in this collection include `HeartRate`, `HeartRateService`, `com.apple.hid.heartrate-access`, `air heartrate tx timer` and `vc30fx_oscclk_freq`. The same applies to `H3Pro2`, `H3Pro3`, `377Super PRO3`, `Super2026+` and build stamp `20230713_70aa57dc`.

String presence suggests features but does not prove every corresponding code path works. String absence alone does not prove a feature is impossible.

## H3Pro container

The reference image is [h3promax3_2607061716_live.up](../../firmware/h3promax3/h3promax3_2607061716_live.up). It is reconstructed from a complete 1 MiB flash read using `C0 83`.

[build_up.py](../../tools/build_up.py) wraps `flash[0 : end-of-OTAP]` in a standard 256-byte `CONFIG` header with body length, body CRC16 and a `55 AA` trailer. [tone_tool.py](../../tools/tone_tool.py) reports `ALL CRCs VALID`.

The chip-name field at header `+0x16` is empty. Flash does not contain that outer-container field and no official H3Pro `.up` supplies a value. OTAP never sees it, while the desktop flasher uses it to select the chip.

PSMP is declared in the index but excluded from the committed image. Its records contain device identity, authorization, pairing and advert-key data. The [settings-store page](settings-store.md) lists key names and lengths without per-unit values.

The live image keeps the HLKJ body, index at `0x3000`, partition names and CRC conventions used by SL6801 images. The repository's offline tools handle it without format changes. [Memory map and boot](memory-map-and-boot.md#flash-layout) gives every partition address, length and stored CRC.

## H3Pro image contents

The extracted data is under [data/partitions-h3promax3](../../data/partitions-h3promax3/), including `firm_strings.txt`.

| Area | H3Pro contents | Comparison |
|---|---|---|
| Build identity | `377Super PRO3`, `Super2026+` | Catalog identities include `377 Super++` and `LHK-SL6800-TEST` |
| TONE | 18 prompts with `[size][name\0]` directory, including `game_mode_close.mp3` | H2S Turbo has 17 |
| EQ2P | 4,172 B, `SLEQ 02 07`, seven profiles | H2S Turbo has a duplicated five-page layout |
| SENC | 2,056 B, CRC `0x77AA` | Same size and CRC as H2S Turbo |
| AAP | AccessoryService plist, `devmotion6` HID descriptor, 2007 Apple copyright string | Same general accessory layer |
| Names | `AirPods`, `AirPods Pro`, `AirPods Pro2` | Name strings alone do not determine the pop-up identity |
| BLE model bytes | `0E 20`, template at CPU `0xC4BF58` | There are 50 raw literal hits, most in code |
| HFP | `AT+XAPL=0042-0887-0100,2` | Same XAPL feature value |
| ANC | `+ANCFFG`, `+ANCFBG`, `+ANCAG`, `+ANCDG`, `+ANCTEST`, `anc_mode_sel`, `anc_mode_phone_sel` | Same command strings |
| Motion | `task motion`, `taskB motion`, `air motion timer` | Head-tracking pipeline present |
| Feature-string scan | No `spatial`, `conversation` or `adaptive` strings | This does not negate the known motion code or adaptive mode value |

All 18 TONE entries list with `tone_tool.py list` and use the same replacement format. TONE occupies all 84,903 declared bytes, with about 1 KiB before EQ2P. The claimable padding between EQ2P and OTAP is about 53 KB. See [flash layout](memory-map-and-boot.md#flash-layout) before interpreting the image as full.

The image-content description calls `AirPods Pro2` a difference from the catalog build. The detailed h2sturbo AAP description also lists that string, so it is not a reliable H3Pro-only marker.

[Audio and DSP](audio-and-dsp.md#h3pro-eq2p-layout) contains the seven-profile record layout and curve details. [AirPods layer](airpods-layer.md) contains the identity table, descriptors and code addresses.

## h2sturbo and SL6800 comparison

The detailed AAP comparison uses `h2s_turbo_2506281656.up`, a 377-generation SL6801 build, and build `2409191721`, described as SL6800 in the source.

| Present in the 377 build | Meaning |
|---|---|
| `AccessoryService`, `ReportDescriptor`, `MaxReportSize` | Accessory HID layer |
| `devmotion6` | Head-motion sensor service |
| `H2HTransformation` | Head-to-head transform for spatial orientation |
| `taskB motion`, `air motion tx timer` | Motion processing and transmission |
| `UDEQ`, `eq_ud_gain`, `eq_preset_cur_num` | User-defined EQ |
| `AirPods` | Additional name variant |

Both builds already contain an AAP server, SDP records, XAPL, Siri and the same BLE template. H3Pro adds the heart-rate HID service within this comparison set.

The h2sturbo SDP and ANC addresses use different image mappings from H3Pro. They are explicitly marked on the [AirPods](airpods-layer.md#sdp-and-hid-descriptors), [audio](audio-and-dsp.md#factory-anc-controls) and [address](addresses.md) pages.

StarFun `2.0.7.016` connects to H3Pro and checks OTA. Its catalog description names 377H3. Version `2.0.7.017` rejects these buds with “This device is not supported, please replace it” and advertises EQ adjustment for some models. The user-defined EQ strings match that feature description.

## OpenPod comparison

`GN438_sl6801_fulldump.bin` contains an MP3-player firmware with music, ebook and picture UI and 7,540 strings. It uses the same silicon family but a different product firmware. Its useful comparisons here are PSMP and the bootloader.

Across all 25 images, bootloader code in the first `0x3000` bytes is byte-identical. Only three flash-class configuration bytes differ between the 1 MB and 2 MB classes. [Memory map and boot](memory-map-and-boot.md#flash-class-configuration) gives the offsets and values.

## zero_ota.bin

The StarFun APK's `assets/zero_ota.bin` is a 204,728-byte Cortex-M service/development program with 674 functions.

| Field | Value |
|---|---|
| Initial SP | `0x86A4A4` |
| Entry | `0x804C41` |
| Entry convention | Same RAM-entry convention as OTAP |
| Container | Bare program, no `CONFIG`, HLKJ wrapper, partition index or container CRCs |

| Strings or subsystem | Evidence |
|---|---|
| CLI shell | `CLI_HALT`, `Enable echo`, `syntax error` |
| Device files | `/dev/key`, `/dev/rtc`, `/dev/timer`, `/dev/tp`, `/dev/pmu`, `/dev/uart2` |
| Filesystem | FatFS, `f_mount`, `f_findfirst` |
| Peripherals | SDMMC, touch panel, USBD |
| System services | Dual-core PLL reporting, PMU/VBUS events |
| PSM/NV | `no enough memory for psm write`, `authorization_code` |
| Restart/update routes | `update set pc and restart`, `update set sd and restart` |

These features indicate a vendor recovery/maintenance image with a POSIX-style service environment. Its use as a recovery image for H3Pro is unverified.

A valid H3Pro package would first need a defined replacement target and a correct container. OTAP is a plausible target because of the RAM-entry convention, but that choice remains unresolved. The bare file is not a ready-to-send `.up`.

Any transfer through the known OTA path still requires the complete sequence `80`, `81`, `82`, repeated `83`, `84`, then `04`. The documented sender writes 512-byte chunks and the index last. Omitting `04` leaves the buds in OTAP even after successful finalize. [OTAP updater](updater-otap.md) explains the state machine and limited read surface available there.

## App-provided update route

Both StarFun versions contain a dormant local-file picker in `SettingMoreActivity.chooseFile()`. It uses `ACTION_GET_CONTENT`, `CATEGORY_OPENABLE`, MIME type `*/*` and request code 100.

`onActivityResult(100, ...)` reads the selected `.up`, preserves device EQ and TONE, then calls `BtOtaHelper`, the same transport used by server updates. The relevant archived code is [SettingMoreActivity.java](../../reference/starfun-app/2.0.7.017/SettingMoreActivity.java), around lines 613 through 651.

Exposing the picker is a possible app change, but this route is unverified on hardware. The [app and servers explanation](../explanation/the-app-and-servers.md) covers the surrounding app behavior. [Command channel](command-channel.md#native-library) covers its native LFSR and CRC functions.
