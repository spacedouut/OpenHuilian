# 21 · Night-shift deep pass: ROM surface, AES, EQ2P answers, catalog sweep

Second-pass analysis done overnight with Ghidra 12.2 (headless, PyGhidra scripts) on top of
docs [17](17-firmware-internals.md)/[18](18-firm-walkthrough.md). Everything here is static
analysis of files already in the repo or inside the StarFun APK; nothing touched hardware.
Raw outputs live in `~/tmp/oh-dump/` on the analysis box; the durable results are below and
in `data/analysis/night-shift-findings.md`.

## What's new here vs. 17/18

1. The mask ROM is a **library**, not 4 functions.
2. FIRM ships a **software AES** (docs 05/15 said no crypto markers - there is one).
3. The EQ2P "pages 51-57" open question is answered for this build.
4. The StarFun native `encryptData` is confirmed to be the same LFSR the repo already
   implements - open item closed.
5. The Shenju `COM.dll` UART boot-ROM frame format is decoded (first time).
6. The APK's `zero_ota.bin` is a full service firmware with a CLI.
7. A scripted sweep of all 24 catalog images + the OpenPod dump (new tool `tools/upparts.py`).

## The mask ROM surface: 467 call targets

A direct-BL sweep (capstone, Thumb-2) over FIRM/OTAP/BOOT plus the decompiled-C
`func_0x…`/`thunk_EXT_FUN_…` references gives **467 distinct mask-ROM call targets** from
FIRM alone. Docs 17/18 document ~10 of them. The heavy hitters:

| ROM addr | calls | what |
|---|---|---|
| `0xB6D8` / `0xB6C4` | 278 / 218 | enter / exit critical section (the documented pair) |
| `0xB2A` / `0xBAA` / `0xC54` | 235 / 231 / 163 | memcpy / memset / memcmp |
| `0xB78C` | 110 | sleep N ms |
| `0x4B29C` | 121 | BT stack helper (A2DP/RF glue) |
| `0x1A90` | 90 | queue/event post |
| `0x11044` / `0x110C0` | 80 / 52 | BT host helpers |
| `0x48268` | 63 | flash helper |
| `0xC70` / `0xC74` | 57 / 56 | malloc / free |
| `0x2A7C` | 76 | timer/queue helper |
| `0xB534` / `0xB514` | 60 / 55 | flash read/write wrappers (used by `FUN_0080576c`) |
| `0x9E3C` | 58 | RTOS helper (called from task creation) |
| `0x404132` | 42 | audio/DSP helper |
| `0xC0DC` / `0xC096` | 25 / 19 | printf family (debug prints) |

The `0x11000`-`0x31000` band is called from the BT stack code: large parts of the vendor BT
stack live in mask ROM and only the glue is in FIRM. For CFW that's good news - patched code
can call the same ROM services FIRM does. Full table: `data/analysis/night-shift-findings.md`
companion `rom_surface.txt` (kept out of git; regenerate with the sweep scripts).

## FIRM contains a software AES

`docs/05` searched for AES/SHA/RSA markers and found none - but the AES S-box is sitting at
**FIRM `0xC4BFC6`** (byte-verified), with a second table at `0xC4C0E7`, and the AES core is at
the tail of FIRM:

| Address | Role |
|---|---|
| `FUN_00cac12e` | xtime (GF(2^8) ×2, 0x1b reduction) |
| `FUN_00cac106` | AddRoundKey-style XOR loop |
| `FUN_00cac140` | SubBytes / mix step |
| `FUN_00cac1b8` | key schedule (336 B) |

Callers: `FUN_00ca9c84`, `FUN_00ca9f4c`, `FUN_00cab8d8` - they build 16/32/54-byte messages,
consult the battery level, and talk to module 4 (the Apple "air" layer). The Apple
Continuity advertisement template sits at FIRM `0xC4BF58` (`1E FF 4C 00 07 19 01 0E20 75…`),
and the adv builder `FUN_00cab92c` fills the battery nibbles / lid counter / status bytes at
runtime, exactly as [10](10-aap-airpods.md) describes. Working theory: the AES encrypts the
post-pairing Continuity messages with the PSMP `air_adv_key` (16 bytes) - the "16 zero bytes
filled at runtime" in the template are ciphertext, not plaintext. Still no TEA/XTEA/SHA/MD5/RC4
constants anywhere; the CRC32 table at `0xC451F4` is the standard reflected one ([09](09-psmp-nvds.md)).

