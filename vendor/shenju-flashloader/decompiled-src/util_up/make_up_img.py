# Source Generated with Decompyle++
# File: make_up_img.pyc (Python 3.10)

from PIL import Image
import numpy as np
import io
import re
import struct

class img_converter:
    supported_colors = [
        '565',
        '565a',
        '2bit',
        '4bit']
    
    def __init__(self, pic_name, pic_content, suffix, little_end = (None, False)):
        LV_IMG_CF_TRUE_COLOR = 4
        LV_IMG_CF_TRUE_COLOR_ALPHA = 5
        LV_IMG_CF_INDEXED_2BIT = 8
        LV_IMG_CF_INDEXED_4BIT = 9
        FOR_DICT = {
            '_565': {
                'method': self._img2rgb565,
                'para': False,
                'cf': LV_IMG_CF_TRUE_COLOR },
            '_565a': {
                'method': self._img2rgb565,
                'para': True,
                'cf': LV_IMG_CF_TRUE_COLOR_ALPHA },
            '_2bit': {
                'method': self._img2bit,
                'para': 2,
                'cf': LV_IMG_CF_INDEXED_2BIT },
            '_4bit': {
                'method': self._img2bit,
                'para': 4,
                'cf': LV_IMG_CF_INDEXED_4BIT } }
        self.little_end = little_end
        self.pic_name = pic_name
        self.pic_content = pic_content
        self.suffix = suffix
        if suffix is None:
            for co in img_converter.supported_colors:
                if co in re.split('[._]', pic_name):
                    self.suffix = '_' + co
        self.method = FOR_DICT[self.suffix]['method']
        self.para = FOR_DICT[self.suffix]['para']
        self.width = 0
        self.height = 0
        self.cf = FOR_DICT[self.suffix]['cf']
        self._bin = bytes(0)
        self._bin_len = 0

    
    def _img2rgb565(self, Alpha = (False,)):
        _bin = bytes(0)
    # WARNING: Decompyle incomplete

    
    def _img2bit(self, bit = (2,)):
        color = bit * bit
        min_width = 4 if bit == 2 else 2
    # WARNING: Decompyle incomplete

    
    def _generate_bin_declare(self, address):
        cf = self.cf & 31
        w = self.width << 10 & 2096128
        h = self.height << 21 & 0xFFE00000
        f1 = (cf | w | h) & 0xFFFFFFFF
        f2 = self._bin_len & 0xFFFFFFFF
        f3 = address & 0xFFFFFFFF
        return struct.pack('III', f1, f2, f3)

    
    def _align4Byte2bin(self, _bin):
        if len(_bin) % 4 != 0:
            return _bin + bytes(4 - len(_bin) % 4)

    
    def make_bin(self):
        if len(self._bin) == 0:
            self._bin = self.method(self.para)
            self._bin_len = len(self._bin)
        return self._align4Byte2bin(self._bin)

    
    def make_head(self, address = (0,)):
        self.make_bin()
        return self._generate_bin_declare(address)


