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
| `build_up.py` | Parse the partition index of a raw flash dump, verify every partition CRC, and wrap `flash[0:end-of-OTAP]` in a `CONFIG` header to produce a `.up`. Refuses to write if any CRC mismatches (`--force` overrides). Optional chip-name argument (unknown for 377H3). | [dump](../docs/how-to/dump-firmware.md) |
| `upparts.py` | Generic `.up` partition lister / extractor / FIRM-strings dumper, any chip generation. Parses the `CONFIG` header + `HLKJ` fields + partition index, verifies every CRC, writes each stored partition to an outdir plus `index.txt` and `firm_strings.txt`. | [format](../docs/reference/up-format.md), [research](../docs/research/README.md) |
| `flashmap.py` | Render the flash / address-space map (docs/flash-map.png) from a `.up`'s real numbers: partitions, ROM/SRAM/XIP spaces, boot flow, container, acceptance rules. PIL only. | [research](../docs/research/README.md) |
| `h3pro_elf.py` | Wrap the H3Pro FIRM / OTAP / bootloader from a `.up` or raw dump into ARM ELFs at their real load addresses for Ghidra. Checks CRCs first. | [research](../docs/research/updater-otap.md) |
| `compmatch.py` + `matching/` | Offline compiler bake-off: verify target hashes, compile C variants with GCC/Clang, resolve Thumb imports, link at stock addresses, and score the entire linked footprint. Saves sources, image, compiler/tool versions, commands, binaries, disassembly, and per-function results in a new output directory. Never produces or sends an OTA image. | Below |
| `hl` + `huilian/` | Native Python `C0`/OTA client for live buds over a serial (RFCOMM/SPP) port: `info`, `auth`, `get`/`set`, `read` (flash dump without Frida), `ota` (both buds, verified on hardware), `leave-ota` (recover buds stuck in the updater), `tone`, `patch`. `--port` takes a Bluetooth address (raw RFCOMM socket on Linux, no deps) or a serial device (needs `pyserial`). | [hl](../docs/reference/tools.md) |
| `webui/` | Static page (`index.html`, ES modules, no build step) that does the same over Web Serial, Chrome/Edge only. Connect to the buds' SPP virtual COM port, run auth/info/settings/flash dump/patch/tone replace/OTA all client-side. `selftest.mjs` checks byte-parity with `huilian/proto.py` + `cfw.py` + `tone_tool.py`. | [hl](../docs/reference/tools.md) |
| `upfmt.py` | Shared helpers the tools above import: `crc16`, the partition-index parser (`index_offset`, `parse_index`), `MAGIC` / `BODY`. Not a CLI. | [format](../docs/reference/up-format.md) |

Quick start on a catalog image:

```bash
python3 tools/tone_tool.py list  firmware/starfun-catalog/h2s_turbo_2506281656.up
python3 tools/tone_tool.py verify firmware/starfun-catalog/h2s_turbo_2506281656.up
python3 tools/psmp_tool.py firmware/openpod-sl6801/GN438_sl6801_fulldump.bin
python3 tools/tone_tool.py list  firmware/h3promax3/h3promax3_2607061716_live.up
```

## Compiler matching

Requires Python 3.10+, an ARM-capable GCC or Clang driver, and GNU ARM binutils
(`as`, `ld`, `objcopy`, `objdump`, `nm`). No Python packages or compiler downloads are performed
by the harness. An installed `arm-linux-gnueabihf-gcc` also works: compilation is freestanding,
and linking uses binutils directly without a Linux C library.

```bash
python3 tools/compmatch.py doctor
python3 tools/compmatch.py list
python3 tools/compmatch.py run --out /tmp/huilian-bakeoff-01
python3 tools/compmatch.py report /tmp/huilian-bakeoff-01
```

`--out` must not already exist. Without `--cc`, the harness finds installed ARM GCC and
Clang drivers. Repeat `--cc /path/to/compiler` to compare versions; use
`--binutils-prefix /path/to/arm-none-eabi-` to select the linker, import assembler, and inspection
tools. GCC's selected assembler is also recorded, including any `-B` override. Relocated
compiler archives may need `--cflag=-B/path/to/arm-none-eabi-` to find the correct assembler
rather than a native host `as`. Legacy ARMCC 5 needs a separate driver adapter
and is not supported yet. The Clang-compatible `armclang` path requires a separately supplied
licensed installation and has not been validated here.