## EQ2P: what FIRM actually reads (open question answered)

The EQ2P reader is `FUN_00c690e8(profile, kind)` at FIRM `0xC690E8`: it reads the `EQ2P`
partition, walks the per-profile record-count table, and copies records whose 8-byte record
`kind` byte matches into a RAM buffer. It has **exactly one call site** (boot init
`FUN_00c51578`) and it asks for **profile 0, kind 0 only**. Nothing in this build ever
requests kinds 51-57 - the ANC/talk-through pages the app's `Eq2ItemType` reserves are dead
weight for the H3Pro. The filters really are compiled in ([11](11-anc-transparency.md)), and
adding ANC data pages to EQ2P would do nothing on this build.

The other six profiles exist for the `C0 90` EQ-block command and the preset switch
(`eq_preset_cur_num`), which serve from RAM structures filled elsewhere - the boot path only
pre-loads profile 0.

## StarFun native lib: `encryptData` confirmed (open item closed)

The APK (`starfun_2.0.7.016`, downloadable from the OTA CDN **without auth**) carries
`lib/arm64-v8a/libuparser-lib.so`. Its JNI layer:

| JNI export | Native impl |
|---|---|
| `BtUtils.encryptData` | `SmartLinkCore::CLFSR::Encrypt_Data` → `Encrypt_OneByte` |
| `BtUtils.getCrc` | `SmartLinkCore::CLFSR::get_crc` = CRC16/CCITT-FALSE (poly 0x1021, MSB-first) |
| `BtUtils.crc8Maxim` | `SmartLinkCore::CLFSR::crc8_maxim` = CRC8/Maxim (poly 0x31 reflected, 0x8C) |

`Encrypt_OneByte` is byte-for-byte the 16-bit LFSR `tools/huilian/proto.py` already implements:
`s = rotl16(s,1) ^ (s & 0x8000 ? 0xD103 : 0)`, clocked 8× per byte, XOR keystream in place.
So the app's "encryption" is the same obfuscator the firmware uses - `hl auth` already speaks
it. The `docs/15` open item is closed: nothing new to extract, the Python is authoritative.

## Shenju COM.dll: the UART boot-ROM frame format (first decode)

`vendor/shenju-flashloader/COM.dll` (x86, 914 functions decompiled) speaks a `42 52` ("BR")
framed protocol to the mask ROM, then to the RAM loader:

| Frame | Layout | Notes |
|---|---|---|
| sync / hello | `42 52 00 02 <crc16 LE>` | retried up to 150× with 20 ms timeout |
| write RAM | `42 52 02 87 <addr LE24> 80 00 <128 B data> <crc16 LE>` | CRC over the 0x87 bytes after `BR` |
| run RAM | (same family, addr = entry) | then `connect_startup` re-syncs with the loader |
| write flash | `42 52 05 00 <addr LE24> 00 04 <1024 B data> <crc16 LE>` | 1 KiB chunks |
| chip erase | `42 52 08 06 00 00 00 00 <sum16 LE>` | checksum is a plain **byte sum**, not CRC16 |

Chunking: RAM writes go in 128-byte pieces, flash writes in 1 KiB pieces, both driven by the
Python (`flash_uart_6801.py`) around the DLL. The loader side (`cal_frequent_drift_gyro_ur.bin`
loaded at `0x850000`) is a 197-function program with fault-dump strings (`CPU0_ADDR`, `PC 0x…`)
and its own command dispatch - the loader internals are still only partially mapped, but the
PC-side frame format above is the part needed to build an open-source UART flasher.

## `zero_ota.bin`: the app ships a full service firmware

`assets/zero_ota.bin` inside the StarFun APK (204,728 B) is a complete Cortex-M program:
SP `0x86A4A4`, entry `0x804C41` (same RAM-entry convention as OTAP), 674 functions. Strings
show what it is: a **POSIX-style service/dev firmware** - a CLI shell (`CLI_HALT`, `Enable echo`,
`syntax error`), device files (`/dev/key`, `/dev/rtc`, `/dev/timer`, `/dev/tp`, `/dev/pmu`,
`/dev/uart2`), FatFS (`f_mount`, `f_findfirst`), SDMMC, touch panel, USBD, dual-core PLL
reporting, PMU/VBUS events, the PSM/NV store (`no enough memory for psm write`,
`authorization_code`), and `update set pc and restart` / `update set sd and restart` paths.

