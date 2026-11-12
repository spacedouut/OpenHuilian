# H3Pro Max3 head tracking: measured defects and replacement experiment

Offline investigation, firmware **2607061716**, 2026-11-12. No Bluetooth,
flashing, commits, or changes to OTAP/PSMP/bootloader were performed.

## Conclusions and release status

The complaint is reproducible without an iPhone: the estimator absorbs sustained
rotation as gyro bias, its integration timebase is inconsistent with 240 Hz,
and the HID producer distorts both orientation and angular velocity.
The previous three-constant patch does not fix the first two defects.

**Not a hardware-qualified fix.** `head-tracking-v2.json` is an experimental
fusion-only patch. It preserves the stock phone frame and its remaining defects.
`head-tracking-v2-lab.json` also sends a direct quaternion, but its body-to-phone
frame and velocity scale are NOT calibrated: **do not flash that lab patch**.
The distinction matters: improved internal quaternions do not establish correct
iPhone playback, timestamps, peer operation, or physical mounting.

## Evidence and reproducibility

- Image SHA256: `7554b57974b79c270804b79f2bcac1580a663057524030c7b6a5c582dc6231d7`.
- Mask ROM SHA256: `81f733395d0aa7402541dcc004d65070a998c484d058d6ddf41688e199eec8df`.
- Machine-readable measurements: `tools/headtrack/results.json`.
- Harness: `tools/emu/headtrack.py`; postprocessor: `headtrack_analysis.py`;
  regression tests: `headtrack_test.py`.
- Reference algorithm, C source, linker script, patch builder, focused Ghidra
  recovery: `tools/headtrack/{reference.py,filter.c,filter.ld,build.py,recover.py}`.
- Full sample/report traces, compiler artifacts, rebuilt images and decompilation
  are in `/home/ubuntu/.openclaw/workspace/tmp/headtrack/`; focused decompilation
  and assembly are in its `evidence/` directory. Traces retain raw report bytes.

REA/Ghidra opened the supplied ELF, but its inventory lacked the requested
function entries. Missing entries were not treated as absent code. Explicit
Thumb disassembly/decompilation was recovered with an in-memory Ghidra program,
cross-checked against Capstone and actual execution. `recover.py` reproduces it
without modifying an existing Ghidra project. The REA target was closed.

The harness runs the **actual FIFO conversion, bias/classifier, fusion, Euler
conversion, report callback and real mask-ROM arithmetic**. It supplies I2C
register/FIFO bytes, calloc, side/profile/connection predicates, and synthetic
RTOS/BT clocks; captures the final send instead of transmitting. No gyro,
quaternion or trig math is shimmed in stock/old/C tests. Only the explicitly
named `python` variant replaces estimator math with the reference prototype.
Full boot/peripheral/queue scheduling is not simulated by this harness.

## Actual pipeline and math

### Sensor and queue

`0xC589BC` writes the table at `0xC34450`:
`07:02 09:77 0A:06 0D:38 17:00 15:03 10:07 11:07`.
This is the known LSM6DSV16BX 240 Hz setup; actual interrupt/ODR timing still
needs a hardware measurement. The sensitivity assumptions used by tests are
0.061 mg/LSB and 0.0175 dps/LSB.

`0xC58A5C` reads FIFO status at register `0x1B`, tag at `0x78`, six data bytes
through `0xC58A50`; tag `1` is gyro and `2` accel. It drains paired entries,
bounded by the caller's count (motion producer `0xC58F60` requests 10).
Accel axes are read Z,Y,X; gyro X,Y,Z. The actual scaling functions are
`0xC5968C: raw*0.061`, `0xC596A4: raw*35`. Accel becomes
`int16(raw*0.061/2000*32768)` and gyro `int16(raw*35/1000000*32768)`.
The motion context then multiplies them by `2/32768` g and `500/32768` dps.
Thus the factor 35 is NOT evidence of a doubled physical gyro sensitivity.

