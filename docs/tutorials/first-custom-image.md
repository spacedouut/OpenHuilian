# Tutorial: flash your first custom image

This page walks you through changing one voice prompt and flashing the result to both buds. It
takes about 15 minutes, most of it waiting for the flash.

Flashing really does write to your buds. Read this whole page before you start. If something goes
wrong, [Get buds out of the updater](../how-to/unstick-buds.md) covers recovery.

You need:

* Everything from [Talk to your buds](first-connection.md), done at least once
* The buds charged. The firmware refuses to enter the updater when the battery is low.
* A short sound file you want to hear instead of a stock prompt

## 1. Pick the prompt to replace

List what's in the stock image:

```bash
python3 tools/tone_tool.py list firmware/h3promax3/h3promax3_2607061716_live.up
```

This example replaces `connected.mp3`, the sound you hear when the buds connect to a phone. Note
its size in the list.

## 2. Make the new sound match

The buds only play formats the stock prompts already use. Pull out the stock file and check its
format:

```bash
python3 tools/tone_tool.py extract firmware/h3promax3/h3promax3_2607061716_live.up stock-tones/
ffprobe stock-tones/connected.mp3
```

Encode your sound with the same sample rate and bitrate, in mono. Trim silence at both ends, and
don't add ID3 tags or a Xing header. If the stock file is MP3 at 16 kHz and 24 kbps:

```bash
ffmpeg -i my-sound.wav -ac 1 -ar 16000 -b:a 24k -map_metadata -1 -write_xing 0 -id3v2_version 0 my-connected.mp3
```

Keep it short. The whole TONE partition is full, so the new prompt can't be much bigger than the
one it replaces. [Replace voice prompts](../how-to/replace-prompts.md) has the details.

## 3. Build the image

```bash
python3 tools/tone_tool.py replace firmware/h3promax3/h3promax3_2607061716_live.up \
    connected.mp3=my-connected.mp3 -o custom.up
python3 tools/tone_tool.py verify custom.up
```

`replace` rebuilds the prompt list and fixes every checksum. `verify` should say
`ALL CRCs VALID`. If `replace` refuses because the set is too big, make the file shorter or lower
its bitrate to match the stock one.

## 4. Flash both buds

Take both buds out of the case, keep them close to the computer, and run:

```bash
python3 tools/hl --port AA:BB:CC:DD:EE:FF ota custom.up
```

Here's what you'll see:

1. Both buds restart into the updater and the connection drops. The tool reconnects.
2. The first bud is erased, written and checked. This is the slow part, about 3 to 4 minutes.
3. The tool tells that bud to leave the updater. It restarts into the normal firmware.
4. The tool reconnects and does the same for the second bud.

Don't close the terminal or put the buds away while it runs.

## 5. Check it worked

```bash
python3 tools/hl --port AA:BB:CC:DD:EE:FF info
```

Both buds should answer and show as linked. Turn your phone's Bluetooth back on and connect. You
should hear your new sound.

If the buds don't reconnect, put both in the case, close the lid for about 10 seconds, and take
them out again. If they show up as a generic Bluetooth device with no AirPods pop-up, they are
still in the updater. Run `python3 tools/hl --port AA:BB:CC:DD:EE:FF leave-ota`.

## What you did

You built an image with a custom prompt and flashed it over Bluetooth. Flashing the stock image
`firmware/h3promax3/h3promax3_2607061716_live.up` the same way puts the original sound back.

Next steps:

* [Apply a firmware patch](../how-to/apply-a-patch.md), such as faster head tracking
* [How updates get accepted](../explanation/how-updates-are-accepted.md), to understand why this
  works
