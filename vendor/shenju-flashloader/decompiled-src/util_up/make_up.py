# Source Generated with Decompyle++
# File: make_up.pyc (Python 3.10)

import struct
from make_up_img import img_converter
from make_up_jpg import jpg_proc
from make_uti import *

class pics_partition:
    
    def __init__(self, bin, addr, chip):
        self.bin = bin
        self.addr = addr
        self.chip = chip

    
    def _parse_bin_declare(self, bin_data):
        if len(bin_data) != 12:
            raise ValueError('Input data should be 12 bytes')
        (f1, f2, f3) = struct.unpack('III', bin_data)
        cf = f1 & 31
        w = (f1 & 2096128) >> 10
        h = (f1 & 0xFFE00000) >> 21
        data_size = f2
        address = f3
        return 'w:%d h:%d size:%d' % (w, h, data_size)

    
    def get_count(self):
        return int.from_bytes(self.bin[0:4], 'little')

    
    def get_desc(self, index):
        pic_desc_t = self.bin[4 + index * 12:4 + index * 12 + 12]
        return self._parse_bin_declare(pic_desc_t)

    
    def make_bin(self, pic_files, sig):
        addr = self.addr + 12582912
        total_part = bytes(0)
        hed_part = len(pic_files).to_bytes(4, 'little', **('byteorder',))
        addr += 4
        hed_addr = addr
        addr += 12 * len(pic_files)
        img_part = bytes(0)
    # WARNING: Decompyle incomplete



class welc_partition:
    
    def __init__(self, _bin):
        self._bin = _bin
        head_offset = 0
        content_offset = 1024
        self.num = 0
        self.infos = []
        (content_size, file_path, head_size) = self._get_header_one_sec(self._bin[head_offset:])
        if content_size == 0:
            return None
        content = None._bin[content_offset:content_offset + content_size]
        content_offset += content_size
        head_offset += head_size
        self.num += 1
        self.infos.append((content_size, file_path, content))
        print(content_size, file_path, head_size)
        continue

    
    def _get_header_one_sec(self, data):