`0xC59298` initializes the motion task with defaults at `0x82B7A4`:
`[2.0,500.0,20.0,5000.0, mode=0]`. These are copied to context `0x82DB10`
by `0xC683A8`; `0xC684D0` loads reference quaternion, offsets and sign flags
from `0xC32130`. Queue plumbing is outside the harness; its per-entry endpoint
is `0xC68924(gyro_int16*,accel_int16*)`.

### The earlier decimation/smoothing explanation is incorrect

`0xC68924` first applies the selected signed 3x3 axis matrix (`0x82C5A0`,
identity after `0xC68580(0)`). It increments a counter at `0x82DAD0`.
The every-fourth-entry branch calls **only the optional plugin** through
`context+0x4C = 0x82DB5C`; that slot is null in this build.

After that branch, ordinary bias estimation and `0xC74F7C` execute **on every
valid gyro entry**, not every fourth. There is already a linked fusion filter.
An empty optional plugin does not mean there is no fusion.

In default mode 0, `0xC68600` computes a changing alpha:

```
alpha = 0.011 * exp(-3.321928 * S)
S = .25*gyro_class + .25*gyro_delta_class
    + .24*bias_alignment_class + .26*accel_delta_class
bias[n] = bias[n-1] + alpha*(gyro[n]-bias[n-1])
corrected_gyro[n] = gyro[n] - bias[n]
```

The last two equations are `0xC68284`, not an output-angle smoother.
The classifier bins squared gyro magnitude at 38.44,40.96,43.56,46.24,49;
squared gyro differences at .36,.49,.64,.81,1; squared accel differences
at 4,9,16,25,36 times 1e-6. Bias/gyro alignment uses squared normalized
dot products with thresholds .75,.933,.9698,.9924 and a separate negative-dot
case. Classes span 0..5. There is no trustworthy stationary/moving gate:
steady intentional rotation eventually becomes estimated bias. The resulting
high-pass behavior also produces a negative tail after a turn stops.
At alpha .011, the bias time constant is about 0.377 s at 240 Hz;
the classifier makes it much longer during vigorous motion.

Modes 2/3 select `0xC679E0`, `0xC6739C`, `0xC674C8`, `0xC675EC`,
`0xC67EA4`, with longer history-based bias adaptation. They are NOT the tested
default. `0xC67374` initializes LP coefficients .005 and .0002. The values
100 and 10 passed to `0xC6739C` are per-update step limits, not Hz cutoffs:
it computes `(input-previous)*coefficient`, optionally rejects a large step,
then updates running statistics. If interpreted as simple first-order LPFs,
those coefficients correspond to approximately .191 and .00764 Hz at 240 Hz,
not 100 Hz and 10 Hz. There is no basis for the previously alleged 150 ms
output-smoother group delay.

### Existing quaternion fusion

`0xC74F7C` is a Mahony-like gravity-corrected gyro integrator:
gyro degrees/s become radians/s; accel is normalized; an estimated gravity
cross-product supplies proportional feedback (gain at `0x82B8A8`, default 1).
An integral correction is enabled at gain .01 only when squared half-vector
error exceeds .0064; otherwise its accumulator is cleared.

With `v` the predicted **negative** gravity half-vector and `a` normalized accel:
`e = a cross v`, `omega = radians(corrected_gyro) + Kp*e + integral`.
Then `q += .5*dt*(q tensor [0,omega])`, followed by normalization.
Quaternion components are `w@0x82B89C`, `x@0x82EC68`, `y@0x82EC6C`,
`z@0x82EC70`. `dt = context[3]*1e-6 = .005 s`, passed at `0xC68D12`.
At actual 240 Hz it should be 1/240 s: stock's angular integration gain is 1.2.

Initialization (`0xC74E14`) is `w=sqrt((1-az)/2), x=-ay/(2w),
y=ax/(2w), z=0`. Exactly `a=(0,0,+1)` divides by zero and poisons the stock
quaternion with NaNs; the replacement has a dedicated inverted-gravity branch.
This is a confirmed edge case, not proof it occurs during normal wear.

