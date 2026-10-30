# TONE: voice prompts

The easiest thing in the image to change, and the one that needs no code reverse-engineering.
All of it was checked by extracting and doing a full replace/repack round-trip on
`h2s_turbo_2506281656.up`. The live H3Pro image uses the same format (see the end of this page).

## Layout

```
TONE partition
  0x000 .. 0x400   directory: repeated  [u32 LE size][filename\0]   (zero-padded to 0x400)
  0x400 ..         raw audio files, concatenated in directory order, no padding
```

Extension in the name is cosmetic, several `.mp3` entries are actually RIFF/WAV
(the decoder sniffs content).

## Contents of h2sturbo 2506281656 (17 files, 83,143 B, packed to the byte)

| Name | Size | Actual format | Meaning |
|---|---|---|---|
| `power_off.mp3` | 2,833 | MP3 v2 24 kbps 16 kHz mono | power off |
| `low_power.mp3` | 5,716 | **WAV** PCM16 mono 8 kHz | low battery |
| `close.mp3` | 3,896 | MP3 v1 56 kbps 48 kHz mono | (mode) off |
| `key_up.mp3` | 1,750 | **WAV** PCM16 mono 48 kHz | key release click |
| `adpt.mp3` | 8,432 | MP3 v1 56 kbps 48 kHz mono | adaptive (ANC) |
| `call.mp3` | 10,508 | MP3 v2 24 kbps 16 kHz mono | incoming call |
| `noise.mp3` | 4,064 | MP3 v1 56 kbps 48 kHz mono | noise cancelling |
| `pass_those.mp3` | 5,408 | MP3 v1 56 kbps 48 kHz mono | transparency ("pass-through") |
| `disconnected.mp3` | 3,157 | MP3 v2 24 kbps 16 kHz mono | disconnected |
| `hangup.mp3` | 2,768 | MP3 v2 56 kbps 22.05 kHz mono | call ended |
| `connected.mp3` | 3,913 | MP3 v2 24 kbps 16 kHz mono | connected |
| `space_close.mp3` | 1,760 | MP3 v2 24 kbps 16 kHz mono | spatial audio off |
| `game_mode_open.mp3` | 2,300 | MP3 v2 24 kbps 16 kHz mono | low-latency / game mode on |
| `slip_max.wav` | 7,198 | WAV PCM16 mono 48 kHz | volume-slide max click |
| `slip.wav` | 5,804 | WAV PCM16 mono 48 kHz | volume-slide click |
| `key.wav` | 2,772 | WAV PCM16 mono 48 kHz | key click |
| `slip_min.wav` | 9,840 | WAV PCM16 mono 48 kHz | volume-slide min click |

All 17 are in [`data/tones-h2sturbo/`](../../data/tones-h2sturbo/). Across the catalog there are 10
distinct TONE blobs, packs are shared between product families.

## The tool

```
python3 tools/tone_tool.py list    fw.up
python3 tools/tone_tool.py extract fw.up outdir/
python3 tools/tone_tool.py replace fw.up game_mode_open.mp3=my.mp3 [more=...] -o out.up
```

`replace` rebuilds the directory, rewrites sizes, recomputes the TONE partition CRC16 and the outer
container CRC16, and verifies every other partition still matches its stored CRC.

Round-trip result: custom beep in, all 6 CRCs valid, re-extract gives the custom file and the 16
untouched prompts byte-identical; only 4 bytes changed outside the TONE payload (TONE crc + outer CRC).

## Constraints when making your own prompts

1. **Match the original encoding**: MP3 mono at 16 kHz/24 kbps (or 48 kHz/56 kbps) or WAV PCM16
   mono 48 kHz. The on-device decoder's exact capabilities are untested, so stick to formats
   that already ship. What has worked on H3Pro buds is matching each slot's stock sample rate and
   bitrate, mono, with leading and trailing silence trimmed and no ID3 or Xing header.
2. **Fit the partition**: stock TONE is exactly full; there is ~2.8 KB of slack before EQ2P
   (`0xBC000 + 0x144C7` vs EQ2P at `0xD1000`… check per image). To grow it, move TONE into the
   ~1 MB of zero padding after EQ2P by rewriting its index `flash_addr`/`length`, the transport
   writes to whatever addresses the index says, so this is feasible but untested on hardware.
3. Directory has 0x400 bytes for names+sizes (~1 KB), plenty for ~17–40 entries.
4. Keep filenames identical, FIRM looks prompts up by name (the strings appear in FIRM).

## On the H3Pro

The round-trip above was on an SL6801 H2S Turbo image. The live H3Pro image
([device](device.md)) uses the same TONE format: `tools/tone_tool.py` lists its 18 prompts
and its CRC verifies. An image with six replaced prompts (connected, disconnected and the ANC /
transparency / adaptive ones), built with `tone_tool.py replace`, has been flashed to real buds
with `tools/hl ota` ([command channel](command-channel.md)). The H3Pro TONE is packed to its declared 84,903 B and
`tone_tool.py replace` won't go past that, so the new set has to fit in the same total. `low_power`
is 8 kHz PCM in an `.mp3`-named slot.
