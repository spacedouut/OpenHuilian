# tools/

All Python 3, standard library only unless noted. These talk to an earbud: `hl` (and the `webui/`
and `panel/` built on the same protocol), which reads, changes settings and flashes, `flashdump.py`,
which is strictly read-only, and `flashota.py`, which writes firmware and only when you ask it to.
The rest operate on files (or, for `pull_ota.py`, on the StarFun server).

| Script | What it does | Doc |
|---|---|---|
| `pull_ota.py` | Log in to `ota.starfun.fun`, list the catalog, query one package/version, download and header-check `.up` files. Needs `STARFUN_USER` / `STARFUN_PASS` env vars (the tenant credentials live in the StarFun APK). | [catalog](../docs/explanation/the-app-and-servers.md) |
| `tone_tool.py` | `list` / `extract` / `replace` / `verify` on the TONE partition of a `.up`; rewrites TONE CRC and container CRC. | [TONE](../docs/reference/tone.md) |
| `psmp_tool.py` | Dump the PSMP NV log from a bare PSMP partition or a raw `HLKJ` flash dump (`--all` shows stale records), `verify` every record's CRC32 check, or `set key=value` to append records offline (writes a new file, never a device). | [PSMP](../docs/reference/psmp.md) |
| `sdp_hid.py` | Decode the SDP record blob and Apple accessory HID report descriptors found in a FIRM image. | [AirPods](../docs/explanation/airpods-emulation.md) |
| `flashdump.py` + `flashdump.js` | **Read-only** flash dump of live buds through StarFun's own authenticated Bluetooth socket: Frida (`pip install frida==16.5.9`, matching `frida-server` on the rooted Android host running StarFun) drives `CMDConfig.getReadFlashCmdArray(addr,len)` / `sendBytes(cmd,1)` and captures the `C083` replies. `FRIDA_HOST=ip:port flashdump.py <addr_hex> <len> <out.bin> [chunk]` (chunk ≤ 200, the device's reply cap). Replies are matched to the outstanding request and the file is only written when the whole range was read. The only command ever sent is `C0 83`. | [dump](../docs/how-to/dump-firmware.md) |
| `flashota.py` + `flashota.js` | Push a `.up` to **one** bud over the same Frida/StarFun socket, using the app's own `55 AA 80/81/82/83/84/04` frames but without its EQ2P/TONE splice, so custom prompts survive. `plan <image.up> --stock <stock.up>` is offline: it checks every CRC, refuses images whose OTAP/PSMP differ from stock or that would write outside `0x4000`..OTAP (plus the index page), and prints the frames (`--frames f.txt` dumps them all). `send ... --side L|R` does the same checks, reads the bud's live index (`C0 83`) and refuses if its FIRM/OTAP/PSMP entries don't match, asks you to type `FLASH`, then sends (`--resume` skips the live read for a bud already stuck in OTAP). If `84` reports a CRC failure it stops before `04`, so the bud stays in OTAP. `selftest` checks the CRC and frame code. Not yet run against a bud. | [OTA](../docs/reference/ota-protocol.md) |
| `repartition.py` | Re-lay SENC, TONE and EQ2P inside the free span between FIRM and OTAP (FIRM, OTAP and PSMP stay put), optionally growing TONE (`--tone-len`), growing FIRM for code caves (`--firm-end`) or swapping prompts. `relayout()` is shared with `cfw.py`. Rewrites the index, partition CRCs and container CRC, and refuses output that fails `upfmt.ota_image_problems`. Offline only; not yet flashed to a bud. | [memory map](../docs/research/memory-map-and-boot.md#flash-layout) |
| `emu/repart_check.py` | Unicorn check that FIRM follows a moved layout: boots each `.up` (first one is the stock reference, plus a built-in shuffled layout) into `task main`, maps every flash access in the SENC/TONE/EQ2P span through that image's own index and requires the same accesses, bytes, lookups and peripheral writes as stock, then calls FIRM's TONE readers (`0xc6f9b8`, `0xc6fa38`) for every prompt. Exits 1 on any mismatch. | [memory map](../docs/research/memory-map-and-boot.md#flash-layout) |
| `cfw.py` | Apply version-pinned patch files to a `.up` and fix every CRC. A patch's `layout` block grows FIRM for new code and reserves heap RAM (lowers FIRM's heap-size literal); the result must pass the OTA checks. | [patch files](../docs/reference/patch-files.md) |
| `cave/build.py` + `cave/monitor.c` | Build the debug monitor (C, zig's clang for Cortex-M4, linked at the cave address) into `patches/2607061716/debug-monitor.json`. `uv run --with ziglang==0.13.0 --with pyelftools python3 tools/cave/build.py`. Refuses undefined symbols and initialized data. | [debug monitor](../docs/research/debug-monitor.md) |
| `emu/monitor_check.py` | Unicorn check of the debug monitor: applies the patch, boots stock and patched FIRM, feeds frames into the real C0 handler, checks every `D0`-`D4` command and error path, the handshake lock, stock commands through the hook, and `hl mon` over an emulated link. Exits 1 on any failure. | [debug monitor](../docs/research/debug-monitor.md) |
| `build_up.py` | Parse the partition index of a raw flash dump, verify every partition CRC, and wrap `flash[0:end-of-OTAP]` in a `CONFIG` header to produce a `.up`. Refuses to write if any CRC mismatches (`--force` overrides). Optional chip-name argument (unknown for 377H3). | [dump](../docs/how-to/dump-firmware.md) |
| `upparts.py` | Generic `.up` partition lister / extractor / FIRM-strings dumper, any chip generation. Parses the `CONFIG` header + `HLKJ` fields + partition index, verifies every CRC, writes each stored partition to an outdir plus `index.txt` and `firm_strings.txt`. | [format](../docs/reference/up-format.md), [research](../docs/research/README.md) |
| `flashmap.py` | Render the flash / address-space map (docs/flash-map.png) from a `.up`'s real numbers: partitions, ROM/SRAM/XIP spaces, boot flow, container, acceptance rules. PIL only. | [research](../docs/research/README.md) |
| `h3pro_elf.py` | Wrap the H3Pro FIRM / OTAP / bootloader from a `.up` or raw dump into ARM ELFs at their real load addresses for Ghidra. Checks CRCs first. | [research](../docs/research/updater-otap.md) |
| `hl` + `huilian/` | Native Python `C0`/OTA client for live buds over a serial (RFCOMM/SPP) port: `info`, `auth`, `get`/`set`, `read` (flash dump without Frida), `ota` (both buds, verified on hardware), `leave-ota` (recover buds stuck in the updater), `dash` (local tuning page: settings, gestures, live ANC gains over HFP), `tone`, `patch`, `mon` (debug monitor: `info`, `peek`, `poke`, `call`, `log`; needs the `debug-monitor` patch). `--port` takes a Bluetooth address (raw RFCOMM socket on Linux, no deps) or a serial device (needs `pyserial`). | [settings](../docs/how-to/change-settings.md), [flash](../docs/how-to/flash-an-image.md) |
| `webui/` | Static page (`index.html`, ES modules, no build step) that does the same over Web Serial, Chrome/Edge only. Connect to the buds' SPP virtual COM port, run auth/info/settings/flash dump/patch/tone replace/OTA all client-side. `selftest.mjs` checks byte-parity with `huilian/proto.py` + `cfw.py` + `tone_tool.py`. | [hl](../docs/reference/tools.md) |
| `emu/h3emu.py` | Offline Unicorn rehost of the H3Pro FIRM (`pip install unicorn capstone`). Loads a `.up` or raw flash dump, fills the unavailable mask ROM with `bx lr` stubs plus emulated `memcpy`/`memset`/`strcmp`/`malloc`/flash-read helpers, maps peripherals on first touch and logs every access. Boots to the scheduler (`--run-task NAME` jumps into a task) or runs one function with `--call ADDR --reg r0=.. --poke ADDR=HEX --peek ADDR:LEN`. Never touches a bud. | [ROM read](../docs/research/rom-read.md), [research](../docs/research/README.md) |
| `upfmt.py` | Shared helpers the tools above import: `crc16`, the partition-index parser (`index_offset`, `parse_index`), `MAGIC` / `BODY`. Not a CLI. | [format](../docs/reference/up-format.md) |

Quick start on a catalog image:

```bash
python3 tools/tone_tool.py list  firmware/starfun-catalog/h2s_turbo_2506281656.up
python3 tools/tone_tool.py verify firmware/starfun-catalog/h2s_turbo_2506281656.up
python3 tools/psmp_tool.py firmware/openpod-sl6801/GN438_sl6801_fulldump.bin
python3 tools/tone_tool.py list  firmware/h3promax3/h3promax3_2607061716_live.up
```

## Panel (`tools/panel/`)

Desktop control panel: a small HTTP server (`server.py`) proxies the C0
protocol through `tools/huilian` over the buds' SPP link, and a local web UI
(`index.html`) shows live status and every known setting. Run:

    python3 tools/panel/server.py --port AA:BB:CC:DD:EE:FF

then open http://127.0.0.1:8765 (phone Bluetooth must be off; the buds hold
one SPP session). Settings beyond `hl`'s verified set (voice_wake,
custom_volume, talk_sensitive, low_high_vol, game_check, space_audio,
audio_type, dialog_op) come from the app's `CMDConfig.java` and are marked
unverified until exercised on hardware. A raw console sends arbitrary C0
commands. The command surface is cataloged in
[../data/analysis/c0-census.md](../data/analysis/c0-census.md).
