# Get stock firmware

No stock images or ROMs are distributed. Dump your own buds using `hl read`, then
wrap the raw flash using build_up. Create a private output directory outside the checkout first.

```bash
./hl --port AA:BB:CC:DD:EE:FF read 0x0 0x100000 ~/stock/flash.bin
python3 -m openhuilian.format.build_up ~/stock/flash.bin ~/stock/my-buds.up
python3 -m openhuilian.format.tone_tool verify ~/stock/my-buds.up
export OPENHUILIAN_STOCK_UP="$HOME/stock/my-buds.up"
```

The length is for a 1 MiB H3Pro Max3; confirm sizes for other hardware.
See [dump firmware](dump-firmware.md) for read details and ROM access limitations.
Never flash another model's image. Raw flash includes device identities and pairing keys.

Experiments using real ROM code also need your own dump:
`export OPENHUILIAN_MASK_ROM="$HOME/stock/my-mask-rom.bin"`.

The optional `python3 -m openhuilian.device.pull_ota` client queries the StarFun server
using existing `STARFUN_USER` / `STARFUN_PASS` credentials. It is not required for
your own stock image, and the server may have no build for your buds.