The shipped code contains `vldr/vstr`, `vfma.f32`, `vdiv.f32`, conversions and
other single-precision VFP instructions, including `0xC68284`.
Hard-float M4 compilation/emulation works. This establishes the firmware's
SP-FPU requirement, not the exact silicon core revision or available cycle budget.

### Euler and HID production

`0xC74C88` computes `p = q * conjugate(reference)` using `0xC74C0C`, then:

```
E0 = atan2(2*(w*z-x*y), w*w-x*x+y*y-z*z) * 180/pi
E2 = -asin(2*(w*x+y*z)) * 180/pi
E1 = -atan2(2*(w*y-x*z), w*w-x*x-y*y+z*z) * 180/pi
```

`0xC68924` applies per-side sign flags and integer offsets, wraps each angle,
and writes **integer degrees** `[E0,E1,-E2]` at `0x833D1C`. Thus quaternion
precision is discarded before the phone path. This Euler chart also has a
singularity; it is not equivalent to transporting the original quaternion.

`0xCAB53C` creates the 40 ms timer; callback `0xCAAAB0` requires new-pose,
connection, profile and role gates. For reported pose `[P0,P1,P2]`, it forms
`A=(side ? 60 : -60)-P1`, `B=-P2`, `C=-P0`, with wrapping.
It then adds a **piecewise Euler shear** to C using coefficients -1/3 or -1/4
from `0x82B804/0x82B808`, negates A on one side or B on the other, and wraps
again. This is not merely a fixed quaternion rotation.

`0xCAA838(A,B,C)` makes a quaternion from half angles:
`[ca*cb*cc-sa*sb*sc, sa*cb*cc-ca*sb*sc,
ca*sb*cc+sa*cb*sc, ca*cb*sc+sa*sb*cc]`.
Additional reference/profile quaternion multiplications use `0xCAA7D8` and
`0xCAAA0C`; profile initialization is `0xCAA554`.
The callback chooses the sign so w<=0 and emits only vector components.

Offsets in the default 0x4F-byte packet buffer `0x836287` (NOT HID-descriptor
bit offsets; another profile uses a shifted buffer) are:

| Offset | Observed field |
|---|---|
| 0x0D | 16-bit sequence; skips low-byte zero by adding 0x81 instead |
| 0x16 | 64-bit timestamp, ns: `(BT_slots*625 + fine_us)*1000 - 68000` on local path |
| 0x21 | 64-bit BT-domain time in us on that path |
| 0x29,0x2B,0x2D | signed Q15 quaternion y,x,z, implicit nonpositive w |
| 0x2F,0x31,0x33 | signed motion-rate values, nonlinear/scaled Euler differences plus dither |
| 0x3B,0x3D,0x3F | accel differences, scaled by fixed 360 and divided by 16 or 64 |
| 0x4B | incrementing counter |

For rate generation, Euler differences are shortest-wrapped, multiplied by
`3000/elapsed_ms`, then conditionally amplified/clamped (limits 3600 or 5000).
One branch multiplies the third component by 4; the other mixes/scales components.
The callback **unconditionally adds periodic tick-dependent values**:
periods 47,37,13 packets, excursions up to 48,36,14 counts. Exactly stationary
input therefore does not yield stationary motion-rate fields. These are observed
wire counts; interpreting all three as physical dps would be unjustified.

The timestamp is constructed at **transmit time**, not the IMU sample time.
The constant subtraction is **68 microseconds, not 68 milliseconds**.
The synthetic-clock test recovers ~68.33 us including integer rounding.
The peer-clock branch uses a separately reconstructed clock, sample/subslot
state and a +30,000,000 ns offset; that branch is not hardware-validated.
Neither the descriptor's vendor blob nor this code proves iOS's clock/prediction
contract. Do not "fix" timestamp units speculatively.

