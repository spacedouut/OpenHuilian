// Web Serial transport, JS port of tools/huilian/link.py.
import * as proto from "./proto.js";

export const BAUD = 115200;

export async function requestPort() {
  const port = await navigator.serial.requestPort();
  return port;
}

export async function openLink(port, baud = BAUD) {
  await port.open({ baudRate: baud });
  return new Link(port);
}

export class Link {
  constructor(port) {
    this.port = port;
    this.buf = new Uint8Array(0);
    this.reader = port.readable.getReader();
    this.pending = null; // the single in-flight reader.read() promise
  }

  // One read at a time: a Promise.race timeout that loses must NOT abandon
  // read(), or the pending read eats the reply nobody handles. Keep the same
  // promise until it settles.
  async _read(ms) {
    if (!this.pending) this.pending = this.reader.read();
    const r = await Promise.race([
      this.pending.then(v => ({ kind: "data", v })),
      new Promise(res => setTimeout(() => res({ kind: "timeout" }), ms)),
    ]);
    if (r.kind === "data") this.pending = null;
    return r.kind === "data" ? r.v : null;
  }

  _feed(value) {
    if (!value || !value.length) return;
    const b = new Uint8Array(this.buf.length + value.length);
    b.set(this.buf); b.set(value, this.buf.length);
    this.buf = b;
  }

  _takeC0() {
    const i = this.buf.indexOf(0xC0);
    if (i < 0 || this.buf.length < i + 3) return null;
    const cmd = this.buf[i + 1];
    if (cmd === 0x83) {
      if (this.buf.length < i + 10) return null;
      const n = new DataView(this.buf.buffer, this.buf.byteOffset).getUint32(i + 6, true);
      if (this.buf.length < i + 10 + n) return null;
      const r = this.buf.slice(i, i + 10 + n);
      this.buf = this.buf.slice(i + 10 + n);
      return r;
    }
    const n = this.buf[i + 2];
    if (this.buf.length < i + 3 + n) return null;
    const r = this.buf.slice(i, i + 3 + n);
    this.buf = this.buf.slice(i + 3 + n);
    return r;
  }

  // A complete 55AA reply. The exact reply layout was never captured, so the
  // frame end is found by crc8: the first j > i+3 where buf[j] equals
  // crc8(55AA..buf[j-1]) closes the frame. Anything that verifies is a real
  // reply; anything that never verifies stays buffered until timeout.
  _take55() {
    const i = this.buf.indexOf(0x55);
    if (i < 0) return null;
    if (this.buf.length === i + 1) {
      // read ended exactly at 0x55: keep it until the next byte arrives
      if (i > 0) this.buf = this.buf.slice(i);
      return null;
    }
    if (this.buf[i + 1] !== 0xAA) {
      this.buf = this.buf.slice(i + 1);
      return null;
    }
    const maxEnd = Math.min(this.buf.length, i + 66);
    for (let j = i + 4; j < maxEnd; j++) {
      if (proto.crc8(this.buf.slice(i, j)) === this.buf[j]) {
        const r = this.buf.slice(i, j + 1);
        this.buf = this.buf.slice(j + 1);
        return r;
      }
    }
    // only one 0x55 seen so far and buffer is large: drop head, keep hunting
    if (this.buf.length - i > 66) this.buf = this.buf.slice(i + 1);
    else if (i > 0) this.buf = this.buf.slice(i);
    return null;
  }

  async _pump(ms) {
    const end = Date.now() + ms;
    while (Date.now() < end) {
      const v = await this._read(Math.min(50, end - Date.now()));
      if (v && v.done) return null;
      if (v && v.value) this._feed(v.value);
      const r = this._takeC0();
      if (r) return r;
      if (this.buf.length > 65536) this.buf = this.buf.slice(-1024);
    }
    return null;
  }

  async _pump55(ms) {
    const end = Date.now() + ms;
    while (Date.now() < end) {
      const v = await this._read(Math.min(50, end - Date.now()));
      if (v && v.done) return null;
      if (v && v.value) this._feed(v.value);
      const r = this._take55();
      if (r) return r;
      if (this.buf.length > 65536) this.buf = this.buf.slice(-1024);
    }
    return null;
  }

  async _send(bytes) {
    const w = this.port.writable.getWriter();
    try { await w.write(bytes); } finally { w.releaseLock(); }
  }

  async c0(cmd, payload = new Uint8Array(0), timeout = 3000) {
    this.buf = new Uint8Array(0);
    await this._send(proto.c0(cmd, payload));
    const end = Date.now() + timeout;
    let r = await this._pump(end - Date.now());
    while (r && r[1] !== cmd && Date.now() < end) r = await this._pump(end - Date.now());
    return r && r[1] === cmd ? r : null;
  }

  async readFlash(addr, n, timeout = 3000) {
    this.buf = new Uint8Array(0);
    await this._send(proto.c0ReadFlash(addr, n));
    const end = Date.now() + timeout;
    const r = await this._pump(end - Date.now());
    if (!r || r.length < 10 || r[1] !== 0x83) return null;
    const dv = new DataView(r.buffer, r.byteOffset);
    const a = dv.getUint32(2, true), ln = dv.getUint32(6, true);
    const data = r.slice(10, 10 + ln);
    if (a !== addr || data.length !== ln || ln === 0) return null;
    return data;
  }

  async readFlashRange(addr, total, chunk = 100, log = () => {}) {
    const out = new Uint8Array(total);
    let pos = 0;
    while (pos < total) {
      const n = Math.min(chunk, total - pos);
      let data = await this.readFlash(addr + pos, n);
      if (!data) {
        log(`  read @0x${(addr + pos).toString(16)} failed, retrying`);
        data = await this.readFlash(addr + pos, n);
      }
      if (!data) return null;
      out.set(data, pos);
      pos += data.length;
      if (pos % 4096 < chunk) log(`  0x${pos.toString(16)}/0x${total.toString(16)}`);
    }
    return out;
  }

  // Send a 55AA request, return the verified reply frame whose cmd echoes the
  // request cmd (replies carry the same opcode). Null on timeout.
  async otaFrame(frame, timeout = 3000) {
    this.buf = new Uint8Array(0);
    await this._send(proto.withCrc8(frame));
    const end = Date.now() + timeout;
    const want = frame[2];
    let r = await this._pump55(end - Date.now());
    while (r && r[2] !== want && Date.now() < end) r = await this._pump55(end - Date.now());
    return r && r[2] === want ? r : null;
  }

  // Same, parsed: OTAP answers `55 AA cmd <answering side> len payload crc8`,
  // payload[0] is the status (0 = ok). Null on timeout.
  async ota(frame, timeout = 3000) {
    const r = await this.otaFrame(frame, timeout);
    if (!r) return null;
    const payload = r.slice(5, r.length - 1);
    return { raw: r, cmd: r[2], side: r[3], payload, status: payload.length ? payload[0] : null,
             ok: payload.length > 0 && payload[0] === 0 };
  }

  async close() {
    try { await this.reader.cancel(); } catch {}
    try { this.reader.releaseLock(); } catch {}
    await this.port.close();
  }
}

export const payload = r =>
  r && r.length >= 3 && r[0] === 0xC0 ? r.slice(3, 3 + r[2]) : null;
