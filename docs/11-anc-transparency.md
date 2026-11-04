# 11 · ANC and transparency ("talk-through")

Can transparency be made better, and is that a data edit or a code patch? It's a code patch, or
live gain tweaking. The filters ship compiled into FIRM, and the container's dedicated ANC data
pages are empty in every image we have. Details below; narrative
version in [`data/reports/aap-transparency-analysis.html`](../data/reports/aap-transparency-analysis.html).

## Live tuning interface in FIRM

The real runtime gain interface is `+NTC=`, an AT line on the HFP channel (RFCOMM 1).
The line parser (`FUN_00c8d364`) copies the 9 chars after `+NTC=` into a buffer and posts
event `0xB2000002`; the dispatcher hands it to `FUN_00c4f6f0`:

```
+NTC=<side><op><B|F><6 digits>
```

* side `L` runs on the connected bud; `R` is relayed to the peer over the TWS link
  (tag `0xDA`, `FUN_0081ba1c`) and lands in the peer's `DAT_0083582e` path.
* op `2` sets the ANC mode: the selector position char is the mode index
  (`FUN_00c5eac4(buf[2]-'0')`).
* op `3` sets a gain: `F` = feedforward mic, `B` = feedback mic. The value is a linear
  float `digits / 10000`, so `010000` = 1.0000 (the factory default). Stored in
  `DAT_0082d494` (FF) / `DAT_0082d498` (FB), set via `FUN_00c5e888` / `FUN_00c5e8b4`.
* op `4` persists both gains to NV key `anc info` (16 bytes = 4 floats).
* op `5` reads a gain back: the bud replies `AT+NTC=<same 9 chars>` with the value
  filled in, sent by `FUN_00c4f5d4`.

Example: `+NTC=L3F012000` sets this bud's feedforward gain to 1.2.

Boot defaults come from `FUN_00c5e978`, which loads NV `anc info` if present and
otherwise uses 1.0 for every slot (gains 2 and 5 in its init struct are code literals,
so two of the six are always 1.0 unless an `anc info` key exists).

### Dead code: the `+ANC` family

The parser also accepts the lines below and posts `0xF4`-family events
(`FUN_00c8d364` → `FUN_00812144`), but nothing in FIRM consumes that event family.
They are factory leftovers and do nothing on this build.

| Command | Message ID | Argument | Reads as |
|---|---|---|---|
| `+ANCTEST=` | `0xF4000001` | 2 digits | ANC test mode select |
| `+ANCFFG=` | `0xF4000002` | 2 digits | feed-forward mic gain |
| `+ANCFBG=` | `0xF4000003` | 2 digits | feedback mic gain |
| `+ANCAG=` | `0xF4000004` | signed (parses leading `-`) | overall ANC gain |
| `+ANCDG=` | `0xF4000005` | digits | denoise / depth gain |

Neighbouring strings: `+MICTEST=`, `+MVS=`. Whether `+MVS=` (mic volume?) is wired up
the same way as `+NTC=` is unchecked.

## The data pages that *could* hold filters are never shipped

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

## The app can *compute* ANC filters

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

## The one data-level lever: ANC-mode EQ

h2sturbo EQ2P carries its five pages **twice**. StarFun's EQ store has scheme types
`TYPE_EQ=1, TYPE_ANC=2, TYPE_ENC=3, TYPE_ANC_2=4` and an `isAnc` flag → the second profile is
the output EQ used in ANC/transparency mode. It is an editable float table in a CRC-only partition.
Which profile binds to transparency vs. ANC-on is still unknown. The H3Pro Max3 doesn't use this
layout: its EQ2P has 7 profiles (`SLEQ 02 07`, see [16](16-live-flash-dump.md)).

## Summary

| Want to change | Kind of change |
|---|---|
| Prompts / SFX | data (TONE) — proven |
| Music EQ, ANC-mode EQ | data (EQ2P) — proven repack |
| Call-mic noise reduction params | data (SENC) — structure known, meaning partly |
| ANC / transparency gains | `+NTC=` over HFP — wired end to end, has read-back and NV persistence |
| ANC / transparency **filters** | **code** in FIRM, or populate pages 51–57 *if* FIRM honours them (unknown) |
