# Docs audit against tools and data (Nov 2026)

What the reorganized docs (#15) claim, checked against the code and the checked-in firmware/data.
Everything here was run offline; no buds, phone, or StarFun server were involved.

## Corrected in this change

| Page | Was | Now (source) |
|---|---|---|
| how-to/dump-firmware.md | `--chunk` "can only make that smaller" than 200 | default 100, accepts 1..200 (`tools/huilian/cli.py` `cmd_read`) |
| reference/eq2p-senc.md | EQ2P records start at offset 26 | header size is the u16 at offset 8: 50 in h2sturbo, 28 in H3Pro; offset 26 decodes garbage (`data/partitions-h2sturbo/eq2p_h2sturbo.bin`, `docs/how-to/edit-eq.md` script) |
| reference/up-format.md | OTAP "exactly 167,248 B in all 24 images" | 22/24; `fit30_2209242029` and `fit50_2210141125` have 166,816 B |
| reference/up-format.md | TONE 83–94 KB | 32,971–103,860 B across the catalog, 84,903 B in H3Pro |
| reference/up-format.md | EQ2P ~1.5 KB | 648–1,562 B across the catalog, 4,172 B in H3Pro |
| reference/up-format.md | partition CRCs match 24/24; `a10_2311090955_RYEQ` has correct partition CRCs | 23/24: that image's FIRM CRC is stale too (stored `0xE63A`, computed `0xD620`; container stored `0xEC7F`, computed `0x4A69`), per `tone_tool.py verify` |

No case where the doc was right and the code wrong.

## Verified (matches)

* **`hl`** (`tools/hl` → `tools/huilian/cli.py`; there is no `tools/hl.py`): subcommands `auth info get set read ota leave-ota dash cmd tone patch`, `--port/-p`, `--baud`, `ota --side both|one` (default both), `--resume`, `--timeout 3.0`, `dash --listen` default `127.0.0.1:8765`, settings names used in tutorials/how-to (`anc_mode` etc.).
* **`tone_tool.py`** `list/extract/verify/replace … -o`: H3Pro TONE at `0x0AF000`, 84,903 B, 18 files packed to the byte, CRC `0x6386`; per-file formats in reference/tone.md (incl. `low_power.mp3` = 8 kHz PCM WAV, `key_up.mp3` = WAV); h2sturbo slack before EQ2P 2,873 B.
* **`cfw.py`** `info` / `apply … --set` / `--chip`: partition table printed in docs matches; head-tracking knobs (`tx_ms` 40→20, 10..100; `decimate` 3→1, 0..15; `alpha` 0.1→0.3, 0.05..1.0) match `patches/2607061716/head-tracking.json`; the how-to's `--set tx_ms=25 --set alpha=0.4` is in range.
* **`flashota.py`** `plan/send/selftest`, `--stock --side L|R --frames --yes --resume`: `selftest OK`; plan frame layout (`80 81 82 83 84 04`, 512-byte chunks, 1,648 write frames `0x4000..0xD2000`, `82` CRC over `0x3000..0xD2000`) matches reference/ota-protocol.md.
* **`.up` format** vs `tools/upfmt.py` / `build_up.py`: `CONFIG` magic, 0x100 header, body length/CRC at 0x10/0x14, CRC16/CCITT-FALSE, index pointer at body+0x20, `<4sIII>` entries at idx+16+16·i, PSMP not stored; `build_up.py` on a 1 MiB dump reproduces the committed H3Pro `.up` byte for byte. OTA guards (index 0x3000, FIRM 0x4000, OTAP ≥ 0x10000 and 4 KiB aligned) match the docs.
* **Catalog** (24 `.up`): chip `SL6801` in all, distinct FIRM 24 / OTAP 23 / SENC 11 / TONE 10 / EQ2P 10 / SEN2 2, sizes 1,027,232 / 1,027,664 / 2,076,240 B, h2sturbo index table, zero padding `0xD2000..0x1D2000`, container CRC 23/24, FIRM wrapper byte 0 = 0x30.
* **H3Pro layout**: FIRM/SENC/TONE/EQ2P/OTAP/PSMP addresses, lengths, CRCs; gaps TONE→EQ2P 1,113 B, EQ2P→OTAP 53,172 B, OTAP→PSMP 4,784 B; flag page `0xFB000` (`AA 55`) as in `tools/flashmap.py`.
* **EQ2P**: H3Pro `SLEQ` v2, 7 pages, header 28, counts 92/71×6; h2sturbo factory 11-band table (freq/Q/gain); `edit-eq.md` script runs and the result verifies.
* **PSMP**: `psmp_tool.py` on the OpenPod dump: 73 records, log end `0x82F`, 0 bad CRC32 (`0xEDB88320`, init 0).
* **Command bytes**: `C0 83` read (LE addr, len), `C0 85/86/87` write-only toggles, `C0 05/12/13`, `534C` verify code against the decompiled app (`reference/starfun-app/2.0.7.016`); dashboard `58/68`, `56/66`, `57/67`, SPP ch 3, HFP ch 1 against `tools/huilian/dash.py`.
* **Panel/WebUI**: `tools/panel/server.py --port/--bind/--http` (8765); `tools/webui` is static files served with `python3 -m http.server`.

## Not verified

* Anything that needs hardware or the network: live `hl` output, OTA success, `leave-ota` unsticking, WebUI over Web Serial, `pull_ota.py` (needs `STARFUN_USER`/`STARFUN_PASS`), `flashdump.py` via Frida/ADB.
* `patchota.py` and `compmatch.py`: named in the ticket but not in the repo; no doc references them.
* Firmware-internal addresses in docs/research (function/RAM addresses, ROM entry points, AES/key notes, low-volume-noise and updater erase-span claims): need Ghidra/Unicorn (`unicorn` not installed here); not re-derived.
* `smartlink_flash/fwhelper` results and OpenPod `B27_251112.up` claims (vendor tool not run).

## Authors

* Docs edited: `reference/up-format.md`, `reference/eq2p-senc.md` (blame: spacedouut / Asher Riggins), `how-to/dump-firmware.md` (Asher Riggins, a few lines Devin AI). The reorganization PR #15 is authored by Asher Riggins (spacedouut) with one Devin AI commit.
* Code checked: `tools/upfmt.py`, `tools/huilian/cli.py`, `tools/huilian/dash.py`, `tools/flashota.py` (Asher Riggins, one Devin AI commit each), `tools/cfw.py` (Asher Riggins), `tools/tone_tool.py`, `tools/build_up.py` (Asher / spacedouut).
