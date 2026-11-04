# OpenHuilian

Tools and docs for reading, changing and flashing the firmware on H3Pro Max3 earbuds. These are
AirPods Pro replicas with a Huilian 377H3 chip, controlled by the StarFun app.

Start at [docs/README.md](docs/README.md). Read the safety note there before you flash anything.

## What's here

| Folder | Contents |
|---|---|
| [`docs/`](docs/README.md) | Tutorials, how-to guides, reference and firmware research |
| [`tools/`](tools/README.md) | `hl` (talk to the buds and flash them) and the file tools for `.up` images |
| [`patches/`](patches/) | Firmware patches for `tools/cfw.py` |
| [`firmware/`](firmware/) | The stock H3Pro Max3 image, the 24 public StarFun catalog images (SL6801, not for these buds) and an OpenPod SL6801 dump |
| [`data/`](data/) | Catalog dumps, extracted partitions and prompts, string dumps, analysis notes |
| [`reference/`](reference/starfun-app/) | The parts of the decompiled StarFun app that matter |
| [`vendor/`](vendor/shenju-flashloader/README.md) | The decompiled Shenju factory flasher |

## License

AGPL-3.0, see [LICENSE](LICENSE).
