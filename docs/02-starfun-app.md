# 02 · The StarFun app (`com.fun.app`)

StarFun is the generic control app for Huilian TWS products. Two builds were decompiled with
JADX; the parts that matter are archived in [`reference/starfun-app/`](../reference/starfun-app/).

## Versions

| Version | Behaviour with H3Pro Max3 | Catalog note (from the app's own update feed) |
|---|---|---|
| **2.0.7.016** | Works: connects, shows device info, fires the OTA check | `匹配377H3机型使用` — "for 377H3 models" |
| 2.0.7.017 | "This device is not supported, please replace it" | `增加EQ调节（仅支持个别机型）` — "adds EQ adjust (only some models)" |

The app self-update endpoint pushes .017 as "suggested". Stay on .016 for these buds.

## Servers and endpoints

| Host | Purpose | Auth |
|---|---|---|
| `https://ota.starfun.fun` | Firmware/APK catalog. `POST /api/v1/authentication/user` → JWT; `GET /api/v1/_/appversions` (list, 30 records); `GET /api/v1/_/appversions/update?package=&version=&deviceid=` (per-device check) | Tenant login baked into the APK (`OtaPresenter.getUserToken`). Tenant name `yiguo` appears in every download URL path. |
| `https://api.starfun.fun` | Main app API (accounts etc.) | user JWT |
| `https://info-api.starfun.fun` | New in .017: `/api/client/query?id=` — unused, returns empty for everything | none |
| `https://ota.shenjugroup.com` | Shenju OTA v2. Public Swagger at `/v2/api-docs` (saved as [`data/catalog/shenju_api.json`](../data/catalog/shenju_api.json)). Endpoints: `release/auth`, `release/last`, `release/report`. No list endpoint; keyed by `firmware_id`. The IDs hardcoded in the app belong to a smartwatch (`w10_watch_2.0.4.up`). | app_id/app_secret from APK, no user login |

Download URLs look like
`https://ota.starfun.fun/api/data/update/yiguo/<package>/up/<file>.up` and need the JWT (the catalog
returns `http://`; `tools/pull_ota.py` upgrades it to `https://` before sending the token).
Directory listing on the CDN is 403; guessing `h3promax3` paths gives 404.

> The tenant username/password are **not** in this repo. `tools/pull_ota.py` reads
> `STARFUN_USER` / `STARFUN_PASS` from the environment. They can be recovered from the APK
> (`OtaPresenter.getUserToken`) if needed.

## The hidden local-file OTA path

Both .016 and .017 ship a **dormant** route to flash a `.up` from local storage, not wired to any
visible button:

```java
// com/sjbt/base/ui/SettingMoreActivity.java
private void chooseFile() {
    Intent intent = new Intent("android.intent.action.GET_CONTENT");
    intent.addCategory(Intent.CATEGORY_OPENABLE);
    intent.setType("*/*");
    startActivityForResult(Intent.createChooser(intent, getString(R.string.choose_file)), 100);
}
// onActivityResult(100, …) reads the picked .up, preserves the device's EQ/TONE data,
// and hands it to BtOtaHelper — the same transport used for server OTAs.
```

See `reference/starfun-app/2.0.7.017/SettingMoreActivity.java` around lines 613–651.
So the H3Pro `.up` rebuilt from the live dump ([16](16-live-flash-dump.md)) could be pushed with the app's own transport by a one-line patch
that exposes `chooseFile()`, with no server involved. That's read from the code; nobody has tried it.

## Command channel security

`CMDConfig.java` has `encryptData` / `verificationCmd`: a keyed challenge/response, implemented in
a native `.so`, that unlocks the `C0` command channel. It is **not** a check on the firmware image.
Whether OTA frames are accepted without passing this handshake hasn't been tested.

## Interesting command IDs seen

| Cmd | Meaning |
|---|---|
| `C0 04` | read product model (→ `proModel_04`) |
| `C0 09` | battery poll (sent every 2 s during OTA) |
| `C0 83` | flash read — app uses it to pull EQ2P/TONE off the buds before an OTA |
| `55AA 80–84` | OTA frames — see [06](06-bt-ota-protocol.md) |

The firmware side of the whole `C0` set, about sixty commands, is tabled in
[18](18-firm-walkthrough.md).

## Data model hints

* `Eq2ItemType` reserves page IDs **51–57** for ANC / talk-through filter pages (never populated
  in any public image — [11](11-anc-transparency.md)).
* Local EQ store has scheme families `TYPE_EQ=1, TYPE_ANC=2, TYPE_ENC=3, TYPE_ANC_2=4`, and
  `EqScheme.isAnc` — explains the duplicated profile in EQ2P ([08](08-eq2p-senc.md)).
* `AncCalRespParam`, `CurveAncAssist`, `CurveAncReference` and `EqCoeffAnc` model classes exist,
  holding frequency lists, amplitude/phase curves and biquad coefficients. There's an ANC
  calibration UI somewhere in the vendor's world.
