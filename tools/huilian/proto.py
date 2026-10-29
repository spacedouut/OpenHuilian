"""StarFun/Shenju wire protocol for the H3Pro / 377H3 buds.

Two frame families on the same SPP/UART channel:
  - C0 commands:  `C0 <cmd> <payload>` -> reply `C0 <cmd> <len> <payload>`
    (C0 83 flash read replies instead carry `C0 83 <addr4><len4><data>`)
  - 55AA OTA frames: `55 AA <cmd> ... <crc8>`, CRC8/Maxim over everything after 55AA

The C0 01/02 "auth" is an obfuscation handshake: the app sends random
challenges, the bud scrambles and echoes them back. Unauthorized units (no
`authorization_code` in PSMP that descrambles to "APP") ignore C0 01 at all,
so a reply is itself the authorization check.
"""
import struct


def crc16(data, crc=0xFFFF):
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def crc8(data):
    """CRC8/Maxim (poly 0x31 reflected), as used on 55AA frames."""
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0x8C if crc & 1 else crc >> 1
    return crc


# --- the authorization-code scrambler (FIRM FUN_00c7144c/64/92) ---------------
# 16-bit LFSR, one clock per input bit; output byte = input XOR keystream where
# keystream bit i (MSB first) is the LFSR's top bit before clock i.
# Self-inverting: the same call scrambles or descrambles.

def lfsr_step(s):
    return (((s << 1) | (s >> 15)) ^ (0xD103 if s & 0x8000 else 0)) & 0xFFFF


def scramble(buf, seed):
    out = bytearray(len(buf))
    s = seed & 0xFFFF
    for i, b in enumerate(buf):
        r = 0
        for bit in range(7, -1, -1):
            r = ((r << 1) | (((b >> bit) ^ (s >> 15)) & 1)) & 0xFF
            s = lfsr_step(s)
        out[i] = r
    return bytes(out), s


def challenge1():
    """Request body for C0 01: the app sends `C0 01 3D` + 61 bytes
    (CMDConfig.getHandshakeCmd). The bud rejects a body that is all 0x00
    or all 0xFF (FUN_00c69958 counts over req[3..0x3f])."""
    import os
    body = bytearray(os.urandom(61))
    while all(b == 0 for b in body) or all(b == 0xFF for b in body):
        body = bytearray(os.urandom(61))
    return bytes(body)


def challenge2():
    """Request body for C0 02, sent as `C0 02 3D` + 61 bytes. The bud rejects
    req[0x10..0x2f] all 0x00 or all 0xFF, and req[0x30..0x3f] all 0x00 or
    all 0xFF (FUN_00c699a6). req indices are full-frame; body starts at +3."""
    import os
    while True:
        b = bytearray(os.urandom(61))
        mid = b[0x10 - 3:0x30 - 3]
        tail = b[0x30 - 3:0x40 - 3]
        ok = not (all(x == 0 for x in mid) or all(x == 0xFF for x in mid))
        ok = ok and not (all(x == 0 for x in tail) or all(x == 0xFF for x in tail))
        if ok:
            return bytes(b)


def c002_reply(req):
    """The bud's 61-byte reply body for a C0 02 request, per FUN_00c699a6.
    `req` is the full request frame (`C0 02 3D` + 61 bytes). Useful to verify
    a live exchange the way StarFun does."""
    r = bytearray(req[:0x40])
    seg, _ = scramble(bytes(r[3:0x10]), (req[5] << 8 | req[6]) ^ 0x1728)
    r[3:0x10] = seg
    seg, _ = scramble(bytes(r[0x10:0x30]), req[0xE] << 8 | req[0xF])
    r[0x10:0x30] = seg
    for i in range(0x10):
        r[0x10 + i] ^= req[0x10 + i]
        r[0x20 + i] ^= req[0x10 + i]
    seg, _ = scramble(bytes(r[0x10:0x30]), sum(req[0x10:0x30]))
    r[0x10:0x30] = seg
    seg, _ = scramble(bytes(r[0x30:0x40]), (req[0x36] << 8 | req[0x39]) ^ 0x358)
    r[0x30:0x40] = seg
    return bytes(r[3:0x40])


# --- frame builders -----------------------------------------------------------

def c0(cmd, payload=b""):
    return bytes([0xC0, cmd]) + payload


def c0_read_flash(addr, n):
    return c0(0x83, struct.pack("<II", addr, n))


def ota_enter(side=0x33):
    return bytes([0x55, 0xAA, 0x80, side, 0x00])


def ota_prepare(side=0x33):
    return bytes([0x55, 0xAA, 0x81, side, 0x00])


def ota_finalize(side=0x33):
    return bytes([0x55, 0xAA, 0x84, side, 0x00])


def ota_leave(side=0x33):
    """55AA 04: clear the boot-to-OTAP flag and reboot into FIRM. Required
    after a `00` finalize; without it both buds stay in the updater."""
    return bytes([0x55, 0xAA, 0x04, side, 0x00])


def ota_declare(payload, side=0x33):
    """55AA 82: declares the CRC16 (CCITT-FALSE, padded to 4B) and length of the
    whole payload region about to be written."""
    f = bytes([0x55, 0xAA, 0x82, side, 0x08])
    f += struct.pack("<I", crc16(payload)) + struct.pack("<I", len(payload))
    return f


def ota_write(addr, data):
    f = bytes([0x55, 0xAA, 0x83])
    f += struct.pack("<HII", len(data) + 8, addr, len(data)) + data
    return f


def with_crc8(frame):
    """55AA frames carry a trailing CRC8/Maxim over the whole frame
    including the '55AA' marker (OtaCmdConfig.addOtaData)."""
    assert frame[0] == 0x55 and frame[1] == 0xAA
    return frame + bytes([crc8(frame)])
