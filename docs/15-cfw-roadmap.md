# 15 · Custom-firmware roadmap and open questions

What's done, what's open, and what's needed before writing anything to an H3Pro Max3.

## Status board

| Building block | Status | Evidence |
|---|---|---|
| Exact device identity + OTA request | done | [01](01-device.md) |
| `.up` container format | done | [04](04-up-format.md), vendor source [12](12-shenju-flasher.md), 3 independent parsers agree |
| All checksums (CRC16/CCITT-FALSE, CRC8/Maxim) | done | [05](05-crc-and-integrity.md) |
| Bluetooth OTA wire protocol | done (from app source) | [06](06-bt-ota-protocol.md) |
| Image signature / encryption | none. H3Pro OTAP + bootloader read: CRC-only | [05](05-crc-and-integrity.md), [17](17-firmware-internals.md) |
| Firmware memory map / disassembly | done (FIRM, OTAP, bootloader) | [17](17-firmware-internals.md) |
| Repack prompts (TONE) | done, round-trip verified | [07](07-tone-sfx.md) |
| Repack EQ (EQ2P) | done, round-trip verified | [08](08-eq2p-senc.md) |
| Read PSMP NV store | done (read-only) | [09](09-psmp-nvds.md) |
| Write PSMP NV store | blocked: record check algorithm unknown | [09](09-psmp-nvds.md) |
| ANC/transparency filters | code-level (in FIRM), not data | [11](11-anc-transparency.md) |
| AAP improvements | code-level, a few 2-byte data tweaks | [10](10-aap-airpods.md) |
| **A 377H3 / H3Pro base image** | **done** — read off the buds, CRC-valid (chip-name header field unknown) | [16](16-live-flash-dump.md) |
| Read-back / verify path over Bluetooth | done (read-only, via the app's socket) | [16](16-live-flash-dump.md) |
| Physical recovery path for buds | unknown (UART boot ROM likely, unverified) | [12](12-shenju-flasher.md) |
| On-device acceptance of a modified image | rules known from code (CRC only), not tried on hardware | [17](17-firmware-internals.md) |

## The path, in order

1. **Base image**: done. Read off the buds with `C0 83` ([16](16-live-flash-dump.md)).
2. **Container check**: done. `HLKJ` body, index at `0x3000`, same partition
   names, all CRCs valid; `tone_tool.py list/verify` and `psmp_tool.py` run unchanged.
3. **Data-only mods first**: TONE prompts, EQ2P profiles. Zero code changes, CRC-only, and the
   original image is the recovery path.
4. **Flash via the app's own transport**, not a hand-rolled client: StarFun already has the dormant
   local-file OTA path (`chooseFile` → `BtOtaHelper`) in [02](02-starfun-app.md). Wiring a button to
   it is a one-line smali/Java patch. The app flashes L then R and handles reconnects.
5. Only then: code-level work on FIRM (AAP model bytes, XAPL features, ANC listen-mode handling,
   transparency filters). Note the H3Pro Max3 is a **1 MiB** part with almost no free flash
   ([16](16-live-flash-dump.md)) — the ~1 MiB spare region only exists on the 2 MiB H2S-class devices.

## Risks that stay real

* **A wrong image bricks a bud.** The SL6801 catalog images must never be sent to H3Pro
  hardware. Buds have no USB; the mask-ROM recovery documented for SL680x is UART/USB and
  unverified for this chip.
* A failed update doesn't roll FIRM back. OTAP restores the old index, but FIRM is already
  erased. Getting back depends on the bud staying in OTAP so you can retry ([17](17-firmware-internals.md)).
* OTAP doesn't bounds-check write addresses. Never send anything below `0x4000`.
* The BT command channel has a keyed challenge/response (native lib) before `C0` commands are
  accepted; the app does this for you, a custom client would have to reproduce it.
* PSMP is where pairing/`authorization_code`/ear side live; don't touch it until the record
  check is understood (or let the device regenerate it).

## Research still open

- [ ] 4-byte PSMP record check algorithm ([09](09-psmp-nvds.md))
- [ ] Disassemble `COM.dll` + `cal_frequent_drift_gyro_ur.bin` for the UART boot-ROM protocol
- [ ] Extract `encryptData` / challenge-response from StarFun's native lib into Python
- [ ] Does FIRM honour EQ2P pages 51–57 if present? (needs a live device or code read)
- [ ] Which EQ2P profile binds to transparency vs. ANC-on
- [x] Is H3Pro's TONE/EQ2P/PSMP layout identical to SL6801's — TONE and PSMP yes; EQ2P is a new
      7-profile `SLEQ 02 07` layout ([16](16-live-flash-dump.md))
- [ ] What goes in the `.up` header's chip-name field for 377H3 (`H3Pro`? `SL68xx`?). Only matters for the desktop flasher; the buds never see it
- [x] Disassemble the live H3Pro OTAP for its acceptance rules: CRC16 only ([17](17-firmware-internals.md))
- [ ] Who sets/clears the `0x55AA` boot-to-OTAP flag ([17](17-firmware-internals.md))
- [ ] Meaning of EQ2P params `0x3C–0x41` (page 0 compressor block?) and `0xFC`
- [ ] Periodic watcher on the `h3promax3` OTA endpoint
