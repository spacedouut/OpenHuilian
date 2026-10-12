# 10 · AAP / AirPods emulation surface

Read statically from `h2s_turbo_2506281656.up` FIRM (377-generation SL6801 build), compared with
the 2409191721 build. Nothing here was observed on the H3Pro Max3 itself. Full narrative report:
[`data/reports/aap_anc_body.html`](../data/reports/aap_anc_body.html); decoder:
[`tools/sdp_hid.py`](../tools/sdp_hid.py).

## What it is

A real Apple Accessory Protocol server, not a spoofed name. It's published over SDP on its own
L2CAP PSM, with two Apple accessory HID services (one of them a head-motion service that's new in
the 377 build), a BLE proximity-pairing advertisement, and the Apple HFP extensions.
**[confirmed]** The AAP opcode handling itself is code rather than tables, so how complete it is
next to real AirPods is **[unverified]**.

## SDP records (FIRM 0x55000–0x55930) — [confirmed]

| Record | Identity | Transport |
|---|---|---|
| **AAP Server** | service UUID `74ec2172-0bad-4d01-8f77-997b2be0722a`, profile UUID `4b6f7c74-07f4-49de-b0b9-ab4304728f29` v1.0 | **L2CAP PSM 0x1001** |
| **Device ID (PnP)** | vendor `0x004C` (Apple), products `0x2014` and `0x200F`, versions `0xE415` / `0xD415` | SDP attribute |
| **Accessory identity blob** | vendor `0x05AC`, `SerialNumber GX1H9C05KE90000B31` (one hardcoded string → every unit reports the same serial), `CFG# B768/MP/2430RYUK/*/*`, `ProtectedAccess`, `ProtUpdate`, `PrimaryVendorUsages 0xFF0C/0x0D`, `H2HTransformation`, `LocationID` | SDP attribute `0xA001` |

## HID report descriptors embedded in the identity blob — [confirmed]

**`devmotion6`** (96-byte descriptor, max report 191 B) — head-motion sensor service, **377 build only**
* Report 1 input: 64-bit field (page `0xFF15` usage 4) + 1456-bit vendor field (`0xFF0C`/`0x0D`) — the motion payload
* Report 2 input: `0xFF0C`/`0x0E`
* Feature reports on HID Sensors page `0x20`: usages `0x030E`, `0x031B`, `0x031A`
* Report `0xFF`: 224-byte vendor feature blob

**`AVClient`** (67-byte descriptor, max report 70 B)
* Report 1 input: 552-bit field; reports 2–4: 8, 16, 8 bits
* Feature `0x030E` (32-bit) on reports 1 and 2

## BLE proximity pairing — [confirmed bytes, inferred meaning]

One Continuity advertisement template at FIRM `0x591E0` (identical in both builds):

```
1E FF 4C00 07 19 01 0E20 75 00 00 31 00 10 00…00
 │  │  │    │  │  │    │     │  │  │  │  │  └ 16 zero bytes, filled at runtime
 │  │  │    │  │  │    │     │  │  │  │  └ colour
 │  │  │    │  │  │    │     │  │  │  └ lid-open counter
 │  │  │    │  │  │    │     │  │  └ case battery / charging
 │  │  │    │  │  │    │     │  └ L/R battery nibbles
 │  │  │    │  │  │    │     └ status
 │  │  │    │  │  │    └ device model 0x0E20 = AirPods Pro (gen 1)
 │  │  │    │  │  └ prefix
 │  │  │    │  └ payload length 25
 │  │  │    └ Continuity type 0x07 = proximity pairing
 │  │  └ Apple company ID 0x004C
 │  └ manufacturer-specific data
 └ AD length 30
```

Those two model bytes decide the iOS pop-up artwork and name. The string table already has
`AirPods`, `AirPods Pro` and `AirPods Pro2`, and the SDP product `0x2014` is the AirPods Pro 2 ID,
yet the advertisement still claims gen 1.

## HFP — [confirmed]

`AT+XAPL=0042-0887-0100,2` — feature bit 1 (battery reporting) is the only bit set. Also
`+APLSIRI:1` and `AT+BVRA` handling.

## What the 377 build added vs. the SL6800 build — [confirmed strings]

| New string | Reads as |
|---|---|
| `AccessoryService`, `ReportDescriptor`, `MaxReportSize` | the Apple accessory HID layer itself |
| `devmotion6` | head-motion sensor service |
| `H2HTransformation` | head-to-head transform (spatial audio orientation) |
| `taskB motion`, `air motion tx timer` | motion task + transmit timer |
| `UDEQ`, `eq_ud_gain`, `eq_preset_cur_num` | user-defined EQ (matches StarFun .017 changelog) |
| `AirPods` | new name variant |

Both builds already had the AAP server, SDP records, XAPL, Siri, and the advertisement.

## Plausible gaps for a CFW — [inferred]

* Stale model spoof: BLE `0x0E20` (Pro gen 1) against SDP `0x2014` (Pro 2). Two bytes.
* XAPL features = 2 (battery only); no case-battery or other feature bits.
* Shared serial number for every unit.
* No string/descriptor evidence of conversation awareness, adaptive audio, loud-sound reduction.
* Noise-control from Control Center: no AAP listen-mode handler found statically (opcodes are
  built in code).

Related: the `authorization_code` / `authorization_code_length` NV keys in FIRM ([09](09-psmp-nvds.md)).
