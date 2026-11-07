# How updates get accepted

The buds accept any image whose CRC16 matches. There's no signature, no encryption and no check
of the chip or version. That's why custom firmware works on these buds, and it's also why a wrong
image is dangerous.

## The three programs on flash

| Program | Where | Job |
|---|---|---|
| Bootloader | flash `0x0`, runs from RAM | picks what to boot |
| FIRM | flash `0x4000`, runs in place | the normal firmware. Bluetooth, audio, the AirPods layer, the `C0` commands |
| OTAP | flash `0xD2000`, copied to RAM | the updater. Takes `55 AA` frames and writes flash |

## Boot

The bootloader looks at one word, the flag page right after OTAP (`0xFB000` on the H3Pro). If it
reads `0x55AA`, it boots OTAP. Otherwise it boots FIRM. It doesn't check any CRC first.

## An update, start to end

1. The phone (or `hl`) sends `55 AA 80`. FIRM checks the battery, tells the partner bud, writes
   the `0x55AA` flag and restarts. Both buds come up in OTAP.
2. OTAP takes the declared CRC and length (`82`), erases the area it will write, then
   writes 512-byte chunks wherever the frames say (`83`). The partition index comes last.
3. On `84` OTAP computes CRC16 over everything it was sent and compares it with the `82` value.
   On a match it keeps the new index. On a mismatch it puts the old index back.
4. On `04` OTAP clears the flag and restarts into the new FIRM.

Until `04`, the flag keeps the buds in OTAP across power cycles. That's what makes an interrupted
flash recoverable over Bluetooth. It also means a flash that skips `04` leaves both buds stuck in
the updater ([get buds out of the updater](../how-to/unstick-buds.md)).

## What isn't checked

* **No signature or MAC.** The `.up` carries nothing beyond CRCs, and none of it is encrypted.
  OTAP has no RSA, ECDSA, SHA or AES code.
* **No chip or version check.** The `.up` header's chip name and the build version never reach the
  buds. The app strips the header and the `82` CRC is computed over the bytes it sends.
* **No partition CRC check at boot.** Neither the bootloader nor OTAP checks the per-partition CRCs
  in the index.
* **No address bounds.** OTAP writes wherever a frame says. Nothing below `0x4000` should ever be
  sent.

FIRM does contain a software AES (S-box at FIRM `0xC4BFC6`, also in every catalog image's FIRM).
It's used for Apple Continuity adverts, most likely with the PSMP `air_adv_key`, and has nothing
to do with updates. The app's `C0 01`/`02` handshake is an LFSR scramble that gates the command
channel, and the updater frames don't use it ([command channel](../reference/command-channel.md)).

## What this means

* An image needs correct CRCs, and that's all. `tone_tool.py` and `cfw.py` fix them for you.
* A failed update doesn't roll FIRM back. The old index comes back, but the old FIRM is already
  erased. The buds stay in OTAP, so you can flash again.
* PSMP (your pairing and serials) is never sent, and OTAP keeps its index entry. Updates don't
  touch your settings.
* There's no tested wired recovery yet. The vendor's UART boot-ROM path exists for older chips
  ([vendor tools](vendor-tools-and-prior-art.md)), but it hasn't been tried on H3Pro buds.

The older SL6806 bootloader checks a `CONFIG` magic, a chip-name string and a timestamp. The
H3Pro checks less than that.

Addresses and the code behind each step are in [research: updater](../research/updater-otap.md)
and [research: boot](../research/memory-map-and-boot.md). The CRC algorithm is in
[`.up` format](../reference/up-format.md#crcs).
