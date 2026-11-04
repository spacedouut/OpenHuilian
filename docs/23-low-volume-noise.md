# 23 · Low-volume crackle / white noise: what the firmware does to quiet audio

Users report a crackle or white-noise hiss that shows up when the volume is low. This page
collects what FIRM `2607061716` does to audio level, so the cause can be pinned to the
speaker/analog side or to firmware with a few listening tests. Static analysis only (Ghidra
on the [`h3pro_elf.py`](../tools/h3pro_elf.py) ELF); **nothing here has been run on buds.**

Short version: the firmware has three things that can make quiet audio sound grainy or hissy,
plus the usual analog suspects. Emulation rules out one of them (section 2) and
another after the music path was traced to the 32-bit mixer ramp (the ROM gain, section 1). The tests at the
bottom tell the rest apart.

## 1. Volume is a dB curve turned into a float gain

`FUN_00c521f0` (audio init) registers three 17-point curves from FIRM rodata. Each point is
`(s32 percent, f32 dB)`, highest first:

| Table | FIRM addr | Registered by | Used for |
|---|---|---|---|
| A2DP | `0xC33C8C` | `FUN_00c6006c` → ctx `+0x3C` | music, normal case |
| flat | `0xC33C04` | `FUN_00c60078` → ctx `+0x44` | music when a per-link property says so (below) |
| voice/tone | `0xC33D14` | `FUN_00c60084` → ctx `+0x54` | call / prompt volume |

| % | 100 | 90 | 85 | 80 | 75 | 65 | 60 | 55 | 50 | 40 | 35 | 30 | 25 | 15 | 10 | 5 | 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A2DP dB | 0 | -2 | -4 | -6 | -8 | -10 | -11 | -13 | -15 | -17 | -20.5 | -23 | -26 | -29 | -32 | -35 | -73 |
| voice dB | -9 | -10 | -12 | -14 | -16 | -18 | -21 | -24 | -27 | -30 | -33 | -36 | -40 | -44 | -49 | -54 | -59 |
| flat dB | 0 | 0 | 0 | ... | | | | | | | | | | | | | 0 |

`FUN_00c5d52c(level, table, n, mute_flag)` interpolates linearly between points (above the
first point it adds 0.5 dB per %), then returns `expf(dB * 0.115129)` = `10^(dB/20)`. The
music level (ctx `0x82D4D0 + 0x34`, 0-100) becomes the linear gain at ctx `+0x38`
(`FUN_00c60090`); voice uses `+0x50`. A fallback 3-point curve at `0xC449A4`
(100→0, 50→-29, 0→-73 dB) is used if no table is registered.

The gain is handed to the audio engine, not applied in FIRM: `FUN_00c60b88`/`FUN_00c618f4`
read it (`FUN_0080d32c`) and post it with `FUN_0080e3c2(stream, 0x11, &gain)`, which becomes
engine message `0x1A` (`FUN_0080c8b8`), then `FUN_00810d24(obj, 0xC, &gain)`, then the
mask-ROM gain ramp at `obj + 0x54`.

### The ROM gain ramp (emulated on the recovered mask ROM)

| ROM | Does |
|---|---|
| `0xBA0C(gain, ramp, rate, channels, bytes/sample)` | init: `{cur, coef = 1 - 3/(rate/4), target}` plus format bytes at `+0xC/+0xD` |
| `0xBA48(gain, ramp)` | set target (`vstr s0, [r0, #8]`) |
| `0xBA50(ramp, pcm, frames)` | apply. While ramping it does `x = (int)(float(x) * cur)` per sample (int16 or int32), then `cur = coef*cur + (1-coef)*target` per frame. Once within 1e-4 of the target it snaps and uses the block path `0xBB54` |

The multiply is `vcvt.s32.f32`: **it truncates toward zero, with no rounding and no dither**.
The ramp time constant is about 83 ms (`coef` 0.99975 at 48 kHz), and a full volume jump takes
about 0.8 s to snap. [`tools/emu/rom_gain.py`](../tools/emu/rom_gain.py) runs those three ROM
routines in Unicorn on the A2DP curve and compares them with an ideal float multiply. The
"round" column is the best any undithered integer output could do:

