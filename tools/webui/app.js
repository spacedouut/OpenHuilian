import * as proto from "./proto.js";
import * as link from "./link.js";
import { cfwApply, toneList, toneReplace } from "./files.js";

const $ = id => document.getElementById(id);
const log = (...a) => {
  $("log").textContent += a.join(" ") + "\n";
  $("log").scrollTop = $("log").scrollHeight;
};
const err = e => { log(`!! ${e.message || e}`); console.error(e); };
const hex = b => b ? [...b].map(x => x.toString(16).padStart(2, "0")).join("") : "";
const ascii = b => b ? [...b].map(c => c >= 32 && c < 127 ? String.fromCharCode(c) : ".").join("") : "";
const download = (bytes, name) => {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([bytes], { type: "application/octet-stream" }));
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
};

if (!("serial" in navigator)) {
  $("btnConnect").disabled = true;
  log("Web Serial not available - use Chrome or Edge on desktop or Android.");
}

let L = null;
const needLink = () => { if (!L) throw new Error("not connected"); };

// --- SETTINGS: name -> {read, write, desc} (from docs/18 command table) ------
const SETTINGS = {
  anc_mode: { r: 0x59, w: 0x69, desc: "0 off · 1 ANC · 2 transparency · 5 adaptive", num: [0, 1, 2, 5] },
  ear_detect: { r: 0x55, w: 0x65, desc: "0/1" },
  game_mode: { r: 0x5E, w: 0x6E, desc: "0/1" },
  eq_mode: { r: 0x52, w: 0x62, desc: "one byte" },
  air_en: { r: 0x50, w: 0x60, desc: "0/1, AirPods emulation" },
  long_press_left: { r: 0x5A, w: 0x6A, desc: "action 1..3", num: [1, 2, 3] },
  long_press_right: { r: 0x5B, w: 0x6B, desc: "action 1..3", num: [1, 2, 3] },
  double_tap_left: { r: 0x5C, w: 0x6C, desc: "action 2..5", num: [2, 3, 4, 5] },
  double_tap_right: { r: 0x5D, w: 0x6D, desc: "action 2..5", num: [2, 3, 4, 5] },
  bt_name: { r: 0x54, w: 0x64, desc: "max 31 chars", str: true },
};
const READS = {
  model: 0x04, product: 0x03, version: 0x05, battery: 0x09, in_ear: 0x0A,
  side: 0x10, link: 0x12, device_id: 0x07, product_id: 0x14, dom: 0x15,
  serial_l: 0x70, serial_r: 0x71, bt_addr: 0x06,
};

const en = on => ["btnInfo", "btnAuth", "btnReadAll", "btnRead", "btnOta", "btnLeave"].forEach(i => { $(i).disabled = !on; });

$("btnConnect").onclick = async () => {
  try {
    const port = await link.requestPort();
    L = await link.openLink(port);
    $("linkState").textContent = "connected";
    $("linkState").style.color = "var(--acc)";
    en(true);
    log("port open @115200");
  } catch (e) { err(e); }
};

$("btnInfo").onclick = async () => {
  try {
    needLink();
    const box = $("info");
    box.classList.remove("hidden");
    box.innerHTML = "";
    for (const [name, cmd] of Object.entries(READS)) {
      const p = link.payload(await L.c0(cmd));
      const row = document.createElement("b");
      row.textContent = name;
      const val = document.createElement("span");
      val.textContent = name === "battery" && p && p.length >= 3
        ? `L=${p[0]} R=${p[1]} case=${p[2]}`
        : p ? `${hex(p)}  ${ascii(p)}` : "no reply";
      box.append(row, val);
    }
    buildSettings();
  } catch (e) { err(e); }
};

$("btnAuth").onclick = async () => {
  try {
    needLink();
    log("C0 01 challenge ...");
    const r1 = await L.c0(0x01, Uint8Array.from([0x3D, ...proto.challenge1()]));
    if (!r1) { log("no reply to C0 01 - unit not authorized"); return; }
    log(`  reply ${hex(r1)}`);
    const ch2 = proto.challenge2();
    const req = Uint8Array.from([0xC0, 0x02, 0x3D, ...ch2]);
    log("C0 02 verify ...");
    const r2 = await L.c0(0x02, Uint8Array.from([0x3D, ...ch2]));
    if (!r2) { log("no reply to C0 02"); return; }
    const p = link.payload(r2);
    const ok = p && hex(p) === hex(proto.c002Reply(req));
    log(`  reply ${hex(r2)}`);
    log(ok ? "authorized" : "answered, but response did not verify");
  } catch (e) { err(e); }
};