That makes it the vendor's recovery/maintenance image, and the app distributes it. If it can
be pushed over the `55AA` OTA transport (same as any CRC-valid image), it is a candidate
safety net: a bud running zero_ota has a CLI and USB/SD update paths instead of a dead
FIRM. Unverified on hardware - treat as a lead, not a plan.

## Catalog sweep (24 images + OpenPod dump)

New tool `tools/upparts.py` (the generic partition lister/extractor/strings dumper the tools
README listed as missing) ran over every image. Per-image reports with unique-string diffs
against the H3Pro and both h2sturbo references were generated on the analysis box. The
feature-relevant findings:

**In other builds, missing from H3Pro 2607061716:**

| String | Builds | Read |
|---|---|---|
| `transparency_adaptive_enable` | 7 | NV key for adaptive transparency - a feature the H3Pro build lacks |
| `transparency_param` | 3 | transparency tuning block |
| `air_hangup_setting` | 10 | another `air_*` AAP setting |
| `audioRoutingRequestID2` | 19 | audio-routing hook |
| `space_open.mp3` / `space_hold.mp3` | 2 | spatial-audio prompts (H3Pro only has `space_close.mp3`) |
| `version_error.mp3` | 3 | a prompt for version-mismatch rejection |
| `hardware EQ config to %d. // 0: None, 1: pop, 2: rock…` | 1 | named hardware EQ presets |
| `sensor motion active timer` | 5 | motion tuning timer |

**H3Pro-exclusive in this collection:** the heart-rate-over-AAP stack (`HeartRate`,
`HeartRateService`, `com.apple.hid.heartrate-access`, `air heartrate tx timer`,
`vc30fx_oscclk_freq`), the `H3Pro2` / `H3Pro3` / `377Super PRO3` / `Super2026+` model names,
and the `20230713_70aa57dc` build stamp.

The OpenPod `GN438_sl6801_fulldump.bin` is an MP3-player firmware (music/ebook/picture UI,
7,540 strings) - same silicon, different product; useful for PSMP/bootloader comparison only.

## OTAP audit (confirmation)

The OTAP state machine `FUN_0080e770` handles exactly `80`, `81`, `82`, `83`, `84`, `04` -
no hidden commands. Matches [17](17-firmware-internals.md).

## Function-recovery note

Ghidra 12.2 auto-analysis finds 3,864 FIRM functions vs. the 4,512 in the original
(ReVa-assisted) analysis. A recovery pass that creates functions at every branch target and
Thumb pointer reference added 44 FIRM / 20 OTAP / 1 BOOT functions, including the receive
demux `FUN_00c4f0cc` and the C0 part-2 dispatcher `FUN_00c52e4c` that docs 18 cites (they are
reached only indirectly, so auto-analysis misses them). The scripts live in
`~/tmp/oh-scripts/` on the analysis box: `oh_dump_lib.py` (full decompile + strings + xrefs +
callgraph + ROM surface), `oh_fixfuncs.py` (function recovery), `oh_mkfunc.py` (create +
decompile at explicit addresses), `romscan.py` (capstone BL sweep), `catalog_sweep.py`
(per-image reports).

## What this changes for CFW

* The AES finding means the Apple Continuity layer is *cryptographically* alive: spoofing the
  pop-up model bytes ([10](10-aap-airpods.md)) is still a 2-byte edit, but anything that
  touches post-pairing advertisement content has to go through the AES path with the real
  `air_adv_key`.
* EQ2P kinds 51-57 are confirmed dead on this build - ANC filter work is code patching,
  full stop.
* The ROM surface table makes small code patches much easier: memcpy/memset/malloc/sleep and
  the BT-stack ROM helpers are all callable from patched FIRM code.
* The UART boot-ROM frame format is now known well enough to attempt an open-source
  replacement for the vendor's COM.dll (recovery path for bricked buds, if the test pads
  exist on these buds).
