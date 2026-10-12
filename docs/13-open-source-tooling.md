# 13 · Public SmartLink / SL68xx tooling and prior art

Three public GitHub projects target the same Shenju/SmartLink silicon family as the StarFun
catalog images. None of them touch earbuds or 377H3, but together they independently confirm the
container format, the CRC, and — most importantly — that the bootloader does not check a
signature. Local clones live at `~/starfun/{smartlink_flash,sl6806,OpenPod}` on the research VM;
only the derived artifacts are in this repo.

## `ilyakurdyukov/smartlink_flash` — USB boot-ROM dumper/writer (C, Linux/MSYS2)

<https://github.com/ilyakurdyukov/smartlink_flash>

* Talks to the mask-ROM USB mass-storage mode (`301a:2800`, inquiry `SMTLINK DEVICE 2.00`) via
  SCSI vendor commands; supports SL6801 and SL6806; read/erase/write whole flash.
* Boot key varies per device; card-reader mode `301a:2801` `SMTLINK CARDREADER`.
* `fwhelper/main.c` parses `CONFIG` + `HLKJ` containers and converts a raw dump to `.up` —
  **independent confirmation of [04](04-up-format.md)** (`file_offset = flash_addr + 0x100`,
  index at body `0x20` → `0x3000`).
* SL6806 is the MP3-player chip (YP3 / "云P3", Jointbees); SL6801 is what all 24 StarFun images
  and OpenPod's player use.

## `take-cheeze/sl6806` — Arduino-style framework + bootloader RE (docs/)

<https://github.com/take-cheeze/sl6806>

Its `docs/BOOTLOADER.md`, `FLASHING.md`, `DUMPING.md` read the 61 KB `HLKJ` bootloader end to end.
Key facts for us:

* Boot flow: mask ROM → boot-mode pin check (~1 s) → load HLKJ to `0x0081FC00`, enter
  `0x00820000` → main chooses *update from PC* (USB), *forced restore* (`restore.up`),
  *sdupdate* (`update.up`), or *load FIRM*.
* `.up` acceptance by the bootloader = `memcmp("CONFIG")` → `header pass`; `memcmp(+0x16, "SL6806")`
  → `mark pass`; build-timestamp differs → `time is not same` → proceed. Then a CRC16
  **write-verify** (`crc cmp %x %x`) computed by the bootloader itself, both sides init `0xFFFF`.
* **"Nothing in the payload has to be signed or checksummed in advance."** The only unresolved
  check is a `loadCrc` log string for the FIRM header at boot, whose code was not located.
* USB download mode is in mask ROM → the chip is recoverable over USB regardless of flash contents.

Caveat: this is SL6806. The StarFun images are SL6801 (same vendor, same container; the mark
string there is `SL6801`). On the H3Pro the updater doesn't check a mark string at all ([17](17-firmware-internals.md)).

## `zeroproj/OpenPod` — a shipped custom firmware on SL6801

<https://github.com/zeroproj/OpenPod> · <https://zeroproj.github.io/OpenPod/>

* Rewrites the UI of the Iigenai GN-438 MP3 player (yp3_2.0.43 base) as an iPod-nano clone.
  Distributed as `.up` binaries; RE notes and tools are **not public**.
* Proves the method on this silicon: dump → patch FIRM → fix CRCs → flash via the vendor tool (only checked on the GN-438).
* Its git history contained two things the project later deleted, both preserved here:
  * Shenju's `SetupFlashloaderSL-DEV(6.9.5).exe` → [12-shenju-flasher](12-shenju-flasher.md)
  * `GN438_sl6801_fulldump.bin`, a raw 2 MiB SL6801 flash image with bootloader, partition table
    and a **live PSMP log** → [`firmware/openpod-sl6801/`](../firmware/openpod-sl6801/), used by
    [09](09-psmp-nvds.md) / `tools/psmp_tool.py`.

## What transfers to the H3Pro Max3, and what doesn't

| Transfers (same vendor conventions) | Does not (yet) |
|---|---|
| `.up` container, `HLKJ` table, CRC16, PSMP NV store | any base image (377H3 vs SL6801) |
| no signature (H3Pro is even looser: CRC only, no mark string, see [17](17-firmware-internals.md)) | boot ROM addresses, loader binaries, USB IDs |
| Shenju flasher's `.up`/PSM logic | a physical write path — buds have no USB |
| BT OTA ([06](06-bt-ota-protocol.md)) as the intended field update route | acceptance tested on real H3Pro hardware |
