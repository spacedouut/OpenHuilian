"""Serial link to the buds over an RFCOMM/SPP port (pyserial).

Pair the buds to the host first, then point hl at the SPP device:
  Linux:   rfcomm bind /dev/rfcomm0 <btaddr> [channel]  -> --port /dev/rfcomm0
  Windows: the "Outgoing" COM port for the buds         -> --port COM6
  macOS:   /dev/cu.<name>-SPP or similar

The buds speak the same frames on UART; nothing here is OS-specific beyond the
port name.
"""
import sys

try:
    import serial
except ImportError:
    serial = None

BAUD = 115200


def open_link(port, baud=BAUD, timeout=1.5):
    if serial is None:
        sys.exit("pyserial is required: pip install pyserial")
    return serial.Serial(port=port, baudrate=baud, timeout=timeout)


def _read_reply(ser, want_cmd, timeout=3.0):
    """Read until a C0 reply for want_cmd arrives. Returns the raw reply."""
    import time
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
    """Send a 55AA frame (crc8 appended) and return the reply bytes (or b'')."""
    from . import proto
    ser.write(proto.with_crc8(frame))
    import time
    buf = bytearray()
    end = time.time() + timeout
    while time.time() < end:
        buf += ser.read(ser.in_waiting or 1)
        i = buf.find(0x55)
        if i >= 0 and len(buf) >= i + 4:
            return bytes(buf[i:])
    return b""
