// Parity test: proto.js / files.js must match tools/huilian/proto.py byte for byte.
// Regenerate vectors: python3 tools/webui/genvec.py > /tmp/vec.json
// Run: node selftest.mjs [vec.json] [dump.up]
import * as proto from "./proto.js";
import { cfwApply, toneList } from "./files.js";
import { readFileSync } from "fs";

const b = h => Uint8Array.from(h.match(/../g).map(x => parseInt(x, 16)));
const hex = a => [...a].map(x => x.toString(16).padStart(2, "0")).join("");
let fails = 0;
const check = (name, got, want) => {
  const ok = eq(got, want);
  console.log(`${ok ? "ok " : "FAIL"}  ${name}`);
  if (!ok) { console.log(`     got  ${hex(got)}`); console.log(`     want ${hex(want)}`); fails++; }
};
const eq = (a, c) => a.length === c.length && a.every((x, i) => x === c[i]);

const vec = JSON.parse(readFileSync(process.argv[2] || "/tmp/vec.json", "utf8"));
const t16 = new Uint8Array([...Array(256).keys()]);
check("crc16", Uint8Array.of(proto.crc16(t16) >> 8, proto.crc16(t16) & 0xff), b(vec.crc16));
check("crc8", Uint8Array.of(proto.crc8(b("55aa803300"))), b(vec.crc8));
check("scramble", proto.scramble(b("00112233445566778899aabbccddeeff"), 0x756)[0], b(vec.scramble));
check("c0 frame", proto.c0(0x6e, Uint8Array.of(1, 1)), b(vec.c0));
check("ota_enter", proto.withCrc8(proto.otaEnter(0x11)), b(vec.ota_enter));
check("ota_prepare", proto.withCrc8(proto.otaPrepare(0x22)), b(vec.ota_prepare));
check("ota_write", proto.withCrc8(proto.otaWrite(0x4000, b("dead"))), b(vec.ota_write));
check("c002Reply", proto.c002Reply(b(vec.req)), b(vec.c002_reply));

// nondegenerate challenges are well-formed
for (const mk of [proto.challenge1, proto.challenge2]) {
  const ch = mk();
  if (ch.length !== 61) { console.log("FAIL challenge length"); fails++; }
}
// c002Reply with a generated challenge: self-consistency (round trips to a 61B reply)
const req2 = Uint8Array.from([0xC0, 0x02, 0x3D, ...proto.challenge2()]);
const rep2 = proto.c002Reply(req2);
if (rep2.length !== 61) { console.log("FAIL c002Reply len"); fails++; }
else console.log("ok  c002Reply len");

// file-side parity vs the live dump
const upPath = process.argv[3];
if (upPath) {
  const up = new Uint8Array(readFileSync(upPath));
  const { payload, fwAddr, index, declared } = proto.upPayloads(up);
  check("up declared", proto.withCrc8(proto.otaDeclare(declared, 0x33)), b(vec.declared));
  check("up index len", Uint8Array.of(index.length >> 8, index.length & 0xff), b(vec.index_len));
  console.log(`payload ${payload.length}B fw@0x${fwAddr.toString(16)} declared ${declared.length}B`);
  const patch = JSON.parse(readFileSync(new URL("../../patches/2607061716/head-tracking.json", import.meta.url)));
  const lines = [];
  const { out } = cfwApply(up, [patch], {}, lines);
  check("cfwApply", out.slice(0, 64), b(vec.cfw_head));
  const tones = toneList(up);
  check("tone count", Uint8Array.of(tones.length), b(vec.tone_count));
}
console.log(fails ? `\n${fails} FAILURES` : "\nall ok");
process.exit(fails ? 1 : 0);
