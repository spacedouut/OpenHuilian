# OpenHuilian: firmware notes for H3Pro Max3 (Huilian 377H3) earbuds

Docs and tools for the firmware on **H3Pro Max3** earbuds. They use a Huilian **377H3** chip, are sold as an
AirPods-Pro-style replica, and are controlled by the **StarFun** app. The older SL6801 images in the
public catalog use the same container, so they're covered too.

Stock and patched images have been flashed to real H3Pro Max3 buds over Bluetooth with
`tools/hl`. Custom voice prompts and faster head tracking both work.

**Start at [docs/README.md](docs/README.md).** It has two tutorials for a first backup and a first
flash, short how-to guides, reference pages, and the firmware research. Read the safety note there
before you flash anything.

## Repo layout

```
docs/                         the docs (start at docs/README.md)
tools/                        scripts (see tools/README.md)
data/catalog/                 OTA catalog dumps, Shenju Swagger spec, image index
data/analysis/                format notes, FIRM string dumps (old vs new h2sturbo)
data/tones-h2sturbo/          the 17 voice prompts extracted from h2sturbo
data/partitions-h2sturbo/     raw EQ2P and SENC partitions
data/reports/                 HTML write-ups (AAP + ANC/transparency)
firmware/h3promax3/           H3Pro Max3 2607061716 image, read off the buds
data/partitions-h3promax3/    its TONE / EQ2P / SENC partitions, index, FIRM strings, decoded EQ profiles
firmware/starfun-catalog/     the 24 public .up images (all SL6801-class)
firmware/openpod-sl6801/      OpenPod .up + a full 2 MB raw SL6801 flash dump
vendor/shenju-flashloader/    decompiled Shenju "Flashloader SL-DEV 6.9.5" + RAM loaders + DLLs
reference/starfun-app/        the decompiled StarFun Java that matters (OTA SDK, command config)
```
