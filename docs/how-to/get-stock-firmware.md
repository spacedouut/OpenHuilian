# Get stock firmware

There is no H3Pro Max3 firmware on StarFun's server. The stock image in this repo,
`firmware/h3promax3/h3promax3_2607061716_live.up`, was read off a pair of buds. If your buds run a
different version, [dump your own](dump-firmware.md).

## Check the server for a new H3Pro build

```bash
export STARFUN_USER=... STARFUN_PASS=...
python3 tools/pull_ota.py h3promax3 2607061716
```

"No update returned" means the server has nothing for that version. The login is the app's own
tenant account. It isn't in this repo, but it can be pulled from the StarFun APK
(`OtaPresenter.getUserToken`).

## Download catalog images

```bash
python3 tools/pull_ota.py a10        # newest image for a package
```

The 24 public images are already in `firmware/starfun-catalog/`. They are all SL6801-class, for
other earbuds. They're useful for comparing formats, but **never flash them to H3Pro buds**. The
list is in [the app and its servers](../explanation/the-app-and-servers.md#the-public-catalog).