### Bud source, metadata and relay limits

The local filter writes `0x833D1C`; the HID callback reads it. Motion task
`0xC59298` contains the >200 ms peer-send gate and sends six integer-pose bytes
with peer opcode 0x4B when role/state conditions allow it. Another hot-code path,
`0x80D3D6 -> 0x80E5D0`, can overwrite the same pose from signed bytes expanded
by two (2-degree resolution); `0x80E560` is the inverse compressor.
Therefore do not assume every HID report always uses a fresh master-local IMU.
Which route actually runs, and how opcode 0x4B connects to all consumers,
remain unverified. A 200 ms relay would add up to ~200 ms age before scheduling,
but that is a conditional bound, not a measured cause on this user's buds.

H3Pro includes `H2HTransformation` blobs at `0xC47ABE`, `0xC49FCC`,
`0xC4A1B4`. Their identity/profile selection and physical head transform have
not been calibrated here. Active/passive quaternion conventions and left/right
handedness must not be inferred solely from a sign reversal in a synthetic test.

## Measured scenarios

All streams use 240 paired IMU samples/s, real FIFO conversion, default mode 0,
side selector 0, profile 3, negative-Z gravity at the initial pose. Truth is
body-to-world quaternion integration, with accel transformed consistently into
the rotating body frame. Noise seed is 377. No linear acceleration, sensor
temperature model, Bluetooth jitter or queue contention is included.
There is 2 s initial rest. Runs are 12 s except still/bias (122 s) and sine
(22 s). "Bias" adds `[.1,-.15,.3]` dps; "noise" adds 0.02 g accel noise and
0.15 dps gyro noise, independent Gaussian per sample.

The table is **internal quaternion geodesic RMSE in degrees from t>=2 s**,
sampled at each variant's report instants. It is NOT measured phone/head error.
Stock reports every 40 ms; old/v2 every 20 ms. Tiny stock/old metric differences
are sample-grid effects, not different filters. A regression compares every
internal quaternion bit-for-bit between stock and old during combined motion.

| Scenario | Stock | Old patch | Compiled v2 | Stock final error | v2 final error |
|---|---:|---:|---:|---:|---:|
| Still, 122 s | 0 | 0 | 0 | 0 | 0 |
| Slow yaw, 10 dps for 8 s | 14.911 | 14.901 | 0.113 | 27.062 | 0.165 |
| Fast yaw, +90 then -90, each in .5 s | 5.166 | 5.171 | 0.0026 | 0.0092 | 0.000014 |
| Nod, +90 then -90 | 6.255 | 6.262 | 0.143 | 0.256 | <0.00001 |
| Roll, +90 then -90 | 6.255 | 6.262 | 0.143 | 0.256 | <0.00001 |
| Combined noncommuting 3-axis motion | 9.670 | 9.670 | 0.0924 | 13.482 | 0.0284 |
| Constant stationary gyro bias, 122 s | 0.1305 | 0.1305 | 0.2893 | 0.1307 | 0.2893 |
| Accel + gyro noise | 0.1033 | 0.1030 | 0.1143 | 0.0390 | 0.0697 |
| Yaw +270 through +180 | 45.375 | 45.370 | 0.0796 | 67.615 | 0.1027 |
| Yaw -270 through -180 | 45.375 | 45.370 | 0.0796 | 67.615 | 0.1027 |
| Pitch to 90, body-axis turn, return | 9.392 | 9.399 | 0.1249 | 6.888 | 0.0298 |

The slow-turn truth ends at 80 degrees. Stock/old reach 56.073 degrees at turn
end and decay to 52.938 by 12 s; v2 reaches and retains 79.835 degrees.
The fast-turn estimator reaches 104.110 degrees for a true 90 (old report
grid captures the peak); v2 reaches 89.995. Maximum nod/roll error falls from
about 15.59 to .4723 degrees. Maximum gimbal-scenario internal error falls
from 13.667 to .2439. Yaw +270 ends near 202.385 stock versus 269.897 v2.

