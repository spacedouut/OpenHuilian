# Apply a firmware patch

Patch files in `patches/<firmware version>/` change specific bytes in FIRM. `cfw.py` applies them
to your own dump and fixes every checksum. The head-tracking patch has been flashed to real buds.

```bash
python3 tools/cfw.py info  my-buds.up
python3 tools/cfw.py apply my-buds.up my-cfw.up patches/2607061716/head-tracking.json
```

Then flash `my-cfw.up` ([flash an image](flash-an-image.md)).

`info` shows the firmware version and checks the CRCs. A patch only applies to the version it was
written for, and only if the bytes it expects are there. Otherwise `cfw.py` refuses, which is the
point. Don't edit the patch to make it fit.

## Knobs

Patches can expose settings. Without `--set` you get the patch's defaults.

```bash
python3 tools/cfw.py apply my-buds.up my-cfw.up patches/2607061716/head-tracking.json \
    --set tx_ms=25 --set alpha=0.4
```

| Patch | What it does | Knobs |
|---|---|---|
| `2607061716/head-tracking.json` | faster, less laggy head tracking | `tx_ms` report period in ms (stock 40), `decimate` run the fusion every N+1 samples (stock 3), `alpha` smoothing blend (stock 0.1) |

You can stack more than one patch file in one `apply`. `hl patch` runs the same thing.

## Writing a patch

The file format and the rules are in [patch files](../reference/patch-files.md).
