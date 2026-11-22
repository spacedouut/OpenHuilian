import os
import struct
import tempfile
import unittest
from pathlib import Path

from openhuilian.device.cli import _up_payloads
from openhuilian.format.upfmt import (BODY, FLASH_HEADER_CRC, crc16, flash_header_problems,
                                      ota_image_problems)

STOCK = os.environ.get("OPENHUILIAN_STOCK_UP")


def header(fill=0x11):
    head = bytearray(b"HLKJ" + bytes([fill]) * (FLASH_HEADER_CRC - 4) + bytes(4))
    struct.pack_into("<I", head, FLASH_HEADER_CRC, crc16(bytes(head[:FLASH_HEADER_CRC])))
    return head


def rewrap(up):
    """Make the CONFIG wrapper match the body again, so only the flash header is wrong."""
    struct.pack_into("<IH", up, 0x10, len(up) - BODY, crc16(bytes(up[BODY:])))
    return bytes(up)


def synthetic_up():
    """Smallest .up the OTA checks accept: header, index at 0x3000, FIRM at 0x4000, OTAP at 0x10000."""
    body = bytearray(0x10000)
    body[:len(header())] = header(0)
    struct.pack_into("<I", body, 0x20, 0x3000)
    struct.pack_into("<I", body, FLASH_HEADER_CRC, crc16(bytes(body[:FLASH_HEADER_CRC])))
    body[0x4000:0x4100] = bytes(range(256))
    struct.pack_into("<II", body, 0x3000, 2, 1)
    struct.pack_into("<4sIII", body, 0x3010, b"FIRM", 0x4000, 0x100, crc16(bytes(body[0x4000:0x4100])))
    struct.pack_into("<4sIII", body, 0x3020, b"OTAP", 0x10000, 0x100, 0)
    up = bytearray(BODY) + body
    up[:6] = b"CONFIG"
    return bytearray(rewrap(up))


def send(image):
    with tempfile.TemporaryDirectory() as scratch:
        path = Path(scratch) / "image.up"
        path.write_bytes(image)
        return _up_payloads(path)


class SyntheticImageTests(unittest.TestCase):
    def test_good_image_is_sent(self):
        self.assertEqual(ota_image_problems(synthetic_up()), [])
        self.assertEqual(send(synthetic_up())[1], 0x4000)

    def test_corrupted_header_is_refused(self):
        for offset in (0x10, 0x1D, FLASH_HEADER_CRC):
            with self.subTest(offset=hex(offset)):
                bad = synthetic_up()
                bad[BODY + offset] ^= 1
                bad = rewrap(bad)
                self.assertEqual(len(ota_image_problems(bad)), 1)
                with self.assertRaisesRegex(SystemExit, "nothing sent"):
                    send(bad)


class FlashHeaderTests(unittest.TestCase):
    def test_good_header(self):
        self.assertEqual(flash_header_problems(header()), [])

    def test_any_covered_byte_changes_the_verdict(self):
        for offset in (0x04, 0x10, 0x1D, 0x20, 0x5B):
            with self.subTest(offset=hex(offset)):
                bad = header()
                bad[offset] ^= 1
                self.assertRegex(flash_header_problems(bad)[0], "flash header CRC at 0x5c")

    def test_wrong_stored_crc(self):
        bad = header()
        bad[FLASH_HEADER_CRC] ^= 1
        self.assertRegex(flash_header_problems(bad)[0], "flash header CRC at 0x5c")

    def test_rom_compares_the_whole_word(self):
        bad = header()
        bad[FLASH_HEADER_CRC + 2] = 1
        self.assertRegex(flash_header_problems(bad)[0], "flash header CRC at 0x5c")

    def test_magic(self):
        bad = header()
        bad[0] ^= 1
        self.assertRegex(flash_header_problems(bad)[0], "HLKJ magic")

    def test_short(self):
        self.assertRegex(flash_header_problems(header()[:0x5F])[0], "too short")
        self.assertRegex(ota_image_problems(b"CONFIG" + bytes(0x100))[-1], "too short")


@unittest.skipUnless(STOCK, "set OPENHUILIAN_STOCK_UP to a stock .up")
class StockImageTests(unittest.TestCase):
    def setUp(self):
        self.up = Path(STOCK).read_bytes()

    def test_stock_passes(self):
        self.assertEqual(flash_header_problems(self.up[BODY:]), [])
        self.assertEqual(ota_image_problems(self.up), [])
        self.assertEqual(send(self.up)[1], 0x4000)

    def test_corrupted_header_is_refused(self):
        for offset in (0x10, 0x1D, FLASH_HEADER_CRC):
            with self.subTest(offset=hex(offset)):
                bad = bytearray(self.up)
                bad[BODY + offset] ^= 1
                bad = rewrap(bad)
                problems = ota_image_problems(bad)
                self.assertEqual(len(problems), 1)
                self.assertIn("flash header CRC at 0x5c", problems[0])
                with self.assertRaisesRegex(SystemExit, "nothing sent"):
                    send(bad)


if __name__ == "__main__":
    unittest.main()
