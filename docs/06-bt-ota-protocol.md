# 06 · The Bluetooth OTA protocol

Read from the `com.shenju.ota` SDK bundled in StarFun (archived in
[`reference/starfun-app/2.0.7.016/ota/`](../reference/starfun-app/2.0.7.016/ota/)). Everything is
**[source]** unless marked. Not exercised against hardware.

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
| **Declare** `82` | `55 AA 82 <side> 08 <crc32 LE: 4 B> <total_len LE: 4 B> <crc8>` | Announces CRC and length of everything about to be sent, so the device can verify at the end. The CRC is computed by native `BtUtils.getCrc` (the same CRC16/CCITT-FALSE, padded to 4 bytes) over the payload region **[confirmed]** |
| **Data** `83` | `55 AA 83 <len16 LE> <flash_addr LE: 4 B> <data_len LE: 4 B> <data> <crc8>` where `len16 = data_len + 8` | Raw write. Normal chunks are **512 bytes** (`len16 = 520`); the last chunk may be shorter |
| **Flash read** `C0 83` | `C0 83 <addr LE 4> <len LE 4>` (20-byte buffer, `getReadFlashCmdArray`) | Not an OTA frame — a normal command the app uses to read back EQ2P/TONE from the buds before flashing so settings can be preserved **[inferred]** |

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
(`83`). On its own that doesn't leave the buds bootable if the update is interrupted. Recovery presumably relies on the separate `OTAP` updater stub / bootloader. **[inferred]**

Sequence (`ota_step` 1 → 2 → 3):

```
app → buds  C004 / C009 (model, battery; battery polled every 2 s during OTA)
app → buds  55AA80 <side>           enter OTA           (retry ≤ 6)
app → buds  55AA81 <side>           prepare / erase
app → buds  55AA82 <side> crc len   declare payload
app → buds  55AA83 … × N            512-byte writes, absolute addresses
app → buds  55AA83 index            partition index
app → buds  55AA84 <side>           finalize → bud reboots, link drops
        (wait for reconnect)
        repeat for the other ear (11 → 22)
step 3 = success
```

Per-ear updates are **serial** — that's the two progress bars in the app. Before all of this the
app reads the current EQ2P/TONE off the device (`C0 83`) and, when flashing from a local file,
splices them into the image so user settings survive ([02](02-starfun-app.md), local-file path).

## Validation the device can perform (from what it is sent)

* CRC8 per frame.
* Whole-payload CRC + length from `82`.
* That's it. OTAP doesn't check partition CRCs, chip name or version; details in [17](17-firmware-internals.md). **[confirmed, static]**

Nothing in the protocol carries a signature or key. Whether the `55AA` frames are accepted without
first passing the command-channel challenge/response (`verificationCmd`) is **[unverified]**.

## Practical notes for a future CFW push

* Chunk size 512, `len16 = 520` — keep it; the device may only accept that size.
* Send FIRM and friends first, index last, exactly as the app does.
* The app expects a reboot/disconnect after `84` and then reconnects for the other side.
* A one-line patch exposing `SettingMoreActivity.chooseFile()` gives a local-file flasher using
  this exact transport, on the app that already knows how to talk to the buds.
