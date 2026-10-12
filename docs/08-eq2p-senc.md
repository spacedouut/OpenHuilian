# 08 · EQ2P and SENC — the parameter tables

Both are plain little-endian float tables in CRC-only partitions. Raw copies from h2sturbo
2506281656 are in [`data/partitions-h2sturbo/`](../data/partitions-h2sturbo/).

## EQ2P (magic `SLEQ`)

Records of 8 bytes starting at offset 26:

```
[u8 kind][u8 param][u16 band][f32 value]
kind  0x00 = main playback EQ      param 0x00 = frequency (Hz), 0x01 = Q, 0x02 = gain (dB)
kind  0x02..0x05 = further band tables (mic / ANC / sidetone paths, 25 Hz – 16 kHz)
```

### Factory H2S Turbo tuning (11-band parametric, band IDs 0–10)

| Freq | Q | Gain |
|---|---|---|
| 80 Hz | 0.71 | −2.0 dB |
| 130 Hz | 1.2 | −1.9 dB |
| 240 Hz | 0.71 | −4.6 dB |
| 420 Hz | 1.0 | −1.3 dB |
| 900 Hz | 1.0 | +0.5 dB |
| 2421 Hz | 1.5 | +3.8 dB |
| 4100 Hz | 2.0 | 0.0 dB |
| 6100 Hz | 5.5 | −4.5 dB |
| 7990 Hz | 2.2 | +4.5 dB |
| 9750 Hz | 5.2 | −0.5 dB |
| 12200 Hz | 4.7 | +6.3 dB |

Bass/low-mid scooped, presence and "air" lifted — a bright, AirPods-Pro-style target.

### Pages and the two-profile layout

The container's parameter format is organised in numbered **pages** (the app's `Eq2ItemType`).
Across the 24 images:

| EQ2P flavour | Pages | Which images |
|---|---|---|
| minimal | 0, 2, 3, 4, 5 — **twice** | h2sturbo, h2sultra, h2spro, a6pro, a8, fit30, fit50 |
| extended | 0–13 (adds EFFECT, HW and seven preset pages) | the reseller re-tunes: a10, a12pro, b24, fit31, fit40, h2slim (`RYEQ`/`DQEQ`/`SYEQ`) |
| ANC / talk-through pages **51–57** | **never present** | none of 24 ([11](11-anc-transparency.md)) |

The duplicated five pages are two **profiles**. The app's EQ store has scheme families
`TYPE_EQ=1, TYPE_ANC=2, TYPE_ENC=3, TYPE_ANC_2=4` and an `isAnc` flag, so the second copy is the
**ANC-mode EQ**. The two factory curves differ slightly (low shelf −2.0 vs −1.8 dB at
130 Hz; broadband trim −4.80 vs −5.04 dB). Which profile binds to transparency vs ANC-on is untested.

### Editing

Edit floats in place → recompute EQ2P CRC16 + container CRC ([05](05-crc-and-integrity.md)).
Done successfully as a round-trip (`repack_test.up`). The 377 build also exposes a runtime
user EQ (`eq_ud_gain`, `eq_preset_cur_num` NV keys, `UDEQ` string) — the app's .017 "EQ adjust"
feature — so on 377-generation devices EQ may also be changeable live without touching flash.

## SENC / SEN2 (magic `SENC`)

Same `[u16 group][u16 idx][f32]` style table, 2,056 bytes in every image. Carries pages **21–32**
in all 24 images: call-microphone noise-reduction parameters (single- and dual-mic base/extended
params, DRC and EQ for mic and "trumpet" paths), plus sensor / wear-detect / motion calibration
constants (values like −25, −60, 125, 0.985). `SEN2` (h2slim, h2spro only) is a second such table.
11 distinct SENC blobs across the catalog — shared per product family.
