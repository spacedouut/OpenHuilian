// StarFun/Shenju wire protocol, JS port of tools/huilian/proto.py.
// C0 commands: `C0 <cmd> <payload>` -> reply `C0 <cmd> <len> <payload>`
// (C0 83 replies carry `C0 83 <addr4><len4><data>`).
// 55AA OTA frames: `55 AA <cmd> ... <crc8/Maxim over whole frame>`.

export function crc16(data, crc = 0xFFFF) {
  for (const b of data) {
    crc ^= b << 8;
    for (let i = 0; i < 8; i++)
      crc = crc & 0x8000 ? ((crc << 1) ^ 0x1021) & 0xFFFF : (crc << 1) & 0xFFFF;
  }
  return crc;
}

export function crc8(data) {
  let crc = 0;
  for (const b of data) {
    crc ^= b;
    for (let i = 0; i < 8; i++)
      crc = crc & 1 ? (crc >> 1) ^ 0x8C : crc >> 1;
  }
  return crc;
}

// The authorization-code scrambler: 16-bit LFSR, one clock per input bit,
// XOR keystream. Self-inverting.
export function lfsrStep(s) {
  return ((((s << 1) | (s >> 15)) ^ (s & 0x8000 ? 0xD103 : 0)) & 0xFFFF) >>> 0;
}

export function scramble(buf, seed) {
  const out = new Uint8Array(buf.length);
  let s = seed & 0xFFFF;
  for (let i = 0; i < buf.length; i++) {
    let r = 0;
    for (let bit = 7; bit >= 0; bit--) {
      r = ((r << 1) | (((buf[i] >> bit) ^ (s >> 15)) & 1)) & 0xFF;
      s = lfsrStep(s);
    }
    out[i] = r;
  }
  return [out, s];
}

function nondegenerate(n) {
  const b = crypto.getRandomValues(new Uint8Array(n));
  if (b.every(x => x === 0) || b.every(x => x === 0xFF)) return nondegenerate(n);
  return b;
}

export const challenge1 = () => nondegenerate(61);

export function challenge2() {
  while (true) {
    const b = nondegenerate(61);
    const mid = b.slice(0x0D, 0x2D), tail = b.slice(0x2D, 0x3D);
    const deg = a => a.every(x => x === 0) || a.every(x => x === 0xFF);
    if (!deg(mid) && !deg(tail)) return b;
  }
}

// The bud's 61-byte reply body for a C0 02 request (FUN_00c699a6).
// `req` is the full request frame (`C0 02 3D` + 61 bytes).
export function c002Reply(req) {
  const r = Uint8Array.from(req.slice(0, 0x40));
  const scr = (from, len, seed) => {
    const [seg] = scramble(r.slice(from, from + len), seed);
    r.set(seg, from);
  };
  scr(3, 0x0D, ((req[5] << 8) | req[6]) ^ 0x1728);
  scr(0x10, 0x20, (req[0x0E] << 8) | req[0x0F]);
  for (let i = 0; i < 0x10; i++) {
    r[0x10 + i] ^= req[0x10 + i];
    r[0x20 + i] ^= req[0x10 + i];
  }
  scr(0x10, 0x20, req.slice(0x10, 0x30).reduce((a, b) => a + b, 0));
  scr(0x30, 0x10, ((req[0x36] << 8) | req[0x39]) ^ 0x358);
  return r.slice(3, 0x40);
}

export const c0 = (cmd, payload = new Uint8Array(0)) =>
  Uint8Array.from([0xC0, cmd, ...payload]);

export const le32 = n => {
  const b = new Uint8Array(4);
  new DataView(b.buffer).setUint32(0, n >>> 0, true);
  return b;
};
const le16 = n => {
  const b = new Uint8Array(2);
  new DataView(b.buffer).setUint16(0, n & 0xFFFF, true);
  return b;
};

export const c0ReadFlash = (addr, n) => c0(0x83, Uint8Array.from([...le32(addr), ...le32(n)]));

const ctl = cmd => Uint8Array.from([0x55, 0xAA, cmd, 0x33, 0x00]);
const ctlSide = (cmd, side) => Uint8Array.from([0x55, 0xAA, cmd, side, 0x00]);

export const otaEnter = side => ctlSide(0x80, side);
export const otaPrepare = side => ctlSide(0x81, side);
export const otaFinalize = side => ctlSide(0x84, side);
// 55AA 04: clear the boot-to-OTAP flag and reboot into FIRM. Required after a
// 00 finalize; without it both buds stay in the updater.
export const otaLeave = side => ctlSide(0x04, side);

export function otaDeclare(payload, side = 0x33) {
  const f = [0x55, 0xAA, 0x82, side, 0x08];
  return Uint8Array.from([...f, ...le32(crc16(payload)), ...le32(payload.length)]);
}

export function otaWrite(addr, data) {
  return Uint8Array.from([0x55, 0xAA, 0x83,
    ...le16(data.length + 8), ...le32(addr), ...le32(data.length), ...data]);
}

export function withCrc8(frame) {
  const out = new Uint8Array(frame.length + 1);
  out.set(frame);
  out[frame.length] = crc8(frame);
  return out;
}

// --- .up container (port of upfmt + the app's getUploadContent) --------------
export const UP_BODY = 0x100;

export function indexOffset(body) {
  return new DataView(body.buffer, body.byteOffset).getUint32(0x20, true);
}

