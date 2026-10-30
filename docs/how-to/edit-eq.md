# Edit the EQ

There are two ways to change the sound. Switching presets or setting the user EQ happens live over
Bluetooth and doesn't touch flash. Editing the factory curves means changing the EQ2P partition
and flashing.

## Live

`hl set eq_mode <n>` writes the one-byte EQ mode. The buds also have commands for the user EQ
(`C0 92` to `94` and `A4`, see [command channel](../reference/command-channel.md)) that `hl` doesn't
wrap yet. `hl cmd <hex>` sends one raw.

## In the image

The H3Pro EQ2P holds 7 profiles of 14 bands each. Profile 1 is the stock house curve, 2 to 6 are
alternatives, and 0 is a different curve with an extra compressor-like block. All values are
little-endian floats ([EQ2P](../reference/eq2p-senc.md)). There's no editor tool yet. This script
changes the gain of one band and fixes both CRCs (run it from the repo root):

```python
# eq_gain.py <in.up> <out.up> <profile> <band> <gain_db>
import struct, sys
sys.path.insert(0, "tools")
from upfmt import BODY, crc16, index_offset, parse_index

src, dst, page, band, gain = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5])
up = bytearray(open(src, "rb").read())
body = memoryview(up)[BODY:]
_, parts = parse_index(body)
i, (tag, addr, length, crc) = next((i, p) for i, p in enumerate(parts) if p[0] == b"EQ2P")
eq = up[BODY + addr: BODY + addr + length]
assert eq[:4] == b"SLEQ" and eq[4] == 2
hdr = struct.unpack_from("<H", eq, 8)[0]
counts = struct.unpack_from(f"<{eq[5]}H", eq, 10)
off = hdr + 8 * sum(counts[:page])
for r in range(counts[page]):
    kind, param, b, val = struct.unpack_from("<BBHf", eq, off + 8 * r)
    if b == band and param == 2:
        struct.pack_into("<f", up, BODY + addr + off + 8 * r + 4, gain)
        print(f"profile {page} band {band}: {val:+.1f} dB -> {gain:+.1f} dB")
        break
else:
    sys.exit("band not found")
ent = index_offset(body) + 16 + 16 * i
struct.pack_into("<I", up, BODY + ent + 12, crc16(up[BODY + addr: BODY + addr + length]))
struct.pack_into("<H", up, 0x14, crc16(up[BODY:]))
open(dst, "wb").write(up)
```

```bash
python3 eq_gain.py my-buds.up eq.up 1 4 2.0      # profile 1, band 4 (2421 Hz) from +3.8 to +2.0 dB
python3 tools/tone_tool.py verify eq.up
```

Band numbers and current values for every profile are in
[`data/partitions-h3promax3/eq2p_profiles.txt`](../../data/partitions-h3promax3/eq2p_profiles.txt).
The same record format holds frequency (`param` 0) and Q (`param` 1). An edited EQ2P hasn't been
flashed to buds yet, only round-tripped offline.
