# Python package

Run modules from the repository root with `python3 -m openhuilian.<subpackage>.<module>`.
The root [hl](../hl) launcher runs `openhuilian.device.cli`.

| Package | Modules and resources |
|---|---|
| `format` | upfmt, upparts, build_up, tone_tool, psmp_tool, h3pro_elf, sdp_hid, flashmap |
| `device` | cli, proto, link, dash and its HTML, pull_ota |
| `patch` | cfw, repartition, cave debug-monitor builder, headtrack experimental C filter and builders |
| `emu` | Unicorn rehosts and offline regression checks |
| `ui.webui` | Static Web Serial UI, genvec and selftest.mjs |
| `ui.panel` | Desktop panel: `python3 -m openhuilian.ui.panel.server --help` |

Most file utilities use only the Python standard library. Emulation needs Unicorn and
Capstone (audio/motion experiments also need NumPy); ELF analysis needs pyelftools;
flash-map drawing needs Pillow. Serial links need pyserial. Builders document compilers
in their module docstrings.

Use `hl read` for backups and `hl ota` for supported updates; see
[dumping](../docs/how-to/dump-firmware.md) and [flashing](../docs/how-to/flash-an-image.md).
No images or ROMs are bundled. Set `OPENHUILIAN_STOCK_UP` and `OPENHUILIAN_MASK_ROM`
to private input paths; most emulation checks also accept an explicit image argument.

```bash
python3 -m openhuilian.format.tone_tool verify "$OPENHUILIAN_STOCK_UP"
python3 -m openhuilian.emu.monitor_check "$OPENHUILIAN_STOCK_UP"
python3 -m openhuilian.emu.repart_check "$OPENHUILIAN_STOCK_UP"
python3 -m openhuilian.ui.webui.genvec "$OPENHUILIAN_STOCK_UP" > /tmp/vec.json
node openhuilian/ui/webui/selftest.mjs /tmp/vec.json "$OPENHUILIAN_STOCK_UP"
uv run --with ziglang==0.13.0 --with pyelftools python3 -m openhuilian.patch.cave.build
```

Builders write patch JSON to repository-root `patches/`.
See the [tool reference](../docs/reference/tools.md) for purposes and guides.