Stock is **better** on stationary constant-bias startup and slightly quieter
on this noise test. The replacement does not magically improve every metric.
Its .289-degree startup yaw offset stops growing after calibration; it has no
external yaw reference. Arbitrarily slow real yaw below the stationary gate
is indistinguishable from bias using this six-axis sensor alone.

### Causal ablations and latency

Disabling stock bias subtraction but leaving its 5 ms dt gives 95.801 degrees
for the 80-degree slow turn and about 107.993 at the fast 90-degree peak.
Correcting dt alone, but retaining the bias estimator, leaves only 44.115 of
the slow 80-degree turn and undershoots the fast peak by about 3.50 degrees.
Thus timebase and bias defects partially cancel in some motions: changing
one constant cannot repair the speed-dependent gain.

For 10-degree sine yaw, the actual firmware/reference frequency responses are:

| Hz | Stock gain | Old gain | v2 gain | Stock phase lead |
|---|---:|---:|---:|---:|
| .25 | 1.04773 | 1.04772 | .99937 | 7.690 degrees |
| 1 | 1.19973 | 1.19973 | .99980 | .740 degrees |
| 4 | 1.19990 | 1.19990 | .99995 | .019 degrees |

A finite-difference group-delay estimate from .9/1.1 Hz is 5.536 ms stock,
5.540 ms old, approximately zero v2, **for this amplitude/operating condition**.
The adaptive estimator is nonlinear/time-varying, so no single global group
delay describes it. The stock fast-turn 45-degree crossing is ~41.7 ms EARLY,
not late, because of overgain. Wrong gain, bias tails and report prediction
artifacts can feel "out of sync" without a large positive filter delay.

The timer contributes 0..40 ms stock or 0..20 ms old/v2 sample-and-hold age,
mean about 20/10 ms if sample arrivals and timer are uniformly phased.
There can also be 0..4.17 ms sample phase and additional FIFO/task/BT/iOS delay.
These are cadence-derived bounds/expectations, not measured hardware latency.
The >200 ms peer path is separate and could dominate if selected.

### Actual report defects, beyond estimator error

With completely still input, settled stock rate fields span
`[-48,44],[-36,36],[-14,10]` counts. Quiet-window RMS is 23.28 counts stock
and 19.93 old (different phases/cadences); a clean gyro should produce zero.
The lab encoder produces zero on the same stream. One-degree Euler increments
also make the derivative jump: before later amplification, one degree in 40 ms
is 75 counts, in 20 ms 150. A faster timer can worsen this differentiated
quantization even while reducing report age.

An ideal-quaternion oracle bypasses estimator error but uses the real Euler
and report functions. A local orthogonal frame fit predicts large rotations
poorly: about 42.24 degrees error at a 90-degree body-X turn and 163.44 at
120 degrees in the chosen reference pose. Local Jacobian singular values are
1.092,1.081,.862 rather than all 1 (5-degree finite differences, includes
integer quantization). This demonstrates nonrigid mapping, not a calibrated
claim about a user's anatomical pitch/roll axes. Its determinant sign alone
does not prove wrong handedness: inversion/active-passive conventions matter.

The lab encoder's decoded-wire RMSE/max errors versus canonical synthetic
truth are .0036/.0094 degrees fast yaw, .105/.168 slow yaw, .0847/.176 combined,
.0818/.895 positive wrap, and .112/.241 gimbal. The .895-degree wrap spike
comes from Q15 vector-only encoding near implicit w=0, even with float fusion.
Noise has .213/1.215 degrees including initial noisy tilt alignment.
These are lab body-frame wire errors, **not an iPhone interoperability result**.

## Ranked diagnosis

1. **Sustained rotation is removed as bias.** This explains speed-dependent
   wrong position and post-turn drift; 80 degrees becomes about 53.