export function parseIndex(body, io = indexOffset(body)) {
  const dv = new DataView(body.buffer, body.byteOffset);
  const count = dv.getUint32(io, true), version = dv.getUint32(io + 4, true);
  const entries = [];
  for (let i = 0; i < count; i++) {
    const o = io + 16 + 16 * i;
    const tag = String.fromCharCode(...body.slice(o, o + 4));
    entries.push({ tag, addr: dv.getUint32(o + 4, true), len: dv.getUint32(o + 8, true), crc: dv.getUint32(o + 12, true), off: o });
  }
  return { version, entries };
}

// OTAP (docs/research/updater-otap.md) erases 0x4000..0x3000+total on 82, writes 83 frames at any
// address, and CRCs flash[0x3000:0x3000+total]; its OTAP/PSMP records are
// pinned. Port of upfmt.ota_image_problems: reasons not to stream an image.
export const OTA_INDEX_ADDR = 0x3000, OTA_FIRM_ADDR = 0x4000, OTA_INDEX_MAX = 0x80;

export function otaImageProblems(upBytes) {
  if (String.fromCharCode(...upBytes.slice(0, 6)) !== "CONFIG") return ["not a .up (missing CONFIG magic)"];
  const body = upBytes.slice(UP_BODY);
  const hdr = new DataView(upBytes.buffer, upBytes.byteOffset);
  const bad = [];
  if (hdr.getUint32(0x10, true) !== body.length || crc16(body) !== hdr.getUint16(0x14, true))
    bad.push("CONFIG header length/CRC does not match the body");
  const io = indexOffset(body);
  if (io !== OTA_INDEX_ADDR) return [...bad, `index at 0x${io.toString(16)}; OTAP only handles an index at 0x3000`];
  const { entries } = parseIndex(body, io);
  const part = t => entries.find(e => e.tag === t);
  const indexLen = (entries.length + 1) * 16;
  if (indexLen > OTA_INDEX_MAX) bad.push(`index is ${indexLen} bytes, OTAP only buffers ${OTA_INDEX_MAX}`);
  if (!part("OTAP") || !part("FIRM")) return [...bad, "index has no OTAP or FIRM entry"];
  if (part("FIRM").addr !== OTA_FIRM_ADDR) bad.push(`FIRM at 0x${part("FIRM").addr.toString(16)}, expected 0x4000`);
  const otap = part("OTAP").addr;
  if (otap > body.length) bad.push(`OTAP at 0x${otap.toString(16)} is past the end of the image`);
  for (const e of entries) {
    if (e.tag === "OTAP" || e.tag === "PSMP") continue;
    if (e.addr < OTA_FIRM_ADDR || e.addr + e.len > otap)
      bad.push(`${e.tag} 0x${e.addr.toString(16)}+0x${e.len.toString(16)} is outside 0x4000..0x${otap.toString(16)}`);
    else if (crc16(body.slice(e.addr, e.addr + e.len)) !== e.crc) bad.push(`${e.tag} CRC mismatch`);
  }
  if (body.slice(io + indexLen, OTA_FIRM_ADDR).some(x => x)) bad.push("index page padding is not all zero");
  return bad;
}

// Compare a bud's index (C0 83 read at 0x3000) with the image's entries.
export function liveIndexProblems(raw, entries) {
  if (!raw || raw.length < 16) return ["live index read came back short"];
  const dv = new DataView(raw.buffer, raw.byteOffset);
  const count = dv.getUint32(0, true);
  if (count < 1 || count > OTA_INDEX_MAX / 16 - 1 || raw.length < (count + 1) * 16)
    return [`live index has an implausible count (${count})`];
  const live = {};
  for (let i = 0; i < count; i++) {
    const o = 16 + 16 * i;
    live[String.fromCharCode(...raw.slice(o, o + 4))] = [dv.getUint32(o + 4, true), dv.getUint32(o + 8, true), dv.getUint32(o + 12, true)];
  }
  const bad = [];
  for (const t of ["OTAP", "PSMP"]) {
    const e = entries.find(x => x.tag === t), l = live[t];
    if (!e || !l || l[0] !== e.addr || l[1] !== e.len || l[2] !== e.crc)
      bad.push(`live ${t} entry ${l ? l.map(v => "0x" + v.toString(16)) : "missing"} != image ${e ? [e.addr, e.len, e.crc].map(v => "0x" + v.toString(16)) : "missing"}`);
  }
  if (!live.FIRM || live.FIRM[0] !== OTA_FIRM_ADDR) bad.push("live FIRM is not at 0x4000");
  return bad;
}

// payload=FIRM..OTAP, index=16*(n+1)B at io, declared=io..OTAP (what the
// updater CRC16-verifies after the write).
export function upPayloads(upBytes) {
  const bad = otaImageProblems(upBytes);
  if (bad.length) throw new Error("refusing this image, nothing sent:\n  " + bad.join("\n  "));
  const body = upBytes.slice(UP_BODY);
  const io = indexOffset(body);
  const { entries } = parseIndex(body, io);
  const present = entries.filter(e => e.addr + e.len <= body.length);
  if (!present.length) throw new Error("no index partition is backed by bytes in this file");
  const fwAddr = Math.min(...present.map(e => e.addr));
  const otap = entries.find(e => e.tag.trim() === "OTAP" && e.addr <= body.length);
  const lastEnd = otap ? otap.addr : Math.max(...present.map(e => e.addr + e.len));
  if (lastEnd <= fwAddr) throw new Error("payload region is empty");
  return {
    body, payload: body.slice(fwAddr, lastEnd), fwAddr,
    index: body.slice(io, io + 16 * (entries.length + 1)), io,
    declared: body.slice(io, lastEnd), lastEnd, entries,
  };
}
