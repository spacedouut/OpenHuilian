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

const en = on => ["btnInfo", "btnAuth", "btnReadAll", "btnRead", "btnOta"].forEach(i => { $(i).disabled = !on; });

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

$("btnOta").onclick = async () => {
  try {
    needLink();
    if (!upBytes) throw new Error("pick a .up first");
    const { payload, fwAddr, index, io, declared, lastEnd } = proto.upPayloads(upBytes);
    log(`payload 0x${fwAddr.toString(16)}..0x${lastEnd.toString(16)} (${payload.length}B), index @0x${io.toString(16)} (${index.length}B)`);
    const sides = $("side").value === "both" ? [0x11, 0x22] : [$("side").value === "l" ? 0x11 : 0x22];
    for (let n = 0; n < sides.length; n++) {
      const side = sides[n];
      if (n) {
        log("waiting for the bud to come back ...");
        try { await L.close(); } catch {}
        L = null;
        const port = await link.requestPort();
        L = await link.openLink(port);
      }
      log(`--- side 0x${side.toString(16)} ---`);
      let r;
      let ok = false;
      for (let i = 0; i < 6; i++) {
        r = await L.otaFrame(proto.otaEnter(side));
        log(`enter(80): ${r ? hex(r) : "<no reply>"}`);
        if (r) { ok = true; break; }
      }
      if (!ok) throw new Error("bud never answered 55AA80");
      r = await L.otaFrame(proto.otaPrepare(side));
      if (!r) throw new Error("no reply to prepare (55AA81)");
      log(`prepare(81): ${hex(r)}`);
      r = await L.otaFrame(proto.otaDeclare(declared, side));
      if (!r) throw new Error("no reply to declare (55AA82)");
      log(`declare(82): ${hex(r)}`);
      for (let pos = 0; pos < payload.length; pos += 512) {
        const chunk = payload.slice(pos, pos + 512);
        r = await L.otaFrame(proto.otaWrite(fwAddr + pos, chunk), 3000);
        if (!r) throw new Error(`write at 0x${(fwAddr + pos).toString(16)} got no reply`);
        if ((pos + chunk.length) % 8192 < 512) log(`  0x${(pos + chunk.length).toString(16)}/0x${payload.length.toString(16)}`);
      }
      r = await L.otaFrame(proto.otaWrite(io, index), 3000);
      if (!r) throw new Error("index write got no reply - aborting before finalize");
      log(`index write: ${hex(r)}`);
      r = await L.otaFrame(proto.otaFinalize(side), 3000);
      log(`finalize(84): ${r ? hex(r) : "<link dropped / rebooting>"}`);
    }
    log("done. Buds reboot on their own.");
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
    lab.innerHTML = `<span>${st.name} <small>${st.what || ""} stock ${st.stock}</small></span>`;
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
      lab.innerHTML = `<span>${e.name} <small>${e.size}B</small></span>`;
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
