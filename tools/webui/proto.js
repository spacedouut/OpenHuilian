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

// payload=FIRM..OTAP, index=16*(n+1)B at io, declared=io..OTAP (what the
// updater CRC16-verifies after the write).
export function upPayloads(upBytes) {
  const magic = String.fromCharCode(...upBytes.slice(0, 6));
  if (magic !== "CONFIG") throw new Error("not a .up (missing CONFIG header)");
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
