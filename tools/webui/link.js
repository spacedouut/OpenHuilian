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
  }

  async _pump(ms) {
    const end = Date.now() + ms;
    while (Date.now() < end) {
      const { value, done } = await Promise.race([
        this.reader.read(),
        new Promise(r => setTimeout(() => r(null), Math.min(50, end - Date.now()))),
      ]);
      if (done) break;
      if (value && value.length) {
        const b = new Uint8Array(this.buf.length + value.length);
        b.set(this.buf); b.set(value, this.buf.length);
        this.buf = b;
      }
      const i = this.buf.indexOf(0xC0);
      if (i >= 0 && this.buf.length >= i + 3) {
        const cmd = this.buf[i + 1];
        if (cmd === 0x83) {
          if (this.buf.length >= i + 10) {
            const n = new DataView(this.buf.buffer, this.buf.byteOffset).getUint32(i + 6, true);
            if (this.buf.length >= i + 10 + n) {
              const r = this.buf.slice(i, i + 10 + n);
              this.buf = this.buf.slice(i + 10 + n);
              return r;
            }
          }
        } else {
          const n = this.buf[i + 2];
          if (this.buf.length >= i + 3 + n) {
            const r = this.buf.slice(i, i + 3 + n);
            this.buf = this.buf.slice(i + 3 + n);
            return r;
          }
        }
      }
      if (this.buf.length > 65536) this.buf = this.buf.slice(-1024);
    }
    return null;
  }

  async _pump55(ms) {
    const end = Date.now() + ms;
    while (Date.now() < end) {
      const { value, done } = await Promise.race([
        this.reader.read(),
        new Promise(r => setTimeout(() => r(null), Math.min(50, end - Date.now()))),
      ]);
      if (done) break;
      if (value && value.length) {
        const b = new Uint8Array(this.buf.length + value.length);
        b.set(this.buf); b.set(value, this.buf.length);
        this.buf = b;
      }
      const i = this.buf.indexOf(0x55);
      if (i >= 0 && this.buf.length >= i + 4) {
        const r = this.buf.slice(i);
        this.buf = this.buf.slice(0, i);
        return r;
      }
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
    let r;
    do { r = await this._pump(end - Date.now()); } while (!r && Date.now() < end);
    while (r && r[1] !== cmd && Date.now() < end) r = await this._pump(end - Date.now());
    return r && r[1] === cmd ? r : null;
  }

  async readFlash(addr, n, timeout = 3000) {
    const f = proto.c0ReadFlash(addr, n);
    this.buf = new Uint8Array(0);
    await this._send(f);
    const end = Date.now() + timeout;
    let r;
    do { r = await this._pump(end - Date.now()); } while (!r && Date.now() < end);
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

  async otaFrame(frame, timeout = 3000) {
    this.buf = new Uint8Array(0);
    await this._send(proto.withCrc8(frame));
    return this._pump55(timeout);
  }

  async close() {
    try { this.reader.cancel(); } catch {}
    try { this.reader.releaseLock(); } catch {}
    await this.port.close();
  }
}

export const payload = r =>
  r && r.length >= 3 && r[0] === 0xC0 ? r.slice(3, 3 + r[2]) : null;
