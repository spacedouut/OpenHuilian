# 11 · ANC and transparency ("talk-through")

Can transparency be made better, and is that a data edit or a code patch? It's a code patch, or
live gain tweaking. The filters ship compiled into FIRM, and the container's dedicated ANC data
pages are empty in every image we have. Details below; narrative
version in [`data/reports/aap-transparency-analysis.html`](../data/reports/aap-transparency-analysis.html).

## Live tuning interface in FIRM — [confirmed strings/dispatch, inferred semantics]

The incoming AT-command parser has an ANC block. Each parses a decimal argument and posts a
message with a fixed ID (dispatch table FIRM `0x96AA0–0x96AC4`, handlers `0x896744–0x8968B2`,
Thumb-2, image base `0x7FFE14`). Present in both h2sturbo builds.

| Command | Message ID | Argument | Reads as |
|---|---|---|---|
| `+ANCTEST=` | `0xF4000001` | 2 digits | ANC test mode select |
| `+ANCFFG=` | `0xF4000002` | 2 digits | feed-forward mic gain |
| `+ANCFBG=` | `0xF4000003` | 2 digits | feedback mic gain |
| `+ANCAG=` | `0xF4000004` | signed (parses leading `-`) | overall ANC gain |
| `+ANCDG=` | `0xF4000005` | digits | denoise / depth gain |

Neighbouring strings: `+MICTEST=`, `+MVS=`, `+NTC=`. Whether these are accepted over the BT
command channel without the keyed challenge/response, and their valid ranges, are **[unverified]**.

## The data pages that *could* hold filters are never shipped — [confirmed]

The app's `Eq2ItemType` (archived in
[`reference/starfun-app/2.0.7.016/uparser/model/eq/Eq2ItemType.java`](../reference/starfun-app/2.0.7.016/uparser/model/eq/Eq2ItemType.java))
reserves seven page IDs:

```
51 PID_ANC_MIC_FORWARD    52 PID_ANC_MIC_FEEDBACK    53 PID_ANC_MIC_COMPENSATE
54 PID_ANC_MIC_TT_FORWARD 55 PID_ANC_MIC_TT_FEEDBACK 56 PID_ANC_MIC_TT_COMPENSATE   (TT = talk-through)
57 PID_ANC_ANHT
```

Every `EQ2P`, `SENC` and `SEN2` in all 24 catalog images was parsed and page IDs counted:
**pages 51–57 appear zero times.** What ships is pages 21–32 (call-mic ENC) in SENC/SEN2 and
pages 0–5 / 0–13 (EQ) in EQ2P ([08](08-eq2p-senc.md)).

## The app can *compute* ANC filters — [source]

`com.shenju.uparser` (native `libuparser`) exposes:

```java
native int ancGetAncCofficent(EqConfigPoint p, EqCoeffAnc out);                 // biquad coeffs
native int ancGetAncRefAssistCurve(BaseAncCalRespParam, CurveAncReference, CurveAncAssist);
native int ancGetFfRefCurve(AncCalRespParam, CurveAncReference);                // feed-forward reference curve
```

with models `AncCalRespParam` (frequency list, amplitude/phase response, delay), `CurveAncReference`,
`CurveAncAssist`, `EqCoeffAnc` (objective gain, minimum phase, biquad coefficients). So the
vendor's *calibration* tooling produces ANC filters from measured responses — i.e. the pipeline to
generate pages 51–57 exists, it's just not how these consumer images were built (filters were
baked into FIRM). No UI in StarFun calls these.

## The one data-level lever: ANC-mode EQ — [inferred]

h2sturbo EQ2P carries its five pages **twice**. StarFun's EQ store has scheme types
`TYPE_EQ=1, TYPE_ANC=2, TYPE_ENC=3, TYPE_ANC_2=4` and an `isAnc` flag → the second profile is
the output EQ used in ANC/transparency mode. It is an editable float table in a CRC-only partition.
Which profile binds to transparency vs. ANC-on, and whether H3Pro Max3 uses the same layout, is
**[unverified]** (needs a 377H3 image or a live read-back).

## Summary

| Want to change | Kind of change |
|---|---|
| Prompts / SFX | data (TONE) — proven |
| Music EQ, ANC-mode EQ | data (EQ2P) — proven repack |
| Call-mic noise reduction params | data (SENC) — structure known, meaning partly |
| ANC / transparency gains | runtime AT commands — exist, untested |
| ANC / transparency **filters** | **code** in FIRM, or populate pages 51–57 *if* FIRM honours them (unknown) |
