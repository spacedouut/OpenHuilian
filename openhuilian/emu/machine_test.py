#!/usr/bin/env python3
"""Register-level tests of the hardware model (machine.py, chip.py). Offline only.

    OPENHUILIAN_STOCK_UP=... python3 -m unittest openhuilian.emu.machine_test

Needs the stock image for a flash to model; the mask ROM is not needed. Skipped without it.
"""
import os
import struct
import unittest
from pathlib import Path

from unicorn.arm_const import UC_ARM_REG_PC, UC_ARM_REG_R0

from openhuilian.emu import chip
from openhuilian.emu.machine import FLASH, SRAM
from openhuilian.format.upfmt import BODY, crc16

UP = os.environ.get("OPENHUILIAN_STOCK_UP")
BUF = SRAM + 0x80000


@unittest.skipUnless(UP and Path(UP).is_file(), "set OPENHUILIAN_STOCK_UP")
class ChipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.image = Path(UP).read_bytes()[BODY:]

    def setUp(self):
        self.m, self.p = chip.power_on(self.image)
        self.f = self.p["flash"]

    def spi(self, op, addr=0, data=b"", n=None):
        self.m.uc.mem_write(BUF, bytes(data))
        for off, v in ((0x14, (n or len(data) or 1) - 1), (0x18, addr), (0x1C, BUF)):
            self.f.write(off, v, 4)
        self.f.write(0x10, 0x80000000 | op, 4)
        return bytes(self.m.uc.mem_read(BUF, n or len(data) or 1))

    def test_flash_read_matches_xip_window(self):
        self.assertEqual(self.spi(0x03, 0x4000, n=64), bytes(self.m.uc.mem_read(FLASH + 0x4000, 64)))
        self.assertEqual(self.f.read(0x0C, 4) & 2, 2)
        self.f.write(0x0C, 2, 4)
        self.assertEqual(self.f.read(0x0C, 4) & 2, 0)

    def test_flash_crc_unit(self):
        self.f.write(0x64, 0xFFFF, 4)
        self.f.write(0x60, 1, 4)
        self.spi(0x03, 0, n=0x5C)
        self.assertEqual(self.f.read(0x6C, 4), crc16(self.image[:0x5C], 0xFFFF))
        self.assertEqual(self.f.read(0x6C, 4), struct.unpack_from("<I", self.image, 0x5C)[0])

    def test_write_needs_write_enable(self):
        before = bytes(self.m.flash)
        self.spi(0x02, 0xFC000, b"\x00" * 4)
        self.spi(0x20, 0xFC000)
        self.assertEqual(bytes(self.m.flash), before)
        self.assertEqual(len(self.f.errors), 2)

    def test_erase_then_program_clears_bits_only(self):
        self.spi(0x06)
        self.assertEqual(self.spi(0x05, n=1)[0] & 2, 2)
        self.spi(0x20, 0xFC123)
        self.assertEqual(self.m.flash[0xFC000:0xFD000], b"\xff" * 0x1000)
        self.assertEqual(self.spi(0x05, n=1)[0] & 3, 1)      # busy, write-enable dropped
        self.spi(0x06)
        self.spi(0x02, 0xFC010, b"\xf0\x0f")
        self.spi(0x06)
        self.spi(0x02, 0xFC010, b"\x3c\xff")
        self.assertEqual(self.m.flash[0xFC010:0xFC012], b"\x30\x0f")
        self.assertEqual(bytes(self.m.uc.mem_read(FLASH + 0xFC010, 2)), b"\x30\x0f")
        self.assertFalse(self.f.errors)

    def test_page_program_wraps_in_page(self):
        self.spi(0x06)
        self.spi(0x20, 0xFC000)
        self.spi(0x06)
        self.spi(0x02, 0xFC0FE, b"\x01\x02\x03\x04")
        self.assertEqual(self.m.flash[0xFC0FE:0xFC100], b"\x01\x02")
        self.assertEqual(self.m.flash[0xFC000:0xFC002], b"\x03\x04")
        self.assertEqual(self.m.flash[0xFC100:0xFC102], b"\xff\xff")
        self.assertTrue(self.f.errors)

    def test_cpu_cannot_write_xip_flash(self):
        m = self.m
        m.uc.mem_write(BUF, bytes.fromhex("0160fee7"))     # str r1, [r0]; b .
        m.uc.reg_write(UC_ARM_REG_PC, BUF)
        m.uc.reg_write(UC_ARM_REG_R0, FLASH + 0x4000)                  # r0
        self.assertEqual(m.run(100), "fault")
        self.assertIn("XIP flash", m.fault)
        self.assertEqual(bytes(m.flash), self.image.ljust(len(m.flash), b"\xff")[:len(m.flash)])

    def test_wfi_with_no_wake_source_is_idle(self):
        m = self.m
        m.uc.mem_write(BUF, bytes.fromhex("30bffee7"))     # wfi; b .
        m.uc.reg_write(UC_ARM_REG_PC, BUF)
        self.assertEqual(m.run(1000), "idle")

    def test_polling_an_unmodelled_bit_is_reported(self):
        m = self.m
        m.stall_limit = 1000
        m.uc.mem_write(BUF, bytes.fromhex("0168fde7"))     # ldr r1, [r0]; b .-2
        m.uc.reg_write(UC_ARM_REG_PC, BUF)
        m.uc.reg_write(UC_ARM_REG_R0, 0x40050000)
        self.assertEqual(m.run(100_000), "fault")
        self.assertIn("0x40050000", m.fault)

    def test_pll_lock_follows_enable(self):
        c = self.p["clocks"]
        for off in (0x00, 0x08, 0x10):
            self.assertEqual(c.read(off, 4) >> 28 & 1, 0)
            c.write(off, 0xC0010000, 4)
            self.assertEqual(c.read(off, 4), 0xD0010000)

    def test_pmu_register_bus(self):
        pmu = self.p["pmu"]
        pmu.write(0x100, 0x80000000, 4)
        self.assertEqual(pmu.read(0x100, 4), 0)
        pmu.write(0x108, 0x5A, 4)
        pmu.write(0x104, 0x80000060 | 0x47 << 8, 4)
        pmu.write(0x104, 0x80000061 | 0x47 << 8, 4)
        self.assertEqual(pmu.read(0x104, 4) >> 31, 0)
        self.assertEqual(pmu.read(0x10C, 4), 0x5A)
        self.assertEqual(pmu.read(0x110, 4) & 0xF000, 0)
        pmu.write(0x104, 0x80000041, 4)                     # no such device
        self.assertTrue(pmu.read(0x110, 4) & 0xF000)

    def test_pmu_rail_handover(self):
        pmu = self.p["pmu"]
        for _ in range(2):
            pmu.write(0xD0, pmu.read(0xD0, 4) | 8, 4)
            self.assertTrue(pmu.read(0xD0, 4) & 2)
            pmu.write(0xD0, pmu.read(0xD0, 4) | 4, 4)
            self.assertFalse(pmu.read(0xD0, 4) & 2)

    def test_i2c_nacks_absent_device(self):
        i2c = self.p["i2c"]
        i2c.write(0x08, 0xC0, 4)
        i2c.write(0x04, 0x80000001, 4)
        self.assertEqual(i2c.read(0x04, 4), 0)
        self.assertTrue(i2c.read(0x10, 4) & 0x8000)
        i2c.write(0x10, 0x8000, 4)
        self.assertFalse(i2c.read(0x10, 4) & 0x8000)

    def test_timer_counts_microseconds(self):
        t, m = self.p["ustimer"], self.m
        m.cycles = 5 * m.cpu_hz
        self.assertEqual(t.read(0x104, 4), 5_000_000)
        self.assertEqual(t.read(0x108, 4), 0)

    def test_uart_and_boot_stage_capture(self):
        self.p["uart0"].write(0, ord("#"), 4)
        self.assertTrue(self.p["uart0"].read(8, 4) & 0x10)
        self.p["system"].write(0x100, 0xB, 4)
        self.assertEqual((bytes(self.p["uart0"].tx), self.p["system"].stages), (b"#", [0xB]))


if __name__ == "__main__":
    unittest.main()
