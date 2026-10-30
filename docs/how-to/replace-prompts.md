# Replace voice prompts

The voice prompts and click sounds live in the TONE partition. `tone_tool.py` swaps them and fixes
the checksums. This has been flashed to real buds.

```bash
python3 tools/tone_tool.py list    my-buds.up
python3 tools/tone_tool.py extract my-buds.up stock-tones/
python3 tools/tone_tool.py replace my-buds.up connected.mp3=new.mp3 noise.mp3=new-anc.mp3 -o custom.up
python3 tools/tone_tool.py verify  custom.up
```

Then flash `custom.up` ([flash an image](flash-an-image.md)).

## Rules for the new files

1. **Match the stock file's format.** Use the same sample rate and bitrate as the slot you replace,
   in mono. Run `ffprobe` on the extracted stock file to see it. The file extension doesn't
   matter, several `.mp3` slots hold WAV data (on the H3Pro, `low_power.mp3` is 8 kHz PCM).
2. **Strip the extras.** Trim silence at both ends and leave out ID3 tags and the Xing header.
3. **Fit the total size.** The H3Pro TONE partition is full, 84,903 bytes. `replace` refuses a set
   that goes over, so a longer prompt has to be paid for by shorter ones.
4. **Keep the names.** The firmware finds prompts by file name.

An ffmpeg line for a 16 kHz, 24 kbps MP3 slot:

```bash
ffmpeg -i in.wav -ac 1 -ar 16000 -b:a 24k -map_metadata -1 -write_xing 0 -id3v2_version 0 out.mp3
```

## Which prompt is which

| File | When it plays |
|---|---|
| `connected.mp3`, `disconnected.mp3` | phone connects or disconnects |
| `noise.mp3`, `pass_those.mp3`, `adpt.mp3`, `close.mp3` | ANC on, transparency, adaptive, off |
| `game_mode_open.mp3`, `game_mode_close.mp3` | game mode on or off |
| `call.mp3`, `hangup.mp3` | incoming call, call ended |
| `low_power.mp3`, `power_off.mp3` | low battery, power off |
| `space_close.mp3` | spatial audio off |
| `key.wav`, `key_up.mp3`, `slip*.wav` | button and volume-slide clicks |

The full list with sizes and formats is in [TONE](../reference/tone.md).
