#!/usr/bin/env python3
"""Render the Huilian H3Pro Max3 flash / address-space map as a PNG.
All numbers from the live image 2607061716 + docs/research.
Flash bar is to scale EXCEPT regions under 8 KB, which are expanded to a
minimum height for legibility (marked on the ruler).
"""
from PIL import Image, ImageDraw, ImageFont

W, H = 1640, 2360
M = 40
img = Image.new("RGB", (W, H), "#fafaf7")
d = ImageDraw.Draw(img)

FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
f_t = ImageFont.truetype(FB, 34)
f_s = ImageFont.truetype(FB, 21)
f_b = ImageFont.truetype(FB, 16)
f_r = ImageFont.truetype(FR, 15)
f_m = ImageFont.truetype(MONO, 14)
f_ms = ImageFont.truetype(MONO, 12)

INK = "#2b2b2b"
GRID = "#c9c5ba"


def text(x, y, s, font=f_r, fill=INK, anchor="la"):
    d.text((x, y), s, font=font, fill=fill, anchor=anchor)


def wrap(x, y, s, font, width, fill=INK, lh=4):
    words, line, yy = s.split(), "", y
    for w in words:
        t = (line + " " + w).strip()
        if d.textlength(t, font=font) <= width:
            line = t
        else:
            text(x, yy, line, font, fill)
            yy += font.size + lh
            line = w
    if line:
        text(x, yy, line, font, fill)
        yy += font.size + lh
    return yy


text(M, 24, "Huilian H3Pro Max3 (377H3) - flash & address-space map", f_t)
text(M, 66, "live image 2607061716 · addresses from the partition index + Ghidra analysis (docs/17-21)", f_r, "#666")

# ============ COLUMN 1: FLASH ============
FX, FY, FW, FH = M + 58, 130, 300, 1560
MINH = 30
scale = FH / 0x100000

text(FX, FY - 32, "FLASH  1 MiB", f_s)
text(FX + FW + 12, FY - 32, "(to scale; <8 KB regions expanded - marked *)", f_ms, "#888")

regions = [
    (0x00000, 0x03000, "HLKJ hdr + BOOT", "12 KB bootloader - byte-identical across all 25 images except 3 config bytes (0x1D/5C/5D = flash class)", "#b8c4e8"),
    (0x03000, 0x04000, "partition index", "4 KB page: count, version=2607061716, 6 x 16B records", "#8fd0a8"),
    (0x04000, 0x0ADC54, "FIRM", "695,380 B Thumb-2 · XIP at 0xC04000 · ~3.9k fns · AES sbox at FIRM+0xC4BFC6 · AAP SDP blob · DSP param tables", "#e8b0b0"),
    (0x0ADC54, 0x0AE000, None, "zero gap", "#e6e4dc"),
    (0x0AE000, 0x0AE808, "SENC", "2,056 B call-mic NR + sensor cal (pages 21-32) - same CRC 0x77AA as h2sturbo", "#e8d8a8"),
    (0x0AE808, 0x0AF000, None, "gap", "#e6e4dc"),
    (0x0AF000, 0x0C3BA7, "TONE", "84,903 B - 18 voice prompts, packed full (no room to grow)", "#c8b0e0"),
    (0x0C3BA7, 0x0C4000, None, "~1 KiB slack", "#e6e4dc"),
    (0x0C4000, 0x0C504C, "EQ2P", "4,172 B - SLEQ v2, 7 profiles; kinds 51-57 (ANC) never read", "#a8d8d8"),
    (0x0C504C, 0x0D2000, None, "zero padding", "#f0eee7"),
    (0x0D2000, 0x0FAD50, "OTAP", "167,248 B updater - linked to run from RAM 0x804800; .up EOF is here (0xFAD50)", "#e8a8a0"),
    (0x0FAD50, 0x0FB000, None, "688 B gap", "#e6e4dc"),
    (0x0FB000, 0x0FC000, "55AA flag", "AA 55 00 00 = reboot into OTAP; set by FIRM, cleared by OTAP", "#f0c8a0"),
    (0x0FC000, 0x100000, "PSMP", "16 KiB NV store (log-structured): bt_addr, device_id, authorization_code, air_adv_key... per-unit - ON DEVICE ONLY, never in the .up", "#b0e0b0"),
]