function buildSettings() {
  const box = $("setRows");
  box.innerHTML = "";
  box.classList.remove("hidden");
  for (const [name, s] of Object.entries(SETTINGS)) {
    const lab = document.createElement("label");
    lab.className = "s";
    const left = document.createElement("span");
    left.innerHTML = `${name} <small>${s.desc}</small>`;
    const right = document.createElement("span");
    let ctl;
    if (s.num) {
      ctl = document.createElement("select");
      for (const v of s.num) ctl.append(new Option(v, v));
    } else if (s.str) {
      ctl = document.createElement("input");
      ctl.type = "text"; ctl.maxLength = 31; ctl.size = 16;
    } else {
      ctl = document.createElement("input");
      ctl.type = "number"; ctl.min = 0; ctl.max = 255; ctl.size = 4;
      ctl.style.width = "5em";
    }
    ctl.dataset.name = name;
    const get = document.createElement("button");
    get.className = "ghost"; get.textContent = "get";
    get.onclick = async () => {
      try {
        const p = link.payload(await L.c0(s.r));
        if (s.str) ctl.value = ascii(p);
        else if (p && p.length) ctl.value = p[0];
      } catch (e) { err(e); }
    };
    const set = document.createElement("button");
    set.className = "ghost"; set.textContent = "set";
    set.onclick = async () => {
      try {
        const v = s.str ? new TextEncoder().encode(ctl.value) : Uint8Array.of(Number(ctl.value) & 0xff);
        const r = link.payload(await L.c0(s.w, Uint8Array.from([v.length, ...v])));
        log(`${name} <- ${hex(r)}`);
      } catch (e) { err(e); }
    };
    right.append(ctl, get, set);
    lab.append(left, right);
    box.append(lab);
  }
}

$("btnReadAll").onclick = async () => {
  for (const [name, s] of Object.entries(SETTINGS)) {
    try {
      const p = link.payload(await L.c0(s.r));
      const ctl = document.querySelector(`#setRows [data-name="${name}"]`);
      if (!ctl) continue;
      if (s.str) ctl.value = ascii(p);
      else if (p && p.length) ctl.value = p[0];
    } catch (e) { err(e); }
  }
};

$("btnRead").onclick = async () => {
  try {
    needLink();
    const addr = Number($("rdAddr").value), total = Number($("rdLen").value);
    log(`dumping 0x${addr.toString(16)} + 0x${total.toString(16)} ...`);
    const data = await L.readFlashRange(addr, total, 100, log);
    if (!data) { log("dump failed partway"); return; }
    download(data, `dump_${addr.toString(16)}_${total.toString(16)}.bin`);
    log(`saved ${data.length} bytes`);
  } catch (e) { err(e); }
};

// --- OTA ---------------------------------------------------------------------
let upBytes = null;
$("btnPickUp").onclick = () => $("upFile").click();
$("upFile").onchange = e => {
  const f = e.target.files[0];
  if (!f) return;
  f.arrayBuffer().then(b => {
    upBytes = new Uint8Array(b);
    $("upName").textContent = `${f.name} (${upBytes.length}B)`;
    $("otaWarn").classList.remove("hidden");
  });
};

const sleep = ms => new Promise(r => setTimeout(r, ms));

// FIRM answers C0 0A (in-ear); the updater (OTAP) does not.
async function budState() {
  const side = link.payload(await L.c0(0x10, new Uint8Array(0), 2000));
  const lk = link.payload(await L.c0(0x12, new Uint8Array(0), 2000));
  const firm = (await L.c0(0x0A, new Uint8Array(0), 2000)) !== null;
  return { side: side && side.length ? side[0] : null, link: lk && lk.length ? lk[0] : null, firm };
}

async function repick(why) {
  log(why + " pick the port again when it is back.");
  try { await L.close(); } catch {}
  L = null;
  const port = await link.requestPort();
  for (let i = 0; i < 30; i++) {
    try { L = await link.openLink(port); return; } catch (e) { await sleep(2000); }
  }
  throw new Error("link did not come back");
}

