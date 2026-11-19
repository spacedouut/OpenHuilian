#!/usr/bin/env python3
"""Postprocess recorded firmware reports and test the stock pose map for rigidity."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

import numpy as np

from headtrack import IMAGE, ROM, Motion, POSE, qconj, qerror, qexp, qlog, qmul


def ideal_pose(e, q):
    for address, value in zip((0x82B89C, 0x82EC68, 0x82EC6C, 0x82EC70), q):
        e.write(address, "<f", value)
    e.call(0xC74C88, 0x8F0100)
    angles = np.array(e.read(0x8F0100, "<3f"))
    angles[1] = int(angles[1])+65
    angles[2] = int(angles[2])
    angles = (angles+180) % 360-180
    pose = angles.astype(int)*[1, 1, -1]
    e.write(POSE, "<3h", *pose)
    e.time += .04
    return e.report()[0]


def rigidity():
    e = Motion()
    base = ideal_pose(e, [1, 0, 0, 0])
    jac = np.zeros((3, 3))
    for axis in range(3):
        v = np.zeros(3)
        v[axis] = np.radians(5)
        p = ideal_pose(e, qexp(v))
        n = ideal_pose(e, qexp(-v))
        jac[:, axis] = (qlog(qmul(p, qconj(base)))-qlog(qmul(n, qconj(base))))/np.radians(10)
    u, s, vt = np.linalg.svd(jac)
    rotation = u@vt
    result = dict(jacobian=jac.tolist(), singular_values=s.tolist(), determinant=float(np.linalg.det(jac)))
    result["rigid_axis_map"] = rotation.tolist()
    result["errors_deg"] = {}
    for axis in range(3):
        for angle in (30, 60, 89, 90, 120, 179, 181, 270):
            v = np.zeros(3)
            v[axis] = np.radians(angle)
            actual = ideal_pose(e, qexp(v))
            predicted = qmul(qexp(rotation@v), base)
            result["errors_deg"][f"{axis}/{angle}"] = float(qerror(actual, predicted))
    return result


def analyze(directory):
    results = {}
    for path in sorted(directory.glob("*-*-240.json")):
        if path.name.startswith("metrics"):
            continue
        records = json.loads(path.read_text())
        ts = np.array([r["t"] for r in records])
        vel = np.array([r["velocity"] for r in records])
        quiet = (ts>1)&(ts<2)
        raw = [bytes.fromhex(r["raw"]) for r in records]
        epochs = np.array([struct.unpack_from("<Q", b, 0x16)[0] for b in raw])
        truth = np.array([r["truth"] for r in records])
        fused = np.array([r["fusion"] for r in records])
        ferr = qerror(truth, fused)
        results[path.stem] = dict(quiet_velocity_rms_counts=float(np.sqrt(np.mean(vel[quiet]**2))),
                                 quiet_velocity_max_counts=int(abs(vel[quiet]).max()),
                                 timestamp_send_minus_field_ns=float(np.median(ts*1e9-epochs)),
                                 fusion_rmse_deg=float(np.sqrt(np.mean(ferr[ts>=2]**2))),
                                 fusion_max_deg=float(ferr[ts>=2].max()),
                                 fusion_final_deg=float(ferr[-1]))
        if "-lab-" in path.name:
            wire = qerror(truth, [r["q"] for r in records])
            results[path.stem].update(wire_rmse_deg=float(np.sqrt(np.mean(wire**2))),
                                      wire_max_deg=float(wire.max()), wire_final_deg=float(wire[-1]))
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory", type=Path)
    p.add_argument("--export", type=Path)
    a = p.parse_args()
    result = dict(rigidity=rigidity(), reports=analyze(a.directory))
    (a.directory/"report-analysis.json").write_text(json.dumps(result, indent=2))
    if a.export:
        if not a.export.parent.is_dir():
            p.error("--export parent must exist")
        data = dict(firmware_sha256=hashlib.sha256(IMAGE.read_bytes()).hexdigest(),
                    rom_sha256=hashlib.sha256(ROM.read_bytes()).hexdigest(),
                    assumptions="240 Hz, side selector 0, mode 0, synthetic BT clocks, actual FIFO conversion",
                    rigidity=result["rigidity"])
        lines = ["{"]+[f'  "{k}": {json.dumps(v)},' for k, v in data.items()]
        lines += ['  "scenarios": {']
        entries = list(result["reports"].items())
        lines += [f'    "{k}": {json.dumps(v)}'+("," if i<len(entries)-1 else "")
                  for i, (k, v) in enumerate(entries)]
        lines += ["  },", '  "frequency_and_ablation": '+json.dumps(
            {k:v for k,v in json.loads((a.directory/"metrics-240.json").read_text()).items()
             if k.startswith("sine_") or k.endswith(("/dt", "/no_bias"))}), "}"]
        a.export.write_text("\n".join(lines)+"\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
