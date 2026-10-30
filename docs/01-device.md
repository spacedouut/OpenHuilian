# 01 · The device: H3Pro Max3

## Identity

What StarFun's "More" screen shows. The app reads it live over Bluetooth (`C0 04` "product model")
and doesn't cache it.

| Field | Value |
|---|---|
| Product number | `H3Pro Max3` |
| Chip model | `H3Pro` |
| Manufacturer | `377Youth·心动版` |
| Firmware version | `2607061716` (build stamp 2026-07-06 17:16) |

The same screen shows a production date and the bud's Bluetooth MAC, which differ per pair.

Replica-community naming: "V5.4 = Huilian 377", "V7 = Huilian 377H3". The `H3Pro` / `377Youth`
strings match 377H3.

Use StarFun **2.0.7.016**. 2.0.7.017 refuses these buds with "This device is not supported, please
replace it" ([02](02-starfun-app.md)).

## The OTA check

Tapping **Check Firmware** sends:

```
GET https://ota.starfun.fun/api/v1/_/appversions/update
      ?package=h3promax3
      &version=2607061716
      &deviceid=<the bud's Bluetooth MAC>
Authorization: <tenant JWT>

→ HTTP 204 No Content
```

* `package` is the product name lower-cased with spaces removed. That's the server key.
* **204 means "no update"**, not an auth failure. Other `version` values (including `0`) also get
  204, while known packages such as `a10` return JSON with a download URL.
* The catalog ([03](03-ota-catalog.md)) has no `h3promax3` entry, and its newest image (June 2025) is
  older than this firmware.

## Where firmware can come from

| Route | State |
|---|---|
| StarFun OTA server | Nothing for `h3promax3`. `tools/pull_ota.py h3promax3 2607061716` checks again. |
| Shenju OTA host `ota.shenjugroup.com` | Needs a per-product `firmware_id` and has no list endpoint; the only IDs in the app are for a smartwatch. |
| Read flash off the buds over Bluetooth | **Works.** `C0 83` reads 200 bytes at a time; the full 1 MiB takes about 16 minutes through the app (`tools/flashdump.py`, [16](16-live-flash-dump.md)). `tools/hl read` does the same without the app ([20](20-hl-cli.md)). The result is in `firmware/h3promax3/`. |
| UART boot ROM via the case pins | Untested, see [12](12-shenju-flasher.md). |