2. **5 ms integration at 240 Hz.** This explains high-speed overgain/overshoot,
   making position and synchronization inconsistent across speeds.
3. **Nonrigid Euler-to-HID transform, quantization and invented rate dither.**
   These can make a receiver's orientation and prediction disagree, even with
   an ideal estimator. Their precise perceptual effect depends on iOS decoding.
4. **25 Hz output and transmit-time stamping.** Known cadence ages and no
   sample timestamps; hardware scheduling and receiver prediction remain open.
5. **Peer freshness and mounting/profile calibration.** High potential impact,
   but not established as the active cause on these particular buds.

The old `decimate 3->1` modifies only the null-plugin branch; its `alpha .1->.3`
literal is overwritten by the classifier in mode 0. Only `tx_ms 40->20` has
the intended direct effect in this tested configuration.

## Replacement, deployment boundary, and remaining work

An existing standard Mahony-style six-axis complementary filter is adequate;
a larger library/ML model is unnecessary. The small custom implementation is
needed for this firmware's ABI, absolute RAM addresses and hook format.
It integrates float quaternions at full rate with dt=1/240, applies gravity
feedback only near 1 g, and learns gyro bias only after .5 s within .96..1.04 g
and gyro norm <.75 dps. Bias time constant is .5 s; no output-angle smoothing
or speculative future-pose prediction is added. Gravity gain is 2/s.

Python and compiled C agree within .002 degrees in the regression stress run.
The actual three-axis combined and gimbal trajectories, both yaw wraps and all
minimum scenarios were run with compiled hooks, not only the Python model.
The existing FIFO/queue data format, integer peer output and stock HID path
remain intact in the fusion-only patch.

Build details: installed GCC 14.2.1, `cortex-m4`, Thumb, `fpv4-sp-d16`,
hard-float ABI, no libc/libm/unresolved symbols. Code is 1,436 bytes at
`0xCB0000`; state is 48 bytes at `0x878400`, reservation 0x300 bytes.
FIRM grows to flash end `0xB2000`; moved SENC/TONE/EQ2P are at
`0xB2000/0xB3000/0xC8000`. Heap-size literal is reduced through cfw's layout
support, reserving the top region; required header/partition/container CRCs
are recomputed. Hooks are BLs at `0xC68F6C` (bias) and `0xC68D12` (fusion).
The lab-only extra hook is `0xCAB22C` (final report send).
Mode 1/2/3 bias paths are NOT covered by the mode-0 bias hook.

Seven regressions pass, including actual rebuilt v2 `.up` execution, exact
old/stock equality, reference/C agreement, inverted gravity, both wraps and
stationary report artifacts. A representative full per-entry instruction
count is 8,255 stock versus 8,147 v2: no observed code-count increase, but
Unicorn instruction counts are not silicon cycles or a real-time CPU guarantee.
Repartition/boot validation passes with 383 traced flash accesses and all
18/18 prompt readers correct; OTAP/PSMP locations and contents remain unchanged.

Before a direct-quaternion release, measure each bud's body-to-head rotation
and iPhone active/passive convention, replace the Euler shear by rigid frame
composition, confirm velocity units/axis ordering from a receiver capture,
and carry actual sample timestamps into the BT clock domain. Handle recenter,
stale peer data and master switches explicitly. The lab encoder is only a
proof of float-to-existing-wire-format feasibility: it retains transmit-time
timestamps, assumes 12 rate counts/dps from one stock branch, and does not
calibrate H2HTransformation or alternate packet profiles.

## Exact offline reproduction and optional user-run trial

Run from `/home/ubuntu/OpenHuilian`. Scratch directory below already exists.
These commands only read local images and write scratch/allowed build outputs.
The checked-in JSON patches do not require a compiler to apply.

