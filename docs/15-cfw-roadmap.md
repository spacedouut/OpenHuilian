# 15 · Custom-firmware roadmap and open questions

Where things stand, what's proven, and what's still needed before anything could sensibly be
written to a real H3Pro Max3. Nothing has been flashed to any device during this research.

## Status board

| Building block | Status | Evidence |
|---|---|---|
| Exact device identity + OTA request | done | [01](01-device.md) |
| `.up` container format | done | [04](04-up-format.md), vendor source [12](12-shenju-flasher.md), 3 independent parsers agree |
| All checksums (CRC16/CCITT-FALSE, CRC8/Maxim) | done | [05](05-crc-and-integrity.md) |
| Bluetooth OTA wire protocol | done (from app source) | [06](06-bt-ota-protocol.md) |
| Image signature / encryption | none found; bootloader on SL6806 verified CRC-only | [05](05-crc-and-integrity.md), [13](13-open-source-tooling.md) |
| Repack prompts (TONE) | done, round-trip verified | [07](07-tone-sfx.md) |
| Repack EQ (EQ2P) | done, round-trip verified | [08](08-eq2p-senc.md) |
| Read PSMP NV store | done (read-only) | [09](09-psmp-nvds.md) |
| Write PSMP NV store | blocked: record check algorithm unknown | [09](09-psmp-nvds.md) |
| ANC/transparency filters | code-level (in FIRM), not data | [11](11-anc-transparency.md) |
| AAP improvements | code-level, a few 2-byte data tweaks | [10](10-aap-airpods.md) |
| **A 377H3 / H3Pro base image** | **done** — read off the buds, CRC-valid (chip-name header field unknown) | [16](16-live-flash-dump.md) |
| Read-back / verify path over Bluetooth | done (read-only, via the app's socket) | [16](16-live-flash-dump.md) |
| Physical recovery path for buds | unknown (UART boot ROM likely, unverified) | [12](12-shenju-flasher.md) |
| On-device acceptance of a modified image | unverified on any TWS device | — |

## The path, in order

1. ~~Get a genuine `h3promax3` `.up`.~~ **Done** — option (c) worked: the `C0 83` flash-read was
   driven through StarFun's own authenticated socket, sidestepping the handshake
   ([16](16-live-flash-dump.md)). A published OTA would still be valuable as the reference for the
   header's chip-name field.
2. ~~Confirm the container matches.~~ **Done** — `HLKJ` body, index at `0x3000`, same partition
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
* OTA acceptance rules on H3Pro's OTAP/bootloader are unknown (SL6806 checks: magic, mark
  string, timestamp differs, CRC write-verify).
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
- [ ] What goes in the `.up` header's chip-name field for 377H3 (`H3Pro`? `SL68xx`?)
- [ ] Disassemble the live H3Pro OTAP (same 167,248-byte size as SL6801's) for its acceptance rules
- [ ] Meaning of EQ2P params `0x3C–0x41` (page 0 compressor block?) and `0xFC`
- [ ] Periodic watcher on the `h3promax3` OTA endpoint
- [ ] 52bluetooth re-check for `377H3` every few months ([14](14-52bluetooth.md))
