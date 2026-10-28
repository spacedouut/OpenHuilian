// File-side tools, JS ports of tools/cfw.py and tools/tone_tool.py.
import { crc16, UP_BODY, indexOffset, parseIndex } from "./proto.js";

const dv = b => new DataView(b.buffer, b.byteOffset, b.byteLength);
const TYPES = { u8: 1, u16: 2, u32: 4, f32: 4 };
const TONE_DATA_START = 0x400;

function loadUp(upBytes) {
  if (String.fromCharCode(...upBytes.slice(0, 6)) !== "CONFIG")
    throw new Error("not a CONFIG/.up container");
  const flash = Uint8Array.from(upBytes.slice(UP_BODY));
  const len = dv(upBytes).getUint32(0x10, true);
  const crc = dv(upBytes).getUint16(0x14, true);
  if (len !== flash.length || crc16(flash) !== crc)
    throw new Error("CONFIG header length/CRC does not match the body, refusing a damaged dump");
  const { version, entries } = parseIndex(flash);
  return { hdr: Uint8Array.from(upBytes.slice(0, UP_BODY)), flash, version, entries };
}

const table = entries => Object.fromEntries(entries.map(e => [e.tag, e]));

const encode = (typ, value) => {
  if (typ === "bytes") {
    return Uint8Array.from(value.match(/../g).map(h => parseInt(h, 16)));
  }
  const b = new Uint8Array(TYPES[typ]);
  const d = dv(b);
  if (typ === "u8") d.setUint8(0, value);
  else if (typ === "u16") d.setUint16(0, value, true);
  else if (typ === "u32") d.setUint32(0, value >>> 0, true);
  else d.setFloat32(0, value, true);
  return b;
};

const eq = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);
const hex = b => [...b].map(x => x.toString(16).padStart(2, "0")).join("");

// applyPatch(flash, version, entries, patch, overrides) -> [changes, log[]]
export function applyPatch(flash, version, entries, patch, overrides = {}, log = []) {
  const fw = Number(patch.firmware);
  if (fw !== version)
    throw new Error(`${patch.name}: written for firmware ${fw}, this image is ${version}`);
  const p = table(entries)[patch.partition];
  if (!p) throw new Error(`${patch.name}: partition ${patch.partition} not in this image`);
  const inPart = (off, n, where) => {
    if (off < 0 || off + n > p.len)
      throw new Error(`${patch.name}: ${where} at ${patch.partition}+${off.toString(16)} (${n}B) outside partition`);
  };
  let changed = 0;
  for (const op of patch.ops || []) {
    const off = Number(op.offset);
    const old = Uint8Array.from(op.old.match(/../g).map(h => parseInt(h, 16)));
    const nw = Uint8Array.from(op.new.match(/../g).map(h => parseInt(h, 16)));
    if (old.length !== nw.length) throw new Error(`${patch.name}: op at ${op.offset} changes length`);
    inPart(off, old.length, "op");
    const cur = flash.slice(p.addr + off, p.addr + off + old.length);
    if (eq(cur, nw)) { log.push(`  = ${op.what || op.offset} (already applied)`); continue; }
    if (!eq(cur, old))
      throw new Error(`${patch.name}: at ${patch.partition}+${op.offset} expected ${hex(old)} found ${hex(cur)}`);
    flash.set(nw, p.addr + off);
    changed++;
    log.push(`  + ${op.what || op.offset}: ${hex(old)} -> ${hex(nw)}`);
  }
  for (const st of patch.settings || []) {
    const off = Number(st.offset);
    const stock = encode(st.type, st.stock);
    let value = st.name in overrides ? overrides[st.name] : st.default;
    if (st.type !== "bytes") {
      if (value === "" || value === null || value === undefined)
        throw new Error(`${st.name}: empty value`);
      value = st.type === "f32" ? parseFloat(value) : Number(value);
      if (!Number.isFinite(value))
        throw new Error(`${st.name}=${value} is not a number`);
      if (st.type !== "f32" && !Number.isInteger(value))
        throw new Error(`${st.name}=${value} is not an integer`);
      if ("min" in st && value < st.min || "max" in st && value > st.max)
        throw new Error(`${st.name}=${value} outside ${st.min}..${st.max}`);
    }
    const nw = encode(st.type, value);
    if (nw.length !== stock.length)
      throw new Error(`${patch.name}: setting ${st.name} value is ${nw.length}B, stock is ${stock.length}B`);
    inPart(off, stock.length, `setting ${st.name}`);
    const cur = flash.slice(p.addr + off, p.addr + off + stock.length);
    if (!eq(cur, stock) && !eq(cur, nw))
      throw new Error(`${patch.name}: setting ${st.name} expected ${hex(stock)} found ${hex(cur)}`);
    if (!eq(cur, nw)) { flash.set(nw, p.addr + off); changed++; }
    log.push(`  * ${st.name} = ${value} (${st.what || ""})`);
  }
  return changed;
}

