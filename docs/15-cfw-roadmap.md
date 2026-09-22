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
| **A 377H3 / H3Pro base image** | **missing** — the gating item | [03](03-ota-catalog.md) |
| Physical recovery path for buds | unknown (UART boot ROM likely, unverified) | [12](12-shenju-flasher.md) |
| On-device acceptance of a modified image | unverified on any TWS device | — |

## The path, in order

1. **Get a genuine `h3promax3` `.up`.** Options: (a) wait for StarFun to publish one (poll the
   exact request in [01](01-device.md); 204 → nothing yet); (b) a reseller/377Youth channel;
   (c) read flash off the live buds via the `C0 83` flash-read command the app already uses for
   EQ2P/TONE ([06](06-bt-ota-protocol.md)) — untested for FIRM-sized reads and needs the keyed
   command-channel handshake.
2. **Confirm the container matches** (`CONFIG`, chip mark string, `HLKJ` table, CRCs) with
   `tools/tone_tool.py list` — it should just work if conventions carried over.
3. **Data-only mods first**: TONE prompts, EQ2P profiles. Zero code changes, CRC-only, and the
   original image is the recovery path.
4. **Flash via the app's own transport**, not a hand-rolled client: StarFun already has the dormant
   local-file OTA path (`chooseFile` → `BtOtaHelper`) in [02](02-starfun-app.md). Wiring a button to
   it is a one-line smali/Java patch. The app flashes L then R and handles reconnects.
5. Only then: code-level work on FIRM (AAP model bytes, XAPL features, ANC listen-mode handling,
   transparency filters), with the ~1 MiB free flash region as room to grow.

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
- [ ] Is H3Pro's TONE/EQ2P/PSMP layout identical to SL6801's
- [ ] Periodic watcher on the `h3promax3` OTA endpoint
- [ ] 52bluetooth re-check for `377H3` every few months ([14](14-52bluetooth.md))
