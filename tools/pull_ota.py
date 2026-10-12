#!/usr/bin/env python3
"""Download + inspect a StarFun/Shenju OTA .up firmware image.

Auth uses the tenant login that the StarFun APK carries internally
(see OtaPresenter.getUserToken in the decompiled app). The credentials are
deliberately NOT stored in this repo: export them as environment variables
STARFUN_USER and STARFUN_PASS before running.

Usage:
    python3 pull_ota.py <product_model> [current_version]
e.g. python3 pull_ota.py a10
     python3 pull_ota.py h3promax3 2607061716   # currently -> 204, no update
"""
import os, sys, json, struct, urllib.request

AUTH_URL = "https://ota.starfun.fun/api/v1/authentication/user"
LOOKUP   = "https://ota.starfun.fun/api/v1/_/appversions/update"
TIMEOUT  = float(os.environ.get("STARFUN_TIMEOUT", "60"))
CREDS    = {"username": os.environ.get("STARFUN_USER", ""),
            "password": os.environ.get("STARFUN_PASS", "")}
if not CREDS["username"] or not CREDS["password"]:
    sys.exit("set STARFUN_USER and STARFUN_PASS (see docs/02-starfun-app.md)")


def post(url, obj):
    req = urllib.request.Request(url, data=json.dumps(obj).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=TIMEOUT))


def get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": token})
    return urllib.request.urlopen(req, timeout=TIMEOUT).read()


def token():
    return post(AUTH_URL, CREDS)["tokenId"]


def lookup(model, version, tok):
    q = f"{LOOKUP}?package={model}"
    if version:
        q += f"&version={version}"
    raw = get(q, tok)
    return json.loads(raw) if raw else None


def parse_up(data):
    assert data[:6] == b"CONFIG", "not a .up (missing CONFIG magic)"
    chip = data[0x16:0x16 + 16].split(b"\0")[0].decode("latin1")
    body = data[0x100:]
    I = struct.unpack_from("<I", body, 0x20)[0]
    N = struct.unpack_from("<I", body, I)[0]
    ver = struct.unpack_from("<I", body, I + 4)[0]
    parts = []
    for k in range(1, N + 1):
        off = I + 16 * k
        tag = body[off:off + 4].decode("latin1")
        addr, length, crc = struct.unpack_from("<III", body, off + 4)
        parts.append((tag, addr, length, crc))
    return {"chip": chip, "version": ver, "index_off": I, "partitions": parts}


if __name__ == "__main__":
    model = sys.argv[1]
    version = sys.argv[2] if len(sys.argv) > 2 else None
    tok = token()
    info = lookup(model, version, tok)
    if not info:
        print(f"No update returned for package={model}"
              f"{' version='+version if version else ''} "
              "(unknown model, or already on latest).")
        sys.exit(1)
    print(json.dumps(info, indent=2))
    url = info["url"].replace("http:", "https:")
    fn = url.rsplit("/", 1)[-1]
    open(fn, "wb").write(get(url, tok))
    print(f"\nDownloaded {fn}")
    if fn.endswith(".up") or url.endswith(".up"):
        meta = parse_up(open(fn, "rb").read())
        print(f"chip={meta['chip']} version={meta['version']} "
              f"index@0x{meta['index_off']:x}")
        for tag, addr, length, crc in meta["partitions"]:
            print(f"  {tag:<5} addr=0x{addr:08x} len=0x{length:08x} crc=0x{crc:08x}")
