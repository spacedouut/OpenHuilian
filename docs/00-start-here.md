# 00 · Start here

## What this is

**H3Pro Max3** true-wireless earbuds: an AirPods-Pro lookalike on a Bluetooth SoC from
**Huilian (慧联 / HLKJ)**. The same chips are sold as **Smartlink / SL68xx**, and the company behind
them appears to be **Shenju (珠海绅聚 / shenjugroup.com)**. The control app is **StarFun**
(`com.fun.app`), the generic app for Huilian TWS products.

## Glossary

| Term | What it means here |
|---|---|
| **Huilian / 慧联 / HLKJ** | The chip/firmware vendor. `HLKJ` (慧联科技) is the magic string in every firmware body. |
| **Smartlink / SL6801 / SL6806** | Older chip family names. Every image in the public catalog claims `SL6801`. |
| **377 / 377H3 / H3Pro** | Newer silicon generation. The H3Pro Max3 reports chip `H3Pro`; the replica community calls it "Huilian 377H3". |
| **Shenju / 绅聚 / shenjugroup.com** | Company behind the flasher tool and a second OTA server used by StarFun. |
| **StarFun** | The phone app. Its OTA tenant is `yiguo`. |
| **`.up` file** | The firmware container (starts with `CONFIG`). A full image, not a patch. |
| **OTA** | Over-the-air update: the app streams a `.up` to the buds over Bluetooth SPP. |
| **FIRM / TONE / EQ2P / SENC / OTAP / PSMP** | The partitions inside a `.up`. See [04](04-up-format.md). |
| **AAP** | Apple Accessory Protocol. The buds run an "AAP Server" to look like AirPods. |
| **CFW** | Custom firmware. |

## Safety

1. **Flashing works, so be careful with it.** `tools/hl ota` has written stock and
   patched images to real buds ([20](20-hl-cli.md)). Every OTA has to end with `55AA04`, or both
   buds stay in the updater ([06](06-bt-ota-protocol.md)). A failed update doesn't roll FIRM back,
   and there is no tested wired recovery yet ([15](15-cfw-roadmap.md)).
2. **Never flash an SL6801 image to an H3Pro / 377H3 device.** It's a different silicon
   generation. SL6806 has a chip-name check in its bootloader ([13](13-open-source-tooling.md)), but
   the H3Pro doesn't: its updater only checks a CRC ([17](17-firmware-internals.md)), so nothing on
   the bud would stop a wrong image.
3. Modified images need **both** the partition CRC and the outer container CRC recomputed
   ([05](05-crc-and-integrity.md)). One image in the public catalog ships with a stale outer CRC.
4. Credentials aren't in this repo. `tools/pull_ota.py` reads them from environment variables.
5. Don't publish a bud's PSMP. It holds that bud's Bluetooth address, serials and Apple pairing
   keys ([09](09-psmp-nvds.md)).

## How it fits together

* Firmware ships as a `.up`: a `CONFIG` header around a raw flash image, with a partition index at
  flash `0x3000`. Integrity is CRC16 only. → [04](04-up-format.md), [05](05-crc-and-integrity.md)
* The partitions: FIRM (code), TONE (voice prompts), EQ2P (EQ), SENC (sensor/mic parameters), OTAP
  (the updater) and PSMP (settings). → [07](07-tone-sfx.md), [08](08-eq2p-senc.md), [09](09-psmp-nvds.md)
* The app updates the buds over Bluetooth with `55 AA 80–84` + `04` frames, and reads flash with
  `C0 83`. `tools/hl` speaks both without the app. → [06](06-bt-ota-protocol.md),
  [16](16-live-flash-dump.md), [20](20-hl-cli.md)
* On the bud, OTAP checks one CRC and the bootloader checks nothing. → [17](17-firmware-internals.md)
* FIRM pretends to be AirPods (AAP server, Apple SDP/HID records, BLE pop-up). ANC filters are
  compiled code. → [10](10-aap-airpods.md), [11](11-anc-transparency.md)
* The vendor's factory tool and public projects for the same chip family. → [12](12-shenju-flasher.md), [13](13-open-source-tooling.md)
* The whole-program FIRM map, patch files, and the second analysis pass. → [18](18-firm-walkthrough.md),
  [19](19-cfw-patching.md), [21](21-night-shift.md)
* What's done and what's open for custom firmware. → [15](15-cfw-roadmap.md)

## Status board

| Area | State |
|---|---|
| Device identity & OTA check | known ([01](01-device.md)) |
| StarFun auth + catalog + downloads | working (`tools/pull_ota.py`) |
| `.up` container format | checked on 24/24 catalog images, the H3Pro image, and vendor source |
| CRC algorithm (partition + container) | CRC16/CCITT-FALSE, matches vendor `up_parser.py` |
| Bluetooth OTA wire protocol | read from the app SDK and OTAP, verified on real buds with `tools/hl ota` ([20](20-hl-cli.md)) |
| TONE replace + repack round-trip | done, and an image with replaced prompts flashed to the buds |
| EQ2P edit + repack round-trip | done offline |
| PSMP / NV record format | layout, keys and the 4-byte record check (CRC32) all known |
| AAP surface | present; opcode table and adv/AES path mapped statically ([21](21-night-shift.md)), behaviour untested |
| ANC/transparency tunables | gains known from app source; filters are compiled into FIRM, not shipped as data |
| Bootloader / updater accept CRC-only images | confirmed from the OTAP and bootloader code ([17](17-firmware-internals.md)) and on real buds ([20](20-hl-cli.md)) |
| Write path into earbuds | Bluetooth OTA works (`tools/hl ota`). Wired UART boot-ROM path untested, frame format decoded ([21](21-night-shift.md)) |
| H3Pro Max3 2607061716 image | in the repo, all CRCs valid ([16](16-live-flash-dump.md)) |
| Read-only flash dump over Bluetooth | working, 200 B/reply, `tools/hl read` or `tools/flashdump.py` (~1.1 KB/s via Frida) |
| App auth handshake (`C0 01`/`02`) | a 16-bit LFSR, reimplemented in `tools/huilian` ([18](18-firm-walkthrough.md)) |
| CFW patch files | `tools/cfw.py` + `patches/`, head-tracking patch flashed fine ([19](19-cfw-patching.md)) |
| Mask-ROM surface / FIRM AES / EQ2P page use / UART boot-ROM frames | second-pass analysis done ([21](21-night-shift.md)) |
