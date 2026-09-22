#!/usr/bin/env python3
"""Decode the SDP record blob and Apple accessory HID report descriptors
embedded in a Huilian/SmartLink FIRM image.

usage: sdp_hid.py <firm.bin> <start_hex> <end_hex> [sdp|hid]   (default: sdp)"""
import sys, struct

def parse_de(b, i):
    """Parse one SDP data element. Returns (value, next_index)."""
    h = b[i]; t, s = h >> 3, h & 7
    i += 1
    if t == 0:
        return None, i
    if s == 5:
        n = b[i]; i += 1
    elif s == 6:
        n = struct.unpack_from('>H', b, i)[0]; i += 2
    elif s == 7:
        n = struct.unpack_from('>I', b, i)[0]; i += 4
    else:
        n = (0, 1, 2, 4, 8, 16)[s] if s < 5 else 0
    v = b[i:i+n]
    if t in (1, 2):
        return ('int', int.from_bytes(v, 'big', signed=(t == 2)), n), i+n
    if t == 3:
        if n == 2:
            return ('uuid16', f'0x{int.from_bytes(v,"big"):04x}'), i+n
        if n == 4:
            return ('uuid32', f'0x{int.from_bytes(v,"big"):08x}'), i+n
        h = v.hex()
        return ('uuid128', f'{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}'), i+n
    if t == 4:
        return ('str', v.decode('latin1')), i+n
    if t == 5:
        return ('bool', bool(v[0])), i+n
    if t in (6, 7):
        end, out = i+n, []
        while i < end:
            e, i = parse_de(b, i)
            out.append(e)
        return ('seq', out), end
    return ('url', v.decode('latin1')), i+n

HID_ITEMS = {
    (0, 0x8): 'Input', (0, 0x9): 'Output', (0, 0xA): 'Collection',
    (0, 0xB): 'Feature', (0, 0xC): 'EndCollection',
    (1, 0x0): 'UsagePage', (1, 0x1): 'LogicalMin', (1, 0x2): 'LogicalMax',
    (1, 0x3): 'PhysicalMin', (1, 0x4): 'PhysicalMax', (1, 0x5): 'UnitExp',
    (1, 0x6): 'Unit', (1, 0x7): 'ReportSize', (1, 0x8): 'ReportID',
    (1, 0x9): 'ReportCount', (1, 0xA): 'Push', (1, 0xB): 'Pop',
    (2, 0x0): 'Usage', (2, 0x1): 'UsageMin', (2, 0x2): 'UsageMax',
}

def hid_decode(b):
    i, depth, out = 0, 0, []
    while i < len(b):
        p = b[i]; i += 1
        if p == 0xFE:
            if i + 2 > len(b):
                raise ValueError('truncated HID long item header')
            size, ltag = b[i], b[i + 1]
            i += 2
            if i + size > len(b):
                raise ValueError('truncated HID long item payload')
            out.append('  ' * max(depth, 0) + f'LongItem tag=0x{ltag:02x} {b[i:i+size].hex()}')
            i += size
            continue
        sz = p & 3
        sz = 4 if sz == 3 else sz
        t, tag = (p >> 2) & 3, p >> 4
        d = int.from_bytes(b[i:i+sz], 'little'); i += sz
        name = HID_ITEMS.get((t, tag), f'item(t={t},tag=0x{tag:x})')
        if name == 'EndCollection':
            depth -= 1
        out.append('  ' * max(depth, 0) + f'{name} 0x{d:0{sz*2}x}' + (f' ({d})' if sz else ''))
        if name == 'Collection':
            depth += 1
    return '\n'.join(out)

def main():
    f = open(sys.argv[1], 'rb').read()
    start = int(sys.argv[2], 16)
    end = int(sys.argv[3], 16)
    b = f[start:end]
    mode = sys.argv[4] if len(sys.argv) > 4 else 'sdp'
    if mode == 'hid':
        print('=== HID report descriptor ===')
        print(hid_decode(b))
        return
    i = 0
    print('=== SDP data elements ===')
    while i < len(b) - 2:
        try:
            v, j = parse_de(b, i)
        except Exception:
            break
        if v is None or j <= i:
            break
        print(f'{start+i:06x}  {v}')
        i = j

if __name__ == '__main__':
    main()