| vol % (dB) | 16-bit, -40 dBFS sine: SNR (round) | 32-bit, -40 dBFS sine: SNR (round) |
|---|---|---|
| 50 (-15) | 38.9 (43.2) dB | 133.3 (140.4) dB |
| 25 (-26) | 27.9 (34.1) dB | 121.6 (127.8) dB |
| 10 (-32) | 20.8 (28.8) dB | 118.1 (122.1) dB |
| 5 (-35) | 17.1 (22.8) dB, 8 % of samples zeroed | 114.6 (118.3) dB |

On a **16-bit** stream, quiet passages at low volume come out at 17-30 dB SNR. The error is
signal-correlated truncation, which is heard as grit or crackle. On a **32-bit** stream the
stage is inaudible.

**A2DP music runs at 32-bit, so this stage is ruled out for music.** The trace:

1. The A2DP sink opens its stream with a format record whose `+0xE` type is `2`
   (`FUN_00c60b88` → `FUN_00c66b4c` → `FUN_0080c8b8(1, …)` → `FUN_00c5db7a` → `FUN_00c6df08`,
   which stores the type at obj `+0x3A`).
2. For type-2 streams the volume message does not touch the per-stream ramp.
   `FUN_00810d24(obj, 0xC)` posts `FUN_0080c8b8(0x24, &gain)` instead, and that calls
   `0xBA48(gain, mixer + 0x68)`, the **mixer's master ramp**.
3. The master ramp is initialised in `FUN_00c5dd04` (the mixer, `*0x82D410`) as
   `0xBA0C(1.0, mixer + 0x68, 48000, 1, 4)`: 48 kHz, mono, **4 bytes per sample**. The mixer
   reports the same format to its sources (`FUN_0080c8b8` cases 7/8/9), and `FUN_00c6df08`
   builds a converter (`FUN_00c70784`) from the source's own format to it.

The ramp reads its sample width from its own struct (`+0xD`), so the music multiply takes the
int32 branch. At 5 % volume that is still 114 dB SNR on a -40 dBFS passage. Other stream types
use the per-stream ramp at obj `+0x54`, which is initialised with the mixer format too.

Two more details matter for quiet audio:

* **Flat table.** `FUN_00c60090` picks the all-0 dB table when the per-link query
  `FUN_00827564(5, 0, 0, 3, addr)` returns 1. In that mode the bud does no attenuation and the
  phone must turn the samples down *before* encoding them. Low volume then means low-level
  SBC/AAC frames, and codec quantisation at -30..-40 dBFS is the textbook source of crunchy,
  crackly quiet audio. Which link property selects this (absolute-volume support is the likely
  one) is not pinned yet.
* **No dither.** The float-to-PCM16 converter `FUN_0081718a` is a plain
  `ssat(int(x * 2^n), 16)`: truncate and saturate. At the bottom of the A2DP curve (-35 dB at
  5 %) a full-scale track peaks around -35 dBFS, so the DAC sees ~10 useful bits, and the
  truncation error is correlated with the signal (grainy) instead of flat hiss.

There is also an optional ×2 (+6 dB, `expf(0.690774)`) pre-gain on the music stream
(`FUN_00c60b88`, applied when ctx `+0x85` is 0 and a registered callback returns non-zero).
What drives it is open.

## 2. The voice-path noise suppressor (emulated: passthrough)

The HFP/SCO stream (8 or 16 kHz, `FUN_00c64aae`) creates an STFT noise suppressor when
ctx `+0x86` bit 1 is set (it is: `FUN_00c521f0` passes 1). Creation is `FUN_00c64860` →
`FUN_00c77bdc` (Hann analysis window, 2× overlap), tuned by `FUN_00c782d8(mod, 0xA900, cfg)`
from the compiled-in block at **FIRM `0xC33D9C`**:

