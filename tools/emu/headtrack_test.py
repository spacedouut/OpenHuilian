#!/usr/bin/env python3
"""Offline regression tests for real firmware, ROM, and compiled fusion hooks.

Optional --image checks a fully rebuilt v2 .up rather than in-memory patch ops.
"""
import argparse
import json
import unittest
from pathlib import Path

import numpy as np
from unicorn import UC_HOOK_CODE

from headtrack import INPUT, Motion, gravity, qerror, scenarios

IMAGE = None


class HeadTrackingTests(unittest.TestCase):
    def test_old_patch_changes_no_internal_orientation(self):
        stock, old = Motion(), Motion("old")
        for t, _, g, a in scenarios("combined"):
            for e in (stock, old):
                e.time = t
                e.step(g, a, through_fifo=True)
            np.testing.assert_array_equal(stock.fusion_q(), old.fusion_q())

    def test_compiled_matches_python_through_actual_fifo(self):
        c, py = Motion("v2", image=IMAGE), Motion("python")
        worst = 0
        for t, _, g, a in scenarios("gimbal"):
            for e in (c, py):
                e.time = t
                e.step(g, a, through_fifo=True)
            worst = max(worst, float(qerror(c.fusion_q(), py.fusion_q())))
        self.assertLess(worst, .002)

    def test_slow_yaw_not_absorbed(self):
        e = Motion("v2", image=IMAGE)
        for t, truth, g, a in scenarios("slow_yaw"):
            e.time = t
            e.step(g, a, through_fifo=True)
        self.assertLess(float(qerror(e.fusion_q(), truth)), .2)

    def test_inverted_gravity_no_nan(self):
        stock, fixed = Motion(), Motion("v2", image=IMAGE)
        for _ in range(10):
            stock.step([0, 0, 0], [0, 0, 1])
            fixed.step([0, 0, 0], [0, 0, 1])
        self.assertTrue(np.isnan(stock.fusion_q()).all())
        self.assertTrue(np.isfinite(fixed.fusion_q()).all())
        np.testing.assert_allclose(gravity(fixed.fusion_q()), [0, 0, 1], atol=1e-6)

    def test_stationary_report_dither_is_real_firmware(self):
        stock, lab = Motion(), Motion("lab")
        velocities = [[], []]
        for i in range(60):
            for k, e in enumerate((stock, lab)):
                e.time = (i+1)*.04
                e.step([0, 0, 0], [0, 0, -1])
                velocities[k].append(e.report()[1])
        self.assertGreater(np.max(np.abs(velocities[0][25:])), 0)
        np.testing.assert_array_equal(velocities[1][25:], np.zeros((35, 3)))

    def test_negative_and_positive_wrap(self):
        for scenario in ("wrap", "wrap_negative"):
            e = Motion("lab")
            maximum = 0
            for t, truth, g, a in scenarios(scenario):
                e.time = t
                e.step(g, a, through_fifo=True)
                maximum = max(maximum, float(qerror(e.fusion_q(), truth)))
            self.assertLess(maximum, .11)

    def test_instruction_budget_not_cycle_claim(self):
        counts = {}
        for variant in ("stock", "v2"):
            e = Motion(variant, image=IMAGE if variant == "v2" else None)
            for _ in range(10):
                e.step([0, 0, 0], [0, 0, -1])
            count = [0]

            def tick(*_):
                count[0] += 1
            hook = e.uc.hook_add(UC_HOOK_CODE, tick)
            for _ in range(10):
                e.step([10, 20, 30], [.1, .2, -.97])
            e.uc.hook_del(hook)
            counts[variant] = count[0]/10
        print("Full per-entry retired instruction counts (not CPU cycles):", counts)
        self.assertLess(counts["v2"], counts["stock"]*1.5)


def main():
    global IMAGE
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--image", type=Path)
    a, rest = p.parse_known_args()
    IMAGE = a.image
    unittest.main(argv=[__file__, *rest])


if __name__ == "__main__":
    main()