layout = []
for a0, a1, name, note, col in regions:
    h = (a1 - a0) * scale
    expanded = False
    if name and h < MINH:
        h, expanded = float(MINH), True
    if not name and h < 6:
        h = 6.0
    layout.append([a0, a1, name, note, col, h, expanded])

total_h = sum(r[5] for r in layout)
ytop = FY


def y_of(addr):
    y = 0.0
    for a0, a1, name, note, col, h, exp in layout:
        if addr <= a0:
            break
        if addr >= a1:
            y += h
            continue
        y += h * (addr - a0) / (a1 - a0)
        break
    return ytop + y

for a in range(0, 0x100001, 0x10000):
    y = y_of(a)
    d.line([FX - 6, y, FX, y], fill="#999")
    text(FX - 10, y - 6, f"{a:05X}", f_ms, "#888", "ra")

d.rectangle([FX - 1, ytop - 1, FX + FW + 1, ytop + total_h + 1], outline="#aaa")

LX = FX + FW + 14
for a0, a1, name, note, col, h, exp in layout:
    y0 = y_of(a0)
    y1 = y_of(a1)
    d.rectangle([FX, y0, FX + FW, y1], fill=col, outline=GRID)
    label = (name or note)
    if exp:
        label += " *"
    if name:
        ty = y0 + (h - 16) / 2 if h < 40 else y0 + 6
        text(LX, ty, label, f_b)
    else:
        text(LX, y0 + (h - 14) / 2, label, f_ms, "#888")
    if name and h >= 44:
        wrap(LX, y0 + 26, note, f_ms, 360, "#555")

# free-space note under the flash bar
text(FX, ytop + total_h + 14, "All in-image gaps are 00 padding (build tool). The ~53 KB between EQ2P and", f_ms, "#555")
text(FX, ytop + total_h + 30, "OTAP is claimable by CFW: repartition FIRM/SENC/TONE/EQ2P within 0x4000..0xD2000,", f_ms, "#555")
text(FX, ytop + total_h + 46, "rewrite index + CRCs; OTAP/PSMP records are pinned by the updater.", f_ms, "#555")

# ============ COLUMN 2: CPU address spaces ============
CX = LX + 390
text(CX, FY - 32, "CPU address spaces", f_s)

spaces = [
    ("MASK ROM  0x00000000+", [
        ("0x0B2A-0x0C74", "libc: memcpy/memset/memcmp/strlen/strcmp/malloc/free", "#d0d0e8"),
        ("0x1720/24", "enter/exit critical section pair", "#d0d0e8"),
        ("0x1A90, 0x2A7C", "queue/event + timer helpers", "#d0d0e8"),
        ("0x9E3C-0xB78C", "RTOS + flash rd/wr wrappers + sleep(ms)", "#d0d0e8"),
        ("0x11000-0x13100", "BT host helpers (big band)", "#c0c8e8"),
        ("0x2348-0x31000", "BT stack band (L2CAP/RFCOMM/SDP glue)", "#c0c8e8"),
        ("0x3D520-0x4B2AC", "A2DP/audio + more BT - 467 targets total from FIRM", "#b0bce8"),
    ]),
    ("SRAM  0x00800000+  (~490 KiB+)", [
        ("0x804800", "OTAP linked here - runs entirely from RAM", "#f0c0b8"),
        ("0x804C40", "FIRM hot code + vectors (4 KiB, copied by BOOT)", "#e8b8b8"),
        ("0x805C40", "FIRM .data (copied by FIRM startup)", "#e8c8b8"),
        ("0x82CA2C", ".bss + heaps -> stack top 0x879820", "#e8d8c8"),
        ("0x850000", "UART RAM-loader target (factory path, COM.dll)", "#d8e8d8"),
        ("0x860000", "BOOT while running (before FIRM loads)", "#b8c4e8"),
    ]),
    ("XIP window  0x00C00000+  (flash mirrored)", [
        ("0xC04000", "FIRM partition executes here (flash 0x04000 + 0xC00000)", "#e8b8b8"),
        ("0xC04000-0xCADC54", "whole FIRM visible; most code runs XIP", "#efc8c8"),
        ("0xCADC54", "end of mapped flash", "#e6e4dc"),
    ]),
]

