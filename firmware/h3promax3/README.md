# firmware/h3promax3/

`h3promax3_2607061716_live.up` — the genuine firmware of an **H3Pro Max3** (chip `H3Pro`, "377H3",
manufacturer `377Youth·心动版`, firmware `2607061716`), **read off the owner's own earbuds** over
Bluetooth on 2026-09-23 and re-wrapped as a `.up`. How: [docs/16](../../docs/16-live-flash-dump.md).

* Body = flash `0x00000 … 0xFAD50` (HLKJ header, partition index, FIRM, SENC, TONE, EQ2P, OTAP).
  All five partition CRCs and the container CRC verify (`tools/tone_tool.py verify`).
* **PSMP (the NV settings store) is deliberately not included** — it holds the owner's Bluetooth
  address, serial numbers, `authorization_code` and Apple pairing key. The image contains no device
  identifiers.
* The `CONFIG` header's chip-name field (`+0x16`) is **empty**: it is not stored in flash and no
  reference 377H3 `.up` has been seen. Fill it before using with any tool that checks it.
* This was never produced by StarFun's server; `package=h3promax3` still returns `204 No Content`.

Do not flash this — or anything derived from it — without a recovery path.
