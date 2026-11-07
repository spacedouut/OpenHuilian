# Shenju Flashloader SL-DEV 6.9.5 — provenance and rights

**These files are not ours and are not covered by this repository's AGPL licence.**
They are third-party vendor artifacts archived for research/interoperability reference only.

| Item | What it is | Origin |
|---|---|---|
| `COM.dll`, `MASSSTORAGE.dll`, `c_crc.dll`, `psm-nvds.dll` | Shenju native helper libraries, unmodified | extracted from the PyInstaller bundle |
| `ram_run_bin/*.bin` | Shenju RAM loaders / reset / calibration blobs, unmodified | extracted from the PyInstaller bundle |
| `doc/readme.txt`, `doc/readme_en.txt` | Shenju's own user notes, unmodified | extracted from the PyInstaller bundle |
| `decompiled-src/**` | Python **regenerated with Decompyle++** from the bundled `.pyc` files — a derived work, not the vendor's original source; some functions are marked "Decompyle incomplete" | our decompilation |

* Source artifact: `SetupFlashloaderSL-DEV-6.9.5.exe`, version 6.9.5, recovered 2026-09-22 from the
  git history of `github.com/zeroproj/OpenPod` (removed from that repo's HEAD as "not ours").
  The installer itself is **not** tracked here.
* Copyright: 珠海绅聚科技 / Zhuhai Shenju Technology (Smartlink). No licence text accompanies the tool
  and no redistribution permission has been sought or granted.
* Treat everything in this directory as "look, don't ship": do not redistribute the binaries or the
  decompiled source outside this research context, and do not link them into other projects.

The same applies to `../../reference/starfun-app/` (decompiled excerpts of the StarFun Android app,
© its publisher) and `../../firmware/` (vendor firmware images from the public StarFun catalog and
the OpenPod GN-438 flash dump) — see `docs/explanation/vendor-tools-and-prior-art.md` and `docs/explanation/vendor-tools-and-prior-art.md`.
