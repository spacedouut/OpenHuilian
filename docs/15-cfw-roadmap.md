# 15 · Custom-firmware roadmap and open questions

What's done, what's open, and what to keep in mind before writing anything to an H3Pro Max3.

## Status board

| Building block | Status | Evidence |
|---|---|---|
| Exact device identity + OTA request | done | [01](01-device.md) |
| `.up` container format | done | [04](04-up-format.md), vendor source [12](12-shenju-flasher.md), 3 independent parsers agree |
| All checksums (CRC16/CCITT-FALSE, CRC8/Maxim) | done | [05](05-crc-and-integrity.md) |
| Bluetooth OTA wire protocol | done, verified on real buds | [06](06-bt-ota-protocol.md), [20](20-hl-cli.md) |
| Image signature / encryption | none. H3Pro OTAP + bootloader read: CRC-only. FIRM's software AES is for Continuity adverts | [05](05-crc-and-integrity.md), [17](17-firmware-internals.md), [21](21-night-shift.md) |
| Firmware memory map / disassembly | done (FIRM, OTAP, bootloader) | [17](17-firmware-internals.md) |
| Repack prompts (TONE) | done, round-trip verified, flashed to real buds | [07](07-tone-sfx.md) |
| Repack EQ (EQ2P) | done, round-trip verified | [08](08-eq2p-senc.md) |
| Read PSMP NV store | done (read-only) | [09](09-psmp-nvds.md) |
| Write PSMP NV store | done offline (record check = CRC32), untried on hardware | [09](09-psmp-nvds.md) |
| ANC/transparency filters | code-level (in FIRM), not data | [11](11-anc-transparency.md) |
| AAP improvements | code-level, a few 2-byte data tweaks | [10](10-aap-airpods.md) |
| **A 377H3 / H3Pro base image** | **done** — read off the buds, CRC-valid (chip-name header field unknown) | [16](16-live-flash-dump.md) |
| Read-back / verify path over Bluetooth | done (read-only), via the app's socket or `hl read` | [16](16-live-flash-dump.md), [20](20-hl-cli.md) |
| Physical recovery path for buds | unknown. UART boot ROM likely, PC-side frames decoded, pins unidentified, untested | [12](12-shenju-flasher.md), [21](21-night-shift.md) |
| On-device acceptance of a modified image | done. CRC only, and patched images flashed fine on real buds | [17](17-firmware-internals.md), [20](20-hl-cli.md) |
| Entering / leaving the updater | known: FIRM sets the `0x55AA` flag on `80`, OTAP clears it on `04`. Recovery for stuck buds is `hl leave-ota` | [06](06-bt-ota-protocol.md), [17](17-firmware-internals.md), [20](20-hl-cli.md) |
| App auth handshake | done. 16-bit LFSR, reimplemented in `tools/huilian` | [18](18-firm-walkthrough.md), [20](20-hl-cli.md) |
| Binary patches to FIRM | done. `cfw.py` + version-pinned patch files, head-tracking patch flashed | [19](19-cfw-patching.md) |

## The path, in order

1. **Base image**: done. Read off the buds with `C0 83` ([16](16-live-flash-dump.md)).
2. **Container check**: done. `HLKJ` body, index at `0x3000`, same partition
   names, all CRCs valid; `tone_tool.py list/verify` and `psmp_tool.py` run unchanged.
3. **Data-only mods first**: TONE prompts, EQ2P profiles. Zero code changes, CRC-only, and the
   original image is the recovery path.
4. **Flash**: done with [`tools/hl ota`](20-hl-cli.md), which speaks the app's `55AA` transport
   over a plain RFCOMM socket, flashes both buds and doesn't touch your EQ2P/TONE. StarFun's
   dormant local-file OTA path (`chooseFile` → `BtOtaHelper`, [02](02-starfun-app.md)) should also
   work after a one-line patch (untried), but it copies the bud's current EQ2P/TONE into your image first,
   which undoes prompt mods. [`tools/flashota.py`](../tools/flashota.py) sends the frames through
   StarFun's socket via Frida, one bud per run, and hasn't been run against a bud.
5. Only then: code-level work on FIRM (AAP model bytes, XAPL features, ANC listen-mode handling,
   transparency filters). Note the H3Pro Max3 is a **1 MiB** part with almost no free flash
   ([16](16-live-flash-dump.md)) — the ~1 MiB spare region only exists on the 2 MiB H2S-class devices.

## Risks that stay real

* **A wrong image bricks a bud.** The SL6801 catalog images must never be sent to H3Pro
  hardware. Buds have no USB; the mask-ROM recovery documented for SL680x is UART/USB and
  unverified for this chip.
* A failed update doesn't roll FIRM back. OTAP restores the old index, but FIRM is already
  erased. Getting back depends on the bud staying in OTAP so you can retry ([17](17-firmware-internals.md)).
  The flag does keep buds in OTAP across power cycles, but a retry after a real CRC failure
  hasn't been tried.
* Every OTA must end with `04` after a good `84`. Skip it and both buds stay in the updater,
  sending it in the wrong state pulls a recovered bud back in ([06](06-bt-ota-protocol.md)).
* OTAP doesn't bounds-check write addresses. Never send anything below `0x4000`.
* PSMP is where pairing/`authorization_code`/ear side live. The record check is known
  ([09](09-psmp-nvds.md)) and OTA never writes PSMP, but a bad direct write still costs you the
  pairing. `hl set` only writes the user-facing keys through `C0`, and nothing here writes raw
  PSMP records to a bud.

## Research still open

- [x] 4-byte PSMP record check algorithm: reflected CRC32 over key, value, masked header; `psmp_tool.py verify/set` ([09](09-psmp-nvds.md))
- [ ] Disassemble `COM.dll` + `cal_frequent_drift_gyro_ur.bin` for the UART boot-ROM protocol.
      The `COM.dll` frame format is done ([21](21-night-shift.md)), the loader is partly mapped
- [x] Extract `encryptData` / challenge-response from StarFun's native lib into Python: the
      native `SmartLinkCore::CLFSR::Encrypt_OneByte` is byte-for-byte the LFSR
      `tools/huilian/proto.py` already implements ([21](21-night-shift.md))
- [x] Does FIRM honour EQ2P pages 51–57 if present? **No** - the only EQ2P consumer in the
      H3Pro build loads profile 0 / kind 0 at boot; nothing requests kinds 51–57 ([21](21-night-shift.md))
- [ ] Which EQ2P profile binds to transparency vs. ANC-on
- [x] Is H3Pro's TONE/EQ2P/PSMP layout identical to SL6801's — TONE and PSMP yes; EQ2P is a new
      7-profile `SLEQ 02 07` layout ([16](16-live-flash-dump.md))
- [ ] What goes in the `.up` header's chip-name field for 377H3 (`H3Pro`? `SL68xx`?). Only matters for the desktop flasher; the buds never see it
- [x] Disassemble the live H3Pro OTAP for its acceptance rules: CRC16 only ([17](17-firmware-internals.md))
- [x] Who sets/clears the `0x55AA` boot-to-OTAP flag: FIRM `FUN_00C6AD1C` on the app's enter-OTA event, OTAP `FUN_0080FE80` at finalize ([17](17-firmware-internals.md))
- [ ] Meaning of EQ2P params `0x3C–0x41` (page 0 compressor block?) and `0xFC`
- [ ] Periodic watcher on the `h3promax3` OTA endpoint
