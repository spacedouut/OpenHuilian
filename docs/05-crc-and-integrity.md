# 05 · CRCs and the integrity model

**Short version: the only integrity check on a `.up` image is CRC16. No signature, no encryption,
no hash chain.** This is the fact that makes custom firmware realistic on this platform.

## The algorithm

**CRC16/CCITT-FALSE**: polynomial `0x1021`, initial value `0xFFFF`, no reflection, no final XOR.

Derived by brute-matching the stored values across the catalog, then found verbatim in the
vendor flasher:

```python
# vendor/shenju-flashloader/decompiled-src/burn_service/flash_loader/up_parser.py
def crc16(init, bytes_to_calc):
    def crc16_one_byte(lastcrc, one_byte):
        POLY_CRC16 = 4129            # 0x1021
        for i in range(8):
            if (one_byte << i ^ lastcrc >> 8) & 128 != 0:
                lastcrc = ((lastcrc << 1) ^ POLY_CRC16) & 65535
            else:
                lastcrc = (lastcrc << 1) & 65535
        return lastcrc & 65535
    for b in bytes_to_calc:
        init = crc16_one_byte(init, b)
    return init
# called with init = 65535 (0xFFFF)
```

`tools/upfmt.py` has the same function; every tool in `tools/` imports it from there.

## Where CRCs live

| CRC | Covers | Stored at |
|---|---|---|
| **Partition CRC** | the partition payload (`file[addr+0x100 : addr+0x100+len]`) | low 16 bits of the `crc` u32 in that partition's index record |
| **Container CRC** | the entire body `file[0x100:]` | outer header offset `0x14` |
| **OTA whole-payload CRC** | everything the app streams (partitions + index) | sent in the `55AA82` frame before data ([06](06-bt-ota-protocol.md)) |
| **Per-frame CRC8** | each Bluetooth OTA frame | CRC8/Maxim (Dallas), appended to the frame |

`PSMP` has crc 0 because it isn't shipped.

## Validation results across the catalog

* Partition CRCs: **match in 24/24 images** (5 or 6 partitions each).
* Container CRC: **match in 23/24**. The exception, `a10_2311090955_RYEQ.up`, has correct
  partition CRCs and a stale outer CRC — looks like a reseller EQ re-tune that fixed the inner
  checksum but not the outer one, and StarFun still serves it as `types: all`. Whether devices
  accept it (i.e. whether the container CRC is even checked by the app/device) is untested;
  the app's own OTA path recomputes its whole-payload CRC from the bytes it sends, so the outer
  header CRC may only matter for the vendor flasher.
* `smartlink_flash/fwhelper scan` independently reproduced both mismatches on that file.
* The OpenPod `B27_251112.up` also reports a FIRM CRC mismatch under `fwhelper` — a modified/test
  artifact or table-version quirk; not generalised.

## Round-trips performed

1. **EQ2P edit** → recompute partition CRC + container CRC → all CRCs re-validate; output file same
   size (`repack_test.up`, not kept in repo).
2. **TONE prompt swap** (`game_mode_open.mp3` → custom beep) via `tools/tone_tool.py replace` →
   all 6 CRCs re-validate; re-extraction returns the custom file and the 16 untouched prompts
   byte-identical; the diff outside the TONE payload is exactly 4 bytes (TONE crc field + outer CRC).

## What is *not* there

The `.up` image carries no signature, MAC or hash beyond the CRCs above, and none of its bytes
are encrypted. OTAP, the code that accepts an image, has no RSA/ECDSA/SHA/AES constants and no
signature-related strings.

FIRM does contain crypto code, it just isn't used on images. Every FIRM blob in the catalog
carries a software AES (the H3Pro live image has its S-box at `0xC4BFC6`). Its callers are the
Apple Continuity advert builders, most likely encrypting post-pairing adverts with the PSMP
`air_adv_key` ([21](21-night-shift.md)). Image acceptance happens in OTAP, which has no AES, so
this doesn't change the CRC16-only model. No SHA/MD5/TEA/XTEA/RC4 constants show up anywhere.

The app's `encryptData`/`verificationCmd` is a keyed challenge/response to unlock the
**command channel**, not an image signature ([02](02-starfun-app.md)).
The SL6806 bootloader RE ([13](13-open-source-tooling.md)) shows the update validator checks
`CONFIG` magic + chip-name string + timestamp compare + write-verify CRC — nothing cryptographic.

## Does the device actually only check a CRC?

This used to be the big unknown. It's now answered from the H3Pro's own code
([17](17-firmware-internals.md)): the OTAP updater checks one CRC16 over everything from the index
onwards against the CRC the phone declares in `82`, and the bootloader checks nothing at all.
Real buds have since taken modified images over this path with only the CRCs fixed up
([20](20-hl-cli.md)).
