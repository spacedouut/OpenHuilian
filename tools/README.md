# tools/

All Python 3, standard library only unless noted. None of them talk to an earbud; they operate on
files (or, for the two network ones, on public servers / a browser session).

| Script | What it does | Doc |
|---|---|---|
| `pull_ota.py` | Log in to `ota.starfun.fun`, list the catalog, query one package/version, download and header-check `.up` files. Needs `STARFUN_USER` / `STARFUN_PASS` env vars (the tenant credentials live in the StarFun APK). | [03](../docs/03-ota-catalog.md) |
| `tone_tool.py` | `list` / `extract` / `replace` / `verify` on the TONE partition of a `.up`; rewrites TONE CRC and container CRC. | [07](../docs/07-tone-sfx.md) |
| `psmp_tool.py` | Read-only dump of the PSMP NV log from a bare PSMP partition or a raw `HLKJ` flash dump (`--all` shows stale records). | [09](../docs/09-psmp-nvds.md) |
| `sdp_hid.py` | Decode the SDP record blob and Apple accessory HID report descriptors found in a FIRM image. | [10](../docs/10-aap-airpods.md) |
| `bt52.py` | Drive an already logged-in Chrome (via Playwright/CDP) to search 52bluetooth and dump threads to text. Needs `playwright`. | [14](../docs/14-52bluetooth.md) |

Quick start on a catalog image:

```bash
python3 tools/tone_tool.py list  firmware/starfun-catalog/h2s_turbo_2506281656.up
python3 tools/tone_tool.py verify firmware/starfun-catalog/h2s_turbo_2506281656.up
python3 tools/psmp_tool.py firmware/openpod-sl6801/GN438_sl6801_fulldump.bin
```

Missing / to write: a generic `.up` partition lister and `EQ2P` float-table editor (the analysis in
[08](../docs/08-eq2p-senc.md) was done with one-off snippets), and a periodic `h3promax3` OTA watcher.
