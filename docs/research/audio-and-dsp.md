# Audio and DSP

FIRM reads EQ presets from EQ2P and call-mic processing parameters from SENC. ANC and transparency filters are compiled into FIRM, alongside DSP tables and literal constants that can be patched for a specific build.

## EQ2P reader

`FUN_00c690e8(profile, kind)` at `0xC690E8` locates EQ2P, walks its per-profile record-count table and copies matching eight-byte records into RAM. It matches the record's `kind` byte.

| Caller | Profile argument | Kind |
|---|---|---|
| `FUN_00c51578` | 0 at boot | 0 |
| `FUN_00c521f0` region | From a config pointer during audio init | 0 |
| `FUN_00c5c6b0` | Runtime profile during preset switch | 0 |

These are the three direct call sites, verified from raw BL instructions. All pass kind 0. No path in this build requests kinds 51 through 57, so adding those pages to EQ2P does not alter its ANC or transparency filters.

`FUN_00c52630` builds the `C0 90` preset block. `eq_preset_cur_num` selects the current preset. The `eq_ud_gain` NV block is 56 bytes and has a four-byte header exposed through the [command channel](command-channel.md#c0-handler-part-2).

## H3Pro EQ2P layout

EQ2P is 4,172 bytes at flash `0xC4000`, with CRC `0xACF5`. Its header is `SLEQ 02 07`, followed by seven u16 record counts, 92 for profile 0 and 71 for each of the other six. The complete header is 28 bytes.

| Record field | Size |
|---|---|
| `kind` | u8 |
| `param` | u8 |
| `band` | u16 |
| Value | f32 |

| Parameter | Meaning |
|---|---|
| `0x00` | Frequency in Hz |
| `0x01` | Q |
| `0x02` | Gain in dB |
| `0x03` | Band enable, 1 or 0 |
| `0xFC` | Always 1.0, likely filter type |
| `0xDD` | Profile pre-gain, about -4.8 to -9.73 dB |
| `0x3C` through `0x41` | Page 0 only, bands 0 through 3, extra filter block with thresholds 0, -9, -30 and -50 dB, likely a four-stage compressor/limiter |

Profile 1 contains the H2S Turbo factory curve byte for byte, padded to 14 bands. The frequency points are 80, 130, 240, 420, 900, 2421, 4100, 6100, 7990, 9750 and 12200 Hz. The 12.2 kHz point has +6.3 dB gain.

Profiles 2 through 6 are five alternative 14-band curves, including bass-heavy, vocal and treble-cut shapes. They likely back the app's model-dependent EQ presets and `eq_preset_cur_num`. Profile 0 is a more aggressive 14-band curve with the extra compressor-like block.

The complete decoded coefficients are in [eq2p_profiles.txt](../../data/partitions-h3promax3/eq2p_profiles.txt). The [EQ2P and SENC reference](../reference/eq2p-senc.md) describes the data format.

## Reserved ANC pages

The app's [Eq2ItemType.java](../../reference/starfun-app/2.0.7.016/uparser/model/eq/Eq2ItemType.java) reserves these decimal kind IDs. TT means talk-through.

| Kind | Name |
|---|---|
| 51 | `PID_ANC_MIC_FORWARD` |
| 52 | `PID_ANC_MIC_FEEDBACK` |
| 53 | `PID_ANC_MIC_COMPENSATE` |
| 54 | `PID_ANC_MIC_TT_FORWARD` |
| 55 | `PID_ANC_MIC_TT_FEEDBACK` |
| 56 | `PID_ANC_MIC_TT_COMPENSATE` |
| 57 | `PID_ANC_ANHT` |

Across all 24 catalog images, parsed EQ2P, SENC and SEN2 partitions contain zero pages with IDs 51 through 57. SENC/SEN2 contain call-mic ENC pages 21 through 32. EQ2P contains EQ pages 0 through 5 or 0 through 13. H3Pro also lacks kinds 51 through 57 and never requests them.

## SENC reader

A separate partition reader checks `SENC` magic, walks pages and passes eight-byte records to `FUN_00c65a10`. This function applies SENC data. Assigning it to EQ2P would be incorrect.

Its switch examines the record's first byte and covers kinds `0x15` through `0x1C` and beyond, corresponding to call-mic ENC pages 21 through 28. It skips records whose kind is at least `0xFF`.

The `piVar5[3] == 1` mode check selects between two destination layouts, described as single-mic and dual-mic parameter sets. The record structure is known, but some parameter meanings remain unverified.

H3Pro SENC is 2,056 bytes with CRC `0x77AA`, matching the H2S Turbo size and CRC.

## Factory ANC controls

The h2sturbo AT parser has a decimal-argument ANC block. It is present in both compared builds. These locations use that image's mapping and are not H3Pro runtime addresses.

| Location | Meaning |
|---|---|
| FIRM-relative `0x96AA0` to `0x96AC4` | Dispatch table |
| `0x896744` to `0x8968B2` | Thumb-2 handlers |
| `0x7FFE14` | Image base used for those handler addresses |

| Command | Message ID | Argument parser | Likely role |
|---|---|---|---|
| `+ANCTEST=` | `0xF4000001` | Two digits | ANC test-mode select |
| `+ANCFFG=` | `0xF4000002` | Two digits | Feed-forward mic gain |
| `+ANCFBG=` | `0xF4000003` | Two digits | Feedback mic gain |
| `+ANCAG=` | `0xF4000004` | Signed, recognizes a leading `-` | Overall ANC gain |
| `+ANCDG=` | `0xF4000005` | Digits | Denoise/depth gain |

Neighboring strings include `+MICTEST=`, `+MVS=` and `+NTC=`. H3Pro retains the ANC command strings and the factory audio interface. Its hidden `+test=` receive path is a likely route from SPP, but command replies over SPP and valid argument ranges are unverified.

The runtime overview calls `ANCAG` an ambient gain and leaves `ANCDG` as a fourth ANC gain. The parser analysis labels them overall ANC gain and denoise/depth gain. Those semantic labels are not fully verified.

## Native ANC calibration

`com.shenju.uparser` and native `libuparser` expose coefficient and reference-curve calculations.

```java
native int ancGetAncCofficent(EqConfigPoint p, EqCoeffAnc out);
native int ancGetAncRefAssistCurve(BaseAncCalRespParam p, CurveAncReference reference, CurveAncAssist assist);
native int ancGetFfRefCurve(AncCalRespParam p, CurveAncReference reference);
```

| API or model | Contents or output |
|---|---|
| `ancGetAncCofficent` | Biquad coefficients |
| `ancGetAncRefAssistCurve` | ANC reference and assist curves |
| `ancGetFfRefCurve` | Feed-forward reference curve |
| `AncCalRespParam` | Frequency list, amplitude/phase response and delay |
| `CurveAncReference`, `CurveAncAssist` | Calibration curves |
| `EqCoeffAnc` | Objective gain, minimum phase and biquad coefficients |

The vendor calibration pipeline can generate ANC filters from measured responses. No StarFun UI calls these APIs. Consumer images in this collection use compiled FIRM filters instead of the reserved ANC data pages.

## ANC-mode EQ and controls

H2S Turbo EQ2P contains its five pages twice. The app's EQ store has `TYPE_EQ = 1`, `TYPE_ANC = 2`, `TYPE_ENC = 3`, `TYPE_ANC_2 = 4` and `EqScheme.isAnc`. The second profile serves output EQ in ANC/transparency mode and is an editable float table in a CRC-only partition.

The binding between that profile and transparency versus ANC-on remains unknown. H3Pro uses the separate seven-profile layout above.

ANC mode values are 0 for off, 1 for ANC, 2 for transparency and 5 for adaptive. `FUN_00c51418` maps them to `close.mp3`, `noise.mp3`, `pass_those.mp3` and `adpt.mp3`. [Settings store](settings-store.md#setting-semantics) gives the live state addresses and command mapping.

| Change | Mechanism and evidence |
|---|---|
| Prompts and SFX | TONE data replacement works on hardware |
| Music EQ and ANC-mode EQ | EQ2P data, repacking verified |
| Call-mic noise reduction | SENC data, structure known and meanings partly decoded |
| ANC/transparency gains | Runtime AT commands exist, live use unverified |
| ANC/transparency filters | FIRM code or compiled data changes |

## Compiled DSP tables

Audio initialization follows `FUN_00c521f0` to `FUN_00c604dc`. It places EQ2P and SENC addresses in the audio context alongside compiled FIRM tables.

| CPU address | Data |
|---|---|
| `0xC33BE8` | Threshold ladder |
| `0xC33C04` | Threshold ladder |
| `0xC33C8C` | Threshold ladder |
| `0xC33D14` | Threshold ladder |
| `0xC33D9C` | Filter/DSP configuration block |

The ladders include `100/90/85/80/75...`, with some float mixtures such as -9.0. They likely describe DRC/compressor thresholds.

The block at `0xC33D9C` begins `02 00 06 00 01`, then includes floats 15.0, 0.98, 0.2, 0.1, 0.01, 0.3, 0.001 and -15.0. These likely represent gains and smoothing factors. The exact parameter roles remain unverified.

These are byte-exact patch targets tied to this firmware version. They permit DSP data changes without altering EQ2P.

## Verified patch offsets

The [2607061716 head-tracking patch](../../patches/2607061716/head-tracking.json) contains three literals verified against the raw image.

| Name | FIRM-relative offset | Stock value | Role |
|---|---|---|---|
| `tx_ms` | `+0xA7550` | 40 | Transmit period in milliseconds |
| `decimate` | `+0x64A1A` | 3 | Literal used by the every-fourth-entry orientation update |
| `alpha` | `+0x64C74` | 0.1 | Smoothing constant |

The [head-tracking pipeline](airpods-layer.md#head-tracking) describes the 240 Hz samples, about 60 Hz pose updates and 25 Hz reports these constants affect. Use [apply a patch](../how-to/apply-a-patch.md) and [cfw.py](../../tools/cfw.py) for version checks and CRC repair.

The [ANC and transparency explanation](../explanation/anc-and-transparency.md) covers the practical limits. The detailed static audio report is [aap-transparency-analysis.html](../../data/reports/aap-transparency-analysis.html).