yy = FY
for title, rows in spaces:
    text(CX, yy, title, f_b)
    yy += 26
    for addr, note, col in rows:
        d.rectangle([CX, yy, CX + 330, yy + 40], fill=col, outline=GRID)
        text(CX + 8, yy + 4, addr, f_ms)
        wrap(CX + 8, yy + 20, note, f_ms, 314, "#555")
        yy += 46
    yy += 20

# ============ COLUMN 3: boot flow + container + rules ============
BX = CX + 360
BW = W - BX - M

text(BX, FY - 32, "Boot flow", f_s)
flow = [
    ("mask ROM (0x00000000)", "#e8e0d0"),
    ("v  clock/periph init", "#f0e8d8"),
    ("v  strap check FUN_008605F2", "#f0e8d8"),
    ("   strap set -> download/wait loop (factory UART/USB)", "#f0e8d8"),
    ("v  read partition index @ flash 0x3000", "#f0e8d8"),
    ("v  word @ 0xFB000 == 0x000055AA ?", "#f0e8d8"),
    ("   yes -> OTAP   /   no -> FIRM", "#f0c8b8"),
    ("v  read 0x30-byte part header, copy block to RAM", "#f0e8d8"),
    ("v  jump entry (0x804C41, Thumb)", "#f0e8d8"),
]
by = FY
for s, col in flow:
    d.rounded_rectangle([BX, by, BX + BW, by + 30], 6, fill=col, outline=GRID)
    text(BX + 10, by + 7, s, f_ms)
    by += 38

by += 14
text(BX, by, "The .up container (what StarFun streams)", f_s)
by += 26
for addr, note, col in [
    ("0x000-0x100", "CONFIG header: body len @0x10, CRC16 @0x14, chip name @0x16, 55 AA @0xFE", "#c8d8f0"),
    ("0x100+", "body = verbatim flash image (file_offset = flash_addr + 0x100)", "#d8e8d8"),
]:
    d.rounded_rectangle([BX, by, BX + BW, by + 46], 6, fill=col, outline=GRID)
    text(BX + 10, by + 4, addr, f_ms)
    wrap(BX + 10, by + 20, note, f_ms, BW - 20, "#555")
    by += 54

by += 8
text(BX, by, "Acceptance rules (the whole security model)", f_s)
by += 26
for s in [
    "BOOT: checks nothing (no CRC16 code at all)",
    "OTAP: one CRC16/CCITT-FALSE over 0x3000..OTAP vs the\nCRC the phone declares in 82; OTAP+PSMP records pinned",
    "no signature, no chip-name check, no version check",
    "83 data writes: NO address bounds check (guard CRC only\nnotices bootloader changes after the fact)",
]:
    lines = s.split("\n")
    hgt = 12 + 17 * len(lines)
    d.rounded_rectangle([BX, by, BX + BW, by + hgt], 6, fill="#f8e8e8", outline=GRID)
    yy2 = by + 6
    for line in lines:
        text(BX + 10, yy2, line, f_ms)
        yy2 += 17
    by += hgt + 8

by += 8
text(BX, by, "Command channels (while FIRM runs)", f_s)
by += 26
for head, note in [
    ("C0 <cmd> ...", "StarFun app channel - behind LFSR auth (01/02, poly D103)"),
    ("55 AA 8x ...", "OTA frames (80-84) + 04 exit - no auth gate"),
    ("+test=...", "8 text cmds over SPP/UART (recover/version/shutdown/...)"),
    ("AT+... / +ANC*", "HFP + ANC tuning (+ANCTEST/FFG/FBG/AG/DG, +MICTEST, +NTC)"),
    ("05 ...", "TWS peer (bud-to-bud) protocol"),
]:
    d.rounded_rectangle([BX, by, BX + BW, by + 42], 6, fill="#e8e8f4", outline=GRID)
    text(BX + 10, by + 4, head, f_ms)
    wrap(BX + 10, by + 20, note, f_ms, BW - 20, "#555")
    by += 50

text(M, H - 28, "Biscut · 2026-10-29 · static analysis of files, nothing written to hardware · numbers: docs/16-21 + ~/tmp/oh-dump", f_ms, "#999")

import sys as _sys
img.save(_sys.argv[1] if len(_sys.argv) > 1 else "/home/ubuntu/tmp/oh-flash-map.png")
print("saved, flash bar height:", total_h)
