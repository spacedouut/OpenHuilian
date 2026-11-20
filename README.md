# OpenHuilian

Tools and docs for reading, changing and flashing H3Pro Max3 earbuds (Huilian 377H3,
controlled by the StarFun app). Start at [docs/README.md](docs/README.md) and read its safety note.

| Path | Contents |
|---|---|
| [openhuilian/](openhuilian/README.md) | Python package: formats, device CLI, patching, emulation and UIs |
| [hl](hl) | Device CLI launcher; equivalent to `python3 -m openhuilian.device` |
| [patches/](patches/) | Version-pinned patch definitions |
| [docs/](docs/README.md) | Tutorials, how-to guides, reference and research |
| [data/](data/) | Small hand-written command census and EQ profile facts |

No stock images, ROMs, vendor binaries or decompiled app archives are distributed.
[Dump your own image](docs/how-to/get-stock-firmware.md) and keep it outside the checkout.
Set `OPENHUILIAN_STOCK_UP` and `OPENHUILIAN_MASK_ROM` to private input paths.

Run from the repository root:
```bash
python3 -m openhuilian.format.tone_tool verify "$OPENHUILIAN_STOCK_UP"
./hl --help
```

## License

AGPL-3.0, see [LICENSE](LICENSE).
