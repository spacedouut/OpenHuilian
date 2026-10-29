"""Link to the buds: a serial port (pyserial) or a raw RFCOMM socket.

Port forms accepted by `--port`:
  AA:BB:CC:DD:EE:FF[:ch]  Bluetooth address, raw RFCOMM socket (Linux, no
                          pyserial, no `rfcomm bind`, no root). Default
                          channel 3, where the buds publish `SL_SPP`.
  /dev/rfcomm0, COM6, /dev/cu.*   serial device via pyserial

Both objects expose write(bytes), read(n), in_waiting and close(), which is all
the protocol layer uses. The buds hold one SPP session at a time: the phone's
Bluetooth has to be off while a computer talks to them.
"""
import re
import socket
import sys
import time

try:
    import serial
except ImportError:
    serial = None

BAUD = 115200
SPP_CHANNEL = 3
_BTADDR = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}(:\d+)?$")


class RfcommLink:
    """socket(AF_BLUETOOTH, SOCK_STREAM, BTPROTO_RFCOMM) with a pyserial-like face."""

    def __init__(self, addr, channel=SPP_CHANNEL, timeout=1.5):
        self.sock = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM,
                                  socket.BTPROTO_RFCOMM)
        self.sock.settimeout(10)
        self.sock.connect((addr, channel))
        self.timeout = timeout
        self._pending = bytearray()

    @property
    def in_waiting(self):
        return len(self._pending)

    def write(self, data):
        self.sock.sendall(data)

    def read(self, n=1):
        if n <= 0:
            return b""
        if len(self._pending) < n:
            self.sock.settimeout(self.timeout)
            try:
                self._pending += self.sock.recv(4096)
            except (socket.timeout, TimeoutError):
                pass
            except OSError:
                pass
        out = bytes(self._pending[:n])
        del self._pending[:n]
        return out

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def open_link(port, baud=BAUD, timeout=1.5):
    if _BTADDR.match(port):
        parts = port.split(":")
        addr = ":".join(parts[:6])
        ch = int(parts[6]) if len(parts) > 6 else SPP_CHANNEL
        return RfcommLink(addr, ch, timeout)
    if serial is None:
        sys.exit("pyserial is required for serial ports: pip install pyserial "
                 "(or pass a Bluetooth address for a raw RFCOMM socket)")
    return serial.Serial(port=port, baudrate=baud, timeout=timeout)


def reopen(port, baud=BAUD, tries=30, delay=2.0):
    """Poll until the link opens again (the bud reboots after OTA steps)."""
    last = None
    for _ in range(tries):
        try:
            return open_link(port, baud)
        except Exception as e:  # EBUSY / EHOSTDOWN while the bud is away
            last = e
            time.sleep(delay)
    sys.exit(f"link did not come back: {last}")


def _read_reply(ser, want_cmd, timeout=3.0):
    """Read until a C0 reply for want_cmd arrives. Returns the raw reply."""
    buf = bytearray()
    end = time.time() + timeout
    while time.time() < end:
        buf += ser.read(ser.in_waiting or 1)
        i = buf.find(0xC0)
        if i < 0:
            continue
        if len(buf) >= i + 3 and buf[i + 1] == want_cmd:
            # C0 83 replies carry addr(4) len(4) data; others carry a len byte
            if want_cmd == 0x83:
                if len(buf) >= i + 10:
                    n = int.from_bytes(buf[i + 6:i + 10], "little")
                    if len(buf) >= i + 10 + n:
                        return bytes(buf[i:i + 10 + n])
            else:
                n = buf[i + 2]
                if len(buf) >= i + 3 + n:
                    return bytes(buf[i:i + 3 + n])
        if len(buf) > 4096:
            del buf[: i if i > 0 else 1]
    return None


def c0(ser, cmd, payload=b"", timeout=3.0):
    from . import proto
    ser.write(proto.c0(cmd, payload))
    r = _read_reply(ser, cmd, timeout)
    return r


def read_flash(ser, addr, n, timeout=3.0):
    """C0 83: returns (addr, data) or None."""
    r = c0(ser, 0x83, __import__("struct").pack("<II", addr, n), timeout)
    if r is None or len(r) < 10:
        return None
    a = int.from_bytes(r[2:6], "little")
    ln = int.from_bytes(r[6:10], "little")
    data = r[10:10 + ln]
    if a != addr or len(data) != ln or ln == 0:
        return None
    return a, data


def read_flash_range(ser, addr, total, chunk=100, log=print):
    """Read a flash range via C0 83 (max 200 bytes/reply)."""
    out = {}
    pos = addr
    while pos < addr + total:
        n = min(chunk, addr + total - pos)
        r = read_flash(ser, pos, n)
        if r is None:
            log(f"  read @0x{pos:x} failed, retrying once")
            r = read_flash(ser, pos, n)
            if r is None:
                return None
        _, data = r
        out[pos] = data
        pos += len(data)
        if log and (pos - addr) % 4096 < chunk:
            log(f"  0x{pos - addr:x}/{total:x}")
    return b"".join(out[a] for a in sorted(out))


def ota_frame(ser, frame, timeout=3.0):
    """Send a 55AA frame (crc8 appended); return the reply frame for the same
    cmd as (side, status, payload, raw), or None on timeout.

    OTAP answers `55 AA <cmd> <side> <len> <payload> <crc8>` where <side> is
    the bud that answered (11/22) and payload[0] is the status (00 = ok).
    Spontaneous C0 frames (battery pushes) can arrive in between; skip them.
    """
    from . import proto
    ser.write(proto.with_crc8(frame))
    want = frame[2]
    buf = bytearray()
    end = time.time() + timeout
    while time.time() < end:
        buf += ser.read(ser.in_waiting or 1)
        i = 0
        while True:
            i = buf.find(b"\x55\xaa", i)
            if i < 0 or len(buf) < i + 5:
                break
            n = buf[i + 4]
            if len(buf) < i + 6 + n:
                break
            fr = bytes(buf[i:i + 6 + n])
            if fr[2] == want and proto.crc8(fr[:-1]) == fr[-1]:
                return OtaReply(fr)
            i += 1
        if len(buf) > 4096:
            del buf[:-64]
    return None


class OtaReply:
    def __init__(self, raw):
        self.raw = raw
        self.cmd = raw[2]
        self.side = raw[3]
        self.payload = raw[5:-1]
        self.status = self.payload[0] if self.payload else None

    def hex(self):
        return self.raw.hex()

    @property
    def ok(self):
        return self.status == 0