// 80..84 + 04 against whichever bud holds the link (OTAP ignores the side
// byte in requests and answers with its own). Returns the answering side.
async function otaOneBud(payload, fwAddr, index, io, declared) {
  let r = null;
  for (let i = 0; i < 6 && !r; i++) {
    r = await L.ota(proto.otaEnter(0x33));
    log(`enter(80): ${r ? hex(r.raw) : "<no reply>"}`);
    if (!r) await sleep(500);
  }
  if (!r) throw new Error("no answer to 55AA80");
  if (!r.ok) throw new Error(`enter refused, status ${r.status} (3 = battery too low)`);
  const side = r.side;
  r = null;
  for (let i = 0; i < 3 && !r; i++) {
    r = await L.ota(proto.otaPrepare(0x33), 30000);
    log(`prepare(81): ${r ? hex(r.raw) : "<no reply>"}`);
  }
  if (!r) throw new Error("no reply to prepare (55AA81)");
  if (!r.ok) throw new Error(`prepare refused, status ${r.status}`);
  r = await L.ota(proto.otaDeclare(declared, 0x33));
  if (!r || !r.ok) throw new Error(`declare (55AA82) failed: ${r ? hex(r.raw) : "<no reply>"}`);
  log(`declare(82): ${hex(r.raw)}`);
  const t0 = Date.now();
  for (let pos = 0; pos < payload.length; pos += 512) {
    const chunk = payload.slice(pos, pos + 512);
    let okw = false;
    for (let attempt = 0; attempt < 4 && !okw; attempt++) {
      r = await L.ota(proto.otaWrite(fwAddr + pos, chunk), 3000);
      okw = !!(r && r.ok);
      if (!okw) log(`  write @0x${(fwAddr + pos).toString(16)}: ${r ? hex(r.raw) : "no reply"}, retry ${attempt + 1}`);
    }
    if (!okw) throw new Error(`write at 0x${(fwAddr + pos).toString(16)} failed`);
    if ((pos + chunk.length) % 16384 < 512) log(`  0x${(pos + chunk.length).toString(16)}/0x${payload.length.toString(16)}  (${Math.round((Date.now() - t0) / 1000)}s)`);
  }
  r = await L.ota(proto.otaWrite(io, index), 3000);
  if (!r || !r.ok) throw new Error("index write failed - stopping before finalize");
  log(`index write: ${hex(r.raw)}`);
  r = await L.ota(proto.otaFinalize(0x33), 10000);
  log(`finalize(84): ${r ? hex(r.raw) : "<no reply>"}`);
  if (!r) throw new Error("no reply to finalize; NOT sending 04. Flash again.");
  if (!r.ok) throw new Error(`finalize status ${r.status}: CRC mismatch, old index restored. NOT sending 04 (that would boot a half-written FIRM). Flash again.`);
  r = await L.ota(proto.otaLeave(0x33), 5000);
  log(`leave(04): ${r ? hex(r.raw) : "<link dropped>"}`);
  return side;
}

// The 55AA flow the way real buds accept it: a 55AA80 to FIRM makes BOTH buds
// reboot into the updater (the master relays it to the peer). Flash whichever
// bud answers, send 04 (clear the boot-to-OTAP flag + reboot), reconnect, and
// if the other bud is still in the updater it is the one answering now. Without
// the 04 both buds stay in OTAP and look like a generic Bluetooth device.
$("btnOta").onclick = async () => {
  try {
    needLink();
    if (!upBytes) throw new Error("pick a .up first");
    const { payload, fwAddr, index, io, declared, lastEnd } = proto.upPayloads(upBytes);
    log(`payload 0x${fwAddr.toString(16)}..0x${lastEnd.toString(16)} (${payload.length}B), index @0x${io.toString(16)} (${index.length}B)`);
    const one = $("side").value === "one";
    const done = [];
    for (let pass = 0; pass < 2; pass++) {
      if (pass) {
        await repick("waiting for the link to come back;");
        const st = await budState();
        if (st.firm) {
          log(`bud 0x${(st.side || 0).toString(16)} answered from FIRM (link ${st.link}); sending 80 again so the remaining bud enters the updater`);
        }
      }
      const side = await otaOneBud(payload, fwAddr, index, io, declared);
      done.push(side);
      log(`--- flashed side 0x${side.toString(16)} ---`);
      if (one || (done.length === 2 && done[0] !== done[1])) break;
    }
    await repick("waiting for the buds to reboot;");
    const st = await budState();
    log(`answering side 0x${(st.side || 0).toString(16)} link ${st.link} mode ${st.firm ? "FIRM" : "OTAP"}; flashed: ${done.map(s => "0x" + s.toString(16)).join(", ")}`);
    if (!st.firm) log("a bud is still in the updater: use Leave updater");
    else if (st.link !== 0) log("peer not linked yet (link != 0); give them a moment or case-cycle both buds");
    else log("done: both buds in FIRM and linked");
  } catch (e) { err(e); }
};