```
02 00  06 00  01 ..   floats: 15.0 0.99 0.2 0.1 0.01 0.3 0.001 -15 -10 0.9 0.4 5 -20 -80
^overlap ^flags
```

Per frame, `FUN_00c780a4` runs: power spectrum; minimum-tracking noise estimate
(`FUN_00c77864`, flag bit 1); Wiener-style gain from a smoothed a-priori SNR (`FUN_00c778e4`);
gain smoothing across bins (`FUN_00c77980`, flag bit 2); then `FUN_00c77dc4`, which (flag bit 1)
**replaces every bin whose gain-scaled power is below the scaled noise floor with a random-phase
bin at noise level** (LCG `seed *= 6221`, `sqrt` magnitude, `sin`/`cos` phase). It also zeroes
5.6-5.8 kHz and 6.2-6.4 kHz outright. Overlap-add back to PCM16 is `FUN_00c77f4c`.

**Emulated: it does not add hiss.** [`tools/emu/voice_ns.py`](../tools/emu/voice_ns.py) builds the
module the way `FUN_00c64860` does (16 kHz, 256-sample frames, the stock `0xC33D9C` block) and
runs `FUN_00c78228` frame by frame in Unicorn. The mask-ROM malloc/memcpy/expf/FFT and FIRM's
`cosf`/`sinf` wrappers are stood in for in Python, and everything else is FIRM code. The
emulation was run three times: stock flags `6`, then images rebuilt with `cfw.py` at flags `4`
and `0`.

| Input (3 s, first 1 s skipped) | in | out, flags 6 (stock) | out, flags 4 / 0 |
|---|---|---|---|
| digital silence | silent | silent | silent |
| -60 dBFS white noise | -60.0 | -60.4 | -60.1 |
| -40 dBFS 1 kHz bursts + -70 dBFS hiss, level in the gaps | -70.0 | -70.6 | -70.4 |

Stock vs flags 4 differ by -73 dBFS on the noise input and -83 dBFS on the bursts, so the
noise fill replaces noise with noise of about the same level instead of adding any. The reason
is that flag bit 0 (`FUN_00c77a68`, the noise estimate the Wiener gain divides by) is **off** in
stock. That leaves the estimate zeroed and floored, so the gain stays at about 1 and the stage
passes audio straight through. Silence stays silent. This path is not the source of a
low-volume hiss, and no patch is shipped for it.

## 3. Not firmware

* **ANC / transparency mic hiss.** FF/FB mic self-noise and the ANC filter's noise floor are
  constant, so they are only noticed when music is quiet. The gains are live-adjustable
  ([11](11-anc-transparency.md), `hl dash`).
* **Amp/DAC idle noise or a damaged driver.** Also constant. A torn or rubbing driver crackles
  with signal and is worse at *high* volume, which is the opposite of the report.

## Telling them apart

| Test | If the noise ... | Then |
|---|---|---|
| Buds in, connected, nothing playing, ANC off (`hl dash`) | is still there | analog / amp floor, or one bud only = hardware |
| Same, ANC or transparency on, then FF/FB gain 0 | appears / disappears with ANC | ANC noise floor ([11](11-anc-transparency.md)) |
| Phone at low volume vs phone at max with a -35 dB track | only the first crackles | phone-side attenuation (flat table / codec) |
| Android: toggle *Disable absolute volume* (developer options) | changes | the flat-table switch above |
| Music vs a call at the same loudness | only in calls | call codec (CVSD/mSBC) or phone side; the voice NS is ruled out (section 2) |
| Swap buds / L vs R | only one bud | hardware |

## Open

* Which link property `FUN_00827564(5, …, 3)` reports, i.e. when the flat table is used.
* What sits after the 32-bit mixer: the final conversion to the DAC/amp format and its width.
  That is the last digital stage where low-volume resolution could be lost. Past it, the analog
  tests in the table are the next step.
* What the voice NS would do with flag bit 0 on (real noise reduction); `voice_ns.py` can test it.