export function checkCrcs(flash, entries, strict = true, log = []) {
  let ok = true;
  for (const e of entries) {
    if (e.tag === "PSMP" && e.crc === 0) continue;
    if (crc16(flash.slice(e.addr, e.addr + e.len)) !== e.crc) {
      ok = false;
      log.push(`  ${e.tag}: stored CRC 0x${e.crc.toString(16)} does not match`);
    }
  }
  if (strict && !ok) throw new Error("partition CRCs do not verify, refusing to patch this image");
  return ok;
}

export function fixCrcs(flash, entries) {
  const io = indexOffset(flash);
  const d = dv(flash);
  entries.forEach((e, i) => {
    if (e.tag === "PSMP" && e.crc === 0) return;
    if ((e.tag === "FIRM" || e.tag === "OTAP") && flash[e.addr] === 0x30) {
      const blk = d.getUint32(e.addr + 0x18, true);
      d.setUint16(e.addr + 0x1C, crc16(flash.slice(e.addr + 0x30, e.addr + 0x30 + blk)), true);
    }
    d.setUint16(io + 16 + 16 * i + 12, crc16(flash.slice(e.addr, e.addr + e.len)), true);
  });
}

export function writeUp(hdr, flash, chip) {
  const h = Uint8Array.from(hdr);
  const d = dv(h);
  d.setUint32(0x10, flash.length, true);
  d.setUint16(0x14, crc16(flash), true);
  if (chip) {
    const name = new TextEncoder().encode(chip);
    if (name.length > 0xFE - 0x16) throw new Error("chip name does not fit the CONFIG header");
    h.fill(0, 0x16, 0xFE);
    h.set(name, 0x16);
  }
  const out = new Uint8Array(h.length + flash.length);
  out.set(h); out.set(flash, h.length);
  return out;
}

// cfw.py apply: load .up, check, apply patch objects, fix CRCs, return new .up bytes
export function cfwApply(upBytes, patches, overrides = {}, log = []) {
  const { hdr, flash, version, entries } = loadUp(upBytes);
  log.push(`firmware ${version}`);
  checkCrcs(flash, entries, true, log);
  let total = 0;
  for (const p of patches) total += applyPatch(flash, version, entries, p, overrides, log);
  fixCrcs(flash, entries);
  return { out: writeUp(hdr, flash), changed: total };
}

// --- tone_tool.py ports ------------------------------------------------------

function readDir(tone) {
  const entries = [];
  let pos = 0, dataOff = TONE_DATA_START;
  const d = dv(tone);
  while (pos < TONE_DATA_START - 4) {
    const size = d.getUint32(pos, true);
    if (size === 0 || size === 0xFFFFFFFF) break;
    const end = tone.indexOf(0, pos + 4);
    if (end < 0) break;
    const name = new TextDecoder("latin1").decode(tone.slice(pos + 4, end));
    if (!name) break;
    entries.push({ name, size, off: dataOff });
    dataOff += size;
    pos = end + 1;
  }
  return entries;
}

export function toneList(upBytes) {
  const { flash, entries } = loadUp(upBytes);
  const p = table(entries).TONE;
  if (!p) throw new Error("no TONE partition in this image");
  return readDir(flash.slice(p.addr, p.addr + p.len));
}

export function toneReplace(upBytes, swaps, log = []) {
  const { hdr, flash, version, entries } = loadUp(upBytes);
  const io = indexOffset(flash);
  const idx = entries.findIndex(e => e.tag === "TONE");
  if (idx < 0) throw new Error("no TONE partition in this image");
  const p = entries[idx];
  const tone = flash.slice(p.addr, p.addr + p.len);
  const ents = readDir(tone);
  const names = new Set(ents.map(e => e.name));
  const blobs = ents.map(e => e.name in swaps ? swaps[e.name] : tone.slice(e.off, e.off + e.size));
  for (const n in swaps)
    if (!names.has(n)) throw new Error(`'${n}' not in this TONE (have: ${[...names].join(", ")})`);
  let dir = [];
  ents.forEach((e, i) => {
    const b = blobs[i];
    const nb = new Uint8Array(4);
    dv(nb).setUint32(0, b.length, true);
    dir.push(...nb, ...new TextEncoder().encode(e.name), 0);
    log.push(`  ${e.name}: ${e.size} B -> ${b.length} B`);
  });
  if (dir.length > TONE_DATA_START)
    throw new Error(`directory too big: ${dir.length} > ${TONE_DATA_START}`);
  const body = new Uint8Array(TONE_DATA_START + blobs.reduce((a, b) => a + b.length, 0));
  body.set(dir);
  let o = TONE_DATA_START;
  for (const b of blobs) { body.set(b, o); o += b.length; }
  if (body.length > p.len)
    throw new Error(`TONE would be ${body.length}B but partition only declares ${p.len}B`);
  const newTone = new Uint8Array(p.len);
  newTone.set(body);
  flash.set(newTone, p.addr);
  const d = dv(flash);
  d.setUint16(io + 16 + 16 * idx + 12, crc16(newTone), true);
  log.push(`  TONE crc 0x${p.crc.toString(16)} -> 0x${crc16(newTone).toString(16)} (${body.length}/${p.len}B)`);
  return writeUp(hdr, flash);
}