```sh
python3 tools/cfw.py apply \
  firmware/h3promax3/h3promax3_2607061716_live.up \
  /home/ubuntu/.openclaw/workspace/tmp/headtrack/v2.up \
  patches/2607061716/head-tracking-v2.json

uv run --offline -q --with unicorn==2.1.1 --with capstone==5.0.3 --with numpy \
  python tools/emu/headtrack_test.py \
  --image /home/ubuntu/.openclaw/workspace/tmp/headtrack/v2.up -v

uv run --offline -q --with unicorn==2.1.1 --with capstone==5.0.3 \
  python tools/emu/repart_check.py \
  firmware/h3promax3/h3promax3_2607061716_live.up \
  /home/ubuntu/.openclaw/workspace/tmp/headtrack/v2.up
```

To rerun the entire matrix (including a deliberately uncalibrated offline
encoder), or rebuild with the installed compiler:

```sh
uv run --offline -q --with unicorn==2.1.1 --with capstone==5.0.3 --with numpy \
  python tools/emu/headtrack.py \
  --out /home/ubuntu/.openclaw/workspace/tmp/headtrack \
  --variants stock old python v2 lab --fifo

uv run --offline -q --with unicorn==2.1.1 --with capstone==5.0.3 --with numpy \
  python tools/emu/headtrack_analysis.py \
  /home/ubuntu/.openclaw/workspace/tmp/headtrack \
  --export /home/ubuntu/OpenHuilian/tools/headtrack/results.json

python3 tools/headtrack/build.py \
  --out /home/ubuntu/.openclaw/workspace/tmp/headtrack \
  --cc /home/ubuntu/.openclaw/workspace/tmp/oh-toolchains/usr/bin/arm-none-eabi-gcc
```

The default matrix omits optional sine/negative-wrap extensions; reproduce
those with `--scenarios sine_0.25 sine_0.9 sine_1 sine_1.1 sine_4 wrap_negative`.
The `--rate` option changes the stimulus rate, not the firmware's configured
dt; use it for sensitivity tests, not as an automatic filter-rate adjustment.
For focused decompilation, run `recover.py --elf <firm.elf> --out <existing-dir>`
under the installed PyGhidra interpreter with `GHIDRA_INSTALL_DIR` set.

If the user elects to do a hardware experiment, the bounded trial is:

1. Keep the known-good original `.up` and a proven recovery path. Use exactly
   build 2607061716; confirm 240 Hz ODR and default filter mode 0 if runtime
   settings differ. Do not layer the old head-tracking patch on top of v2,
   or combine other cave patches without checking hooks/RAM/layout.
2. Run all offline commands above and require seven tests plus the partition/
   prompt checks to pass. This does NOT qualify the image for hardware safety;
   repartitioned OTA behavior remains untested on a real updater.
3. **User action only:** flash the generated `v2.up`, not `v2-lab.up`, with
   `tools/hl ota` (try `--side one` first), which sends the image as built. Do
   NOT use the StarFun app's local-file OTA path: it copies the bud's current
   TONE/EQ2P into the image at their stock addresses, which corrupts any
   repartitioned image (v2 moves them). No flashing commands were executed or
   tested in this investigation.
4. Leave the buds still for at least 1 s after tracking starts, then compare
   stock versus v2 at both 10 dps/80 degrees and .5 s/90-degree turns, all three
   axes, return to neutral, +/-180 crossings and looking up. Test each single
   bud, both buds and master switching. Record startup offset and 2-minute drift.
5. Stop and restore the known-good image via the user's recovery procedure if
   axes invert, tracking drops, playback glitches, roles stop syncing, or drift/
   offsets worsen. A fusion-only improvement can still leave large stock
   Euler/report errors; do not interpret it as a complete spatial-audio fix.

Required hardware evidence for release is a time-aligned jig/phone HID capture:
measure real ODR/FIFO age, sample-to-packet age, receiver timestamp interpretation,
rigid axis mapping, velocity units, left/right selection and peer staleness.
Until then the direct-quaternion patch is a lab artifact, not a recommended OTA.
