# Night-shift findings: OpenHuilian deep Ghidra pass

Date: 2026-10-29 (overnight). Analyst: Biscut (Ghidra 12.2 headless, PyGhidra scripts, capstone).
Target: H3Pro Max3 live image 2607061716 (FIRM/OTAP/BOOT), plus vendor/app binaries.
Method: full-program decompile dump (~/tmp/oh-dump/), raw Thumb-2 sweeps (capstone),
function recovery pass (+44 FIRM / +20 OTAP / +1 BOOT functions), string/xref analysis.
Everything below is static analysis of files already in the repo or its APK; nothing touched hardware.

## 1. The mask ROM is a whole library, not 4 functions

Docs 17/18 document ~10 mask-ROM entry points. A direct-BL sweep (capstone) plus the
decompiled-C `func_0x…` references show **431 distinct ROM call targets** from FIRM
(~/tmp/oh-dump/firm/rom_surface.txt), with call counts. Highlights beyond the documented ones:

| ROM addr | calls | guess |
|---|---|---|
| 0x4b29c | 121 | BT stack helper (heavy user: RF/A2DP code) |
| 0x1a90 | 90 | event/timer or queue post |
| 0x11044 | 80 | BT host helper |
| 0x48268 | 63 | flash/flash-cache helper |
| 0x1720 / 0x1724 | 52/54 | enter/exit critical section pair (direct-BL form; docs' 0xB6D8/0xB6C4 pair is the indirect-literal form) |
| 0x404132 | 42 | audio/DSP helper |
| 0x46cc0 | 36 | |
| 0x3d520 | 32 | |
| 0xc0dc / 0xc096 | 25/19 | printf-family (used by debug printfs) |
| 0x128d8 | 25 | |

The 0x11000-0x31000 band is called from the BT stack code - large parts of the vendor BT
stack live in mask ROM, only the glue is in FIRM. Consequence for CFW: you can call these
ROM services from patched code the same way FIRM does.

## 2. FIRM contains a software AES implementation (docs said none)

- AES sbox at FIRM 0xC4BFC6 (verified byte-for-byte), second table at 0xC4C0E7.
- AES core at the tail of FIRM: xtime `FUN_00cac12e` (0x1b reduction), AddRoundKey-style XOR
  `FUN_00cac106`, SubBytes/mix `FUN_00cac140`, key schedule sized fn `FUN_00cac1b8` (336 B).
- Users: `FUN_00ca9c84`, `FUN_00ca9f4c`, `FUN_00cab8d8` - they build 16/32/54-byte messages,
  check battery, and talk to module 4 (the Apple "air" layer).
- The Apple Continuity advertisement template sits at FIRM 0xC4BF58
  (`1E FF 4C 00 07 19 01 0E20 75 ...`), and the adv builder `FUN_00cab92c` fills the
  battery nibbles / lid counter / status bytes at runtime (matches doc 10's layout).
- Working theory (strong): the AES is the encryption for Apple proximity-pairing /
  continuity follow-up messages using the PSMP `air_adv_key` (16 bytes). The "16 zero bytes
  filled at runtime" in the template are filled with ciphertext, not plaintext.
- No TEA/XTEA/SHA/MD5/RC4 constants anywhere in FIRM. CRC32 table confirmed at 0xC451F4
  (standard reflected CRC32, matches doc 09).

## 3. New build-identity strings in H3Pro FIRM (not in docs)

- `20230713_70aa57dc` at FIRM 0x42BB95+0xC04000... (string offset 0x02BB95) - looks like a
  vendor SDK/library build stamp (date_hash).
- `H3Pro2` and `H3Pro3` model names at 0x040D93/0x040D9A - the model-string table knows two
  more H3Pro variants that doc 18's table doesn't list.
- `com.apple.hid.heartrate-access` (x2, 0x047D5F/0x047DA3) - the buds expose Apple's
  heart-rate-access HID service (the thing AirPods Pro 2 use for heart-rate sharing with
  Apple Watch). Doc 10 (h2sturbo-based) doesn't mention it. The H3Pro has a VC30Fx HR sensor
  and a `sensor-hr` task, so this is likely a real, working feature.
- AAP identity plist (0x045B49): MaxReportSize 182, SerialNumber base64
  `R1dYWkZLSjZKUUgzAA==` = `GWYZLKJ6JQH3\0`, CFG# base64 `QjI5OC9SUi9SMDAxL1ZWLwA=` =
  `B298/RR/R001/VV/`. Different CFG# than the h2sturbo build (doc 10).

## 4. EQ2P consumption in FIRM (answers an open question)

The EQ2P reader is `FUN_00c690e8(profile, kind)` (FIRM 0xC690E8): reads the EQ2P partition,
walks the profile record-count table, and copies records whose 8-byte record kind byte
matches `kind` into a RAM buffer. Exactly ONE call site exists (boot init `FUN_00c51578`):
`FUN_00c690e8(0, 0)` - **profile 0, kind 0 only**. Nothing in this build requests kinds
51-57 (the ANC/talk-through pages the app reserves). So: shipping ANC filter data in EQ2P
pages 51-57 would be dead weight for this build - the filters really are compiled in.

## 5. Command surface

- The receive demux `FUN_00c4f0cc` (recovered - it was one of the functions auto-analysis
  missed) matches doc 18: C0/05/55 -> StarFun handler, E0 and A0..AF dropped, else `+test=`.
- C0 part-2 dispatcher `FUN_00c52e4c` (also recovered) matches doc 18's table; additionally
  confirmed opcodes 0x67/0x68 write handlers post events, 0x85 calls FUN_00ca9610.
- The `05`-frame path: first-byte `05` frames are the **TWS peer (bud-to-bud) protocol**, not
  a phone channel - OTAP's peer handler checks `05 <op> 00 …` frames and FIRM routes them to
  module 7 type 1 (same transport family as the peer-sync opcodes in docs/18). The app side
  has a separate second protocol (`constructCmd`: 16-byte header with cmdId 0x8001/0x8002,
  divideType, offset, crc32 - getBiuShakeHandsCmd/getBiuVerifyCmd) for OTHER Huilian products
  (watches); no Biu/JSON strings exist in H3Pro FIRM, so on the buds that channel is almost
  certainly inert. Worth one live probe someday.
- Module dispatch: two dispatcher tables (`FUN_00827564` table base 0x831e7c,
  `FUN_00c2ab6c` table base 0xc2ab94's target), 9 modules each, registered via
  `FUN_00c9e66c(module, handler)` - registrations found for modules 1, 2, 6; module 7
  (SPP/UART transport) and module 4 (air) handlers are registered elsewhere/differently.

## 6. Mask-ROM call rendering note

ROM calls appear in decompiled C as `func_0x00000xxx`. Docs' 0xB6D8/0xB6C4 critical-section
pair and 0xB78C sleep don't appear as direct BL targets in this build; the direct-BL pair
is 0x1720/0x1724. Both may be true (direct vs literal-pool indirect calls).

## 7. Tooling added

- `tools/upparts.py` - the generic .up partition lister/extractor/strings tool the repo
  listed as missing. Verified against doc 04's h2sturbo numbers and the H3Pro image.
- Ghidra 12.2 headless project at ~/tmp/oh-ghidra/proj (firm.elf/otap.elf/boot.elf,
  ARM:LE:32:Cortex), PyGhidra dump/recover scripts in ~/tmp/oh-scripts/.
- ReVa (mcp-reva) installed but has no Ghidra 12.2 extension build yet (latest is 12.1.3);
  script-driven headless used instead.

## 8. APK assets (downloaded without auth from the OTA CDN)

- `starfun_2.0.7.016` APK pulls with no auth from the catalog URL. Native libs extracted.
- `libuparser-lib.so` (arm64) contains the JNI implementations: `BtUtils_encryptData`,
  `BtUtils_getCrc`, `BtUtils_crc8Maxim`, plus the uparser ANC/EQ math (analysis pending).
- `assets/zero_ota.bin` (204,728 B) is a Cortex-M program: SP 0x86A4A4, entry 0x804C41,
  same RAM-entry convention as OTAP, contains an "ASCII" string near the end. Likely the
  factory/zero-OTA test image the app can push. Analysis pending.
- `assets/demo.eq2` (608 B) is a SLEQ v2 1-profile EQ table (the app's demo EQ).

## 9. OTAP-mode C0 command set (new)

OTAP's own C0 dispatcher `FUN_00810914` (1,196 B) answers: 01/02 (full app auth), 04 (model),
05 (version), 06 (BT addr), 07 (device_id), 09 (battery), 10 (side), 11, 12 (link state), 13,
50/51/53/54, 60/61, 63/64, 83 (flash read, 200 B cap). Bigger than the empirically observed
subset in docs/20 - recovery tooling can authenticate and read everything in OTAP mode.

## 10. Bootloader: one binary, 3 config bytes

First 0x3000 bytes byte-identical across all 25 images EXCEPT 0x1D/0x5C/0x5D, which split
1 MB-class (00 8C 0F) from 2 MB-class (04 7C 40). fit30 (2022) == H3Pro (2026) bootloader.
Flash class is data, not code.

## 11. Module map + AAP region (new)

- Module registrations via FUN_00c9e66c(handler, module): modules 1 (BT host, x2), 2 (NV/PSM),
  3, 4 (air/AAP -> FUN_00c54da8), 5, 6 (audio), 7 (SPP/UART -> FUN_00c53260). Two dispatch
  APIs (FUN_00827564, FUN_00c2ab6c) over one 9-entry table at RAM 0x831E7C.
- Module 7 handler FUN_00c53260 cases: 0 = C0 part-2 dispatcher (FUN_00c52e4c), 2 = OTA path,
  3 = reply send, 4 = name/string access.
- AAP region: L2CAP event dispatcher FUN_00ca8c04 (PSMs 0x1001/0x1007/0x1F), connection
  state machine FUN_00cabe28, adv builder FUN_00cab92c, senders FUN_00c87724/760/798
  (header bytes 0x20/0x40/0x10), ear-to-ear sync parser FUN_00c87834 (types 0x10-0x50).
  Phone-facing AAP opcode table: NOT located this pass - top follow-up.
- SENC applier = FUN_00c65a10 (switch on record kind 0x15-0x1C+, two destination layouts
  selected by a mode flag); SENC reader shares the EQ2P staging buffer. Records with
  kind >= 0xFF (e.g. 0xFC) are skipped by the reader.
- Dispatcher event ids resolved from literal pools: 0x80000016/17/19/20, 0x80010016/17,
  0x8100003a, 0xb0000010/13, 0xb2000001/2/3, 0xc0300021, 0xc1000001/4, 0xd000000b/1b/2b/2e,
  0xd1000001, 0xd2000001/2/7/8/9/e, 0xf2000011/17, 0xf600000e/0f/46, 0xf7000003.
- Head-tracking patch offsets re-verified byte-exact against the raw image
  (tx_ms@0xA7550=40, decimate@0x64A1A=3, alpha@0x64C74=0.1).
- +test= command set is complete at 8 commands: recover, version, shutdown, encen, encdis,
  getaddr, pair_, vbusp:.
- Model-name table in the C0 03 handler: H2S Ultra, H2S Turbo, H3sProMax, H3Pro2, H3Pro3,
  377Super PRO3, Super2026+ (docs/18's table missed H3Pro2/H3Pro3).

## Still open (for the next pass)

- Loader internals (cal_frequent_drift_gyro_ur.bin @0x850000, 197 fns) - the loader-side
  command dispatch after connect_startup.
- COM.dll response parsing + baud-rate negotiation details.
- Whether OTA frames are accepted without the C0 01/02 auth handshake (needs hardware).
- EQ2P params 0x3C-0x41 (page-0 compressor block) and 0xFC - consumer not traced.
- Which EQ2P profile binds to transparency vs ANC-on (H3Pro has 7 profiles; binding logic
  not traced).
- Semantic confirmation of the AAP opcode table labels (needs live iOS traffic or deeper
  sub-handler reads; the dispatch structure itself is solid).