// Get buds out of the updater. OTAP's 04 handler clears the boot flag and
// reboots when the bud has no linked peer; a linked master relays the request
// to its peer and follows 2 s later. Sending 04 to an OTAP bud whose peer is
// already back in FIRM drags that peer back into the updater, so only send 04
// when the answering bud is in OTAP, then re-check.
$("btnLeave").onclick = async () => {
  try {
    needLink();
    for (let rnd = 0; rnd < 4; rnd++) {
      if (rnd) { await sleep(5000); await repick("bud rebooting;"); }
      const st = await budState();
      log(`round ${rnd}: side 0x${(st.side || 0).toString(16)} link ${st.link} mode ${st.firm ? "FIRM" : "OTAP"}`);
      if (st.firm) {
        log(st.link === 0 ? "both buds in FIRM and linked"
          : "this bud is in FIRM but has no peer. If the other bud is still in the updater: put THIS bud in the case with the lid closed, keep the other out, and run Leave updater again.");
        return;
      }
      const r = await L.ota(proto.otaLeave(0x33), 5000);
      log(`  04: ${r ? hex(r.raw) : "<link dropped>"}`);
    }
    err(new Error("still in the updater after 4 rounds; case-cycle both buds and retry"));
  } catch (e) { err(e); }
};

// --- patch -------------------------------------------------------------------
let fwBytes = null, patchObjs = [];

$("btnPickFw").onclick = () => $("fwFile").click();
$("fwFile").onchange = e => {
  const f = e.target.files[0];
  if (!f) return;
  f.arrayBuffer().then(b => { fwBytes = new Uint8Array(b); $("fwName").textContent = f.name; refreshKnobs(); });
};
$("btnPickPatches").onclick = () => $("patchFiles").click();
$("patchFiles").onchange = e => {
  patchObjs = [];
  const files = [...e.target.files];
  Promise.all(files.map(f => f.text().then(t => JSON.parse(t)))).then(objs => {
    patchObjs = objs;
    $("patchNames").textContent = files.map(f => f.name).join(", ");
    refreshKnobs();
  });
};

function refreshKnobs() {
  const box = $("knobs");
  box.innerHTML = "";
  const settings = patchObjs.flatMap(p => p.settings || []);
  if (!settings.length) { box.classList.add("hidden"); $("btnPatch").disabled = !(fwBytes && patchObjs.length); return; }
  box.classList.remove("hidden");
  for (const st of settings) {
    const lab = document.createElement("label");
    lab.className = "s";
    const sp = document.createElement("span");
    const sm = document.createElement("small");
    sm.textContent = `${st.what || ""} stock ${st.stock}`;
    sp.append(st.name + " ", sm);
    lab.append(sp);
    const inp = document.createElement("input");
    inp.type = "number"; inp.value = st.default;
    if ("min" in st) inp.min = st.min;
    if ("max" in st) inp.max = st.max;
    if (st.type === "f32") inp.step = "any";
    inp.dataset.name = st.name;
    lab.append(inp);
    box.append(lab);
  }
  $("btnPatch").disabled = !fwBytes;
}

$("btnPatch").onclick = () => {
  try {
    const overrides = {};
    document.querySelectorAll("#knobs input").forEach(i => { overrides[i.dataset.name] = i.value; });
    const lines = [];
    const { out, changed } = cfwApply(fwBytes, patchObjs, overrides, lines);
    lines.forEach(l => log(l));
    if (!changed) log("nothing changed");
    download(out, "patched.up");
    log(`wrote patched.up (${out.length}B, ${changed} changes)`);
  } catch (e) { err(e); }
};

// --- tones -------------------------------------------------------------------
$("btnToneList").onclick = () => {
  try {
    if (!fwBytes) throw new Error("pick a firmware .up in the patch section first");
    const rows = $("toneRows");
    rows.innerHTML = "";
    rows.classList.remove("hidden");
    for (const e of toneList(fwBytes)) {
      const lab = document.createElement("label");
      lab.className = "s";
      const sp = document.createElement("span");
      const sm = document.createElement("small");
      sm.textContent = `${e.size}B`;
      sp.append(e.name + " ", sm);
      lab.append(sp);
      const inp = document.createElement("input");
      inp.type = "file";
      inp.dataset.name = e.name;
      inp.onchange = () => { $("btnToneApply").disabled = false; };
      lab.append(inp);
      rows.append(lab);
    }
  } catch (e) { err(e); }
};

$("btnToneApply").onclick = async () => {
  try {
    const swaps = {};
    for (const inp of document.querySelectorAll("#toneRows input[type=file]")) {
      if (inp.files[0])
        swaps[inp.dataset.name] = new Uint8Array(await inp.files[0].arrayBuffer());
    }
    if (!Object.keys(swaps).length) throw new Error("pick at least one replacement file");
    const lines = [];
    const out = toneReplace(fwBytes, swaps, lines);
    lines.forEach(l => log(l));
    download(out, "toned.up");
    log(`wrote toned.up (${out.length}B)`);
  } catch (e) { err(e); }
};
