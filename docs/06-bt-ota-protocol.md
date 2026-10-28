# 06 · The Bluetooth OTA protocol

Read from the `com.shenju.ota` SDK bundled in StarFun (archived in
[`reference/starfun-app/2.0.7.016/ota/`](../reference/starfun-app/2.0.7.016/ota/)). Not exercised against hardware.

## Transport

* Same **SPP (RFCOMM) command channel** as everything else in the app (`mClient.sendBytes`), with
  OTA frames flagged internally as `CMD_TYPE_OTA = 3` (vs `1` = normal `C0xx` commands).
* Every OTA frame starts with `55 AA`, then a command byte, and ends with a **CRC8/Maxim** (Dallas
  1-Wire CRC, poly 0x31 reflected) over all preceding bytes.
* Multi-byte integers inside frames are **little-endian** (`getSplitReverseHexStringCmd`).
* Ear selector byte: `11` = left, `22` = right, `33` = both.

## Frames

| Frame | Layout | Purpose |
|---|---|---|
| **Control** `80` / `81` / `84` | `55 AA <cmd> <side> 00 <crc8>` | 80 = enter OTA (retried up to 6×), 81 = prepare/erase, 84 = finalize |
| **Declare** `82` | `55 AA 82 <side> 08 <crc32 LE: 4 B> <total_len LE: 4 B> <crc8>` | Announces CRC and length of everything about to be sent, so the device can verify at the end. The CRC is computed by native `BtUtils.getCrc` (the same CRC16/CCITT-FALSE, padded to 4 bytes) over the payload region |
| **Data** `83` | `55 AA 83 <len16 LE> <flash_addr LE: 4 B> <data_len LE: 4 B> <data> <crc8>` where `len16 = data_len + 8` | Raw write. Normal chunks are **512 bytes** (`len16 = 520`); the last chunk may be shorter |
| **Flash read** `C0 83` | `C0 83 <addr LE 4> <len LE 4>` (20-byte buffer, `getReadFlashCmdArray`) | Not an OTA frame — a normal command the app uses to read back EQ2P/TONE from the buds before flashing so settings can be preserved |

Constants of note: `VERIFY_CODE = "534C"` (`"SL"`), `CMD_READ_SUPPORT_OTA = C013`,
`CMD_READ_LEFT_RIGHT_VERSION_STATUS = C012`, `CMD_READ_SOFTWARE_VERSION_05 = C005`.

## What gets written and where

The app parses the `.up` into `UpInfoData`:

* `upPartByteArrayWithOutIndex` — the contiguous partition payload region starting at
  `firmwarePosition` (FIRM's flash address) through the last stored partition;
* `indexByteArray` — the partition index, written **last** as its own `83` frame at
  `indexPosition`.

So the device is treated as a dumb flash writer: `(absolute address, 512 bytes, CRC8)` frames land
wherever the `.up` index says. Writing the index last keeps the old index in place until the very
end, but by then the partitions it points at may already be erased (`81`) or half overwritten
(`83`). On its own that doesn't leave the buds bootable if the update is interrupted. Recovery presumably relies on the separate `OTAP` updater stub / bootloader.

Sequence (`ota_step` 1 → 2 → 3):

```
app → buds  C004 / C009 (model, battery; battery polled every 2 s during OTA)
app → buds  55AA80 <side>           enter OTA           (retry ≤ 6)
app → buds  55AA81 <side>           prepare / erase
app → buds  55AA82 <side> crc len   declare payload
app → buds  55AA83 … × N            512-byte writes, absolute addresses
app → buds  55AA83 index            partition index
app → buds  55AA84 <side>           finalize: reply says whether the CRC matched
app → buds  55AA04 <side>           clear the OTA flag and reboot, link drops
        (wait for reconnect)
        repeat for the other ear (11 → 22)
step 3 = success
```

Per-ear updates are **serial** — that's the two progress bars in the app. Before all of this the
app reads the current EQ2P/TONE off the device (`C0 83`) and, when flashing from a local file,
splices them into the image so user settings survive ([02](02-starfun-app.md), local-file path).

## What the region and CRC actually are

`getUploadContent` builds two buffers. The data frames carry `.up` body bytes from FIRM's address
(`0x4000`) up to OTAP's address, in 512-byte chunks, then one more frame with just the index
(`(count+1)*16` bytes) at `0x3000`. The `82` CRC and length cover body `0x3000` up to OTAP, so
they include the rest of the index page (zeros in every catalog image) as well. On the H3Pro that's
CRC16 over `0xCF000` bytes. OTAP, PSMP and anything below `0x3000` are never sent.

## Replies (from OTAP `FUN_0080e770`)

OTAP answers every frame with `55 AA <cmd> <side> <len> <payload> <crc8>`, where `<side>` is the
bud that is answering (`11`/`22`). It ignores the side byte in requests, so it flashes whichever bud
holds the link.

| Request | Reply payload |
|---|---|
| `80`, `81`, `82`, `04` | `00` |
| `83` | `00 <addr LE 4> <data_len LE 4>`, echoing the frame. A repeat of the last address is acked again without a second write, so resending after a timeout is safe |
| `84` | `00` if the CRC matched and the new index was committed, nonzero if it put the old index back |

OTAP counts written bytes (the index frame counts as `0x1000`) and runs the CRC check once the
count reaches the `82` total. On `04` it clears the boot-to-OTAP flag and reboots
([17](17-firmware-internals.md)). Sending `04` after a failed `84` would boot a half-written FIRM,
so don't.

## Validation the device can perform (from what it is sent)

* CRC8 per frame.
* Whole-payload CRC + length from `82`.
* That's it. OTAP doesn't check partition CRCs, chip name or version; details in [17](17-firmware-internals.md).

Nothing in the protocol carries a signature or key. Whether the `55AA` frames are accepted without
first passing the command-channel challenge/response (`verificationCmd`) hasn't been tested.

## Practical notes for a future CFW push

* Chunk size 512, `len16 = 520` — keep it; the device may only accept that size.
* Send FIRM and friends first, index last, exactly as the app does.
* The app expects a reboot/disconnect after `84` and then reconnects for the other side.
* A one-line patch exposing `SettingMoreActivity.chooseFile()` gives a local-file flasher using
  this exact transport, on the app that already knows how to talk to the buds. It still splices the
  bud's current EQ2P/TONE into your file, though.
* [`tools/flashota.py`](../tools/flashota.py) sends the same frames through StarFun's socket via
  Frida, without the splice, one bud per run, with the safety checks listed in its docstring. It
  hasn't been run against a bud yet.