```bash
python3 tools/compmatch.py run --out /tmp/huilian-crc8-01 \
  --cc arm-none-eabi-gcc --target crc8_maxim --opt Os \
  --cflag=-fno-if-conversion --cflag=-fno-if-conversion2
```

The default matrix is `-O1`, `-O2`, `-O3`, and `-Os`, across every source variant in
`matching/targets.json`. Repeat `--target` and `--opt` to narrow a run. `--cpu` selects the
experimental CPU setting (default `cortex-m4`); it is not a claim about the exact chip core.
The current probes use integer arguments and `-mfloat-abi=soft`, so they cannot identify the
firmware's floating-point ABI or FPU. Run compiler-specific `--cflag` experiments separately
if a flag is not shared by all selected drivers.

Eight probes cover 282 bytes of the H3Pro image: NVIC access, a volatile-register loop,
a function calling a stock ROM veneer, CRC8/Maxim, population count, byte comparison, and
bounded bit-mask classification. The byte-comparison probe intentionally retains the stock
low-byte loop-bound quirk; it is not a general `memcmp` implementation. Pure C variants have
host-side behavior tests. MMIO probes are compiled only, never executed.

Both the complete input image and each target slice are SHA256-checked. Expected byte ranges
include trailing alignment and literal pools, not just Ghidra's instruction count. The
generated linker script places code at the original execution address, and a typed Thumb
import object resolves external calls. Unresolved calls, wrong entry points, unexpected
allocated sections, compiler failures, and timeouts are errors, never masked nonmatches.

`results.json` records every attempt; `summary.tsv` tracks the best result per function.
Each attempt retains `candidate.o`, `candidate.elf`, `candidate.bin`, `commands.json`,
`candidate.asm`, and `diff.txt` when those stages succeed. Raw binary disassembly also decodes
literal-pool data as instructions; byte comparison, not that listing, determines exactness.
Outputs include a source/image/runner snapshot that can be replayed with
`python3 <old-out>/runner.py run --manifest <old-out>/targets.json --out <new-out>`.
The compiler binaries still need to be available.

Only identical **fully linked, full-length bytes** receive `exact: true`. Positional byte
percentages and sequence similarity are debugging heuristics, not semantic equivalence or a
probability of compiler identity. Aggregate scores compare the best source variant for each
target under one compiler/optimization pair; failed targets score zero rather than disappearing.
Multiple toolchains can match the same function, and libraries may have been built separately.
An exact match is not hardware validation, a complete SDK reconstruction, or proof of a safe
replacement ABI.

`run` returns 0 for completed nonmatching experiments too, 1 for build failures, and 2 for
invalid input/preflight failures. Add `--require-exact` to return 1 unless every selected target
has at least one exact build. `report` returns nonzero for incomplete runs or recorded build
errors. Checkpoints with `complete: false` are not completed matrices.

Verification:

```bash
python3 -m unittest discover -s tools -p 'test_compmatch.py' -v
python3 tools/flashota.py selftest
```

GCC integration tests skip if ARM GCC/binutils are unavailable; the Clang integration test
skips if Clang/ARM binutils are unavailable. Host behavior tests skip if host GCC is unavailable.
Neither test command connects to a device.

The [initial recorded baseline](../data/analysis/compiler-bakeoff-baseline.json) compared
GCC 8.3.1, 14.2.1, and 15.2.0 using the same GNU ARM assembler/linker. All 264 builds
succeeded; 3 of 8 probes matched exactly: CRC8/Maxim (46 B, GCC 8 at `-Os`), population count
(40 B, all three at `-O2`/`-O3`), and peripheral initialization including calls/literals
(60 B, GCC 14/15 at `-Os`). No single tested compiler/optimization pair matched all three.
This establishes an operational matching loop, not the identity of the original compiler.

The [Clang 18.1.8 follow-up](../data/analysis/compiler-bakeoff-clang18.json) adds 110 successful
builds: 88 at the same four optimization names, plus 22 at `-Oz`. It uses Clang's integrated
assembler and the same GNU ARM linker/import tools. No probes matched exactly, so the GCC
variants remain the better byte-matching lead; this does not rule out other Clang versions,
flags, or source forms. The Clang ARM compile/link/import path now has a regression test.
Use `--cc clang-18` to select the installed version explicitly. This does not validate the
separate proprietary `armclang` driver.

Missing / to write: an `EQ2P` float-table editor (the analysis in
[EQ2P](../docs/reference/eq2p-senc.md) was done with one-off snippets), and a periodic `h3promax3` OTA watcher.

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
