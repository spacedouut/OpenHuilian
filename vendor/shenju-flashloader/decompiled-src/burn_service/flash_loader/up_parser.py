# Source Generated with Decompyle++
# File: up_parser.pyc (Python 3.10)

from ctypes import *
import io
import tarfile
from  import env

class section:
    
    def __init__(self, _type = ('',)):
        self.offset = 0
        self.data = None
        self.items = []
        self.type = _type

    
    def add(self, item):
        self.items.append(item)

    
    def merge(self, force = (False,)):
        if self.data is not None and force is False:
            return self.data
        self.data = None(0)
        for item in sorted(self.items):
            if len(item[1]) > 0:
                self.data += bytes(item[0] - len(self.data))
                self.data += item[1]
        return self.data

    
    def unmerge(self):
        self.data = None



def crc16(init, bytes_to_calc):
    
    def crc16_one_byte(lastcrc, one_byte):
        POLY_CRC16 = 4129
        b = one_byte
        for i in range(8):
            if (b << i ^ lastcrc >> 8) & 128 != 0:
                lastcrc <<= 1
                lastcrc = (lastcrc ^ POLY_CRC16) & 65535
                continue
            lastcrc <<= 1
            lastcrc = lastcrc & 65535
        return lastcrc & 65535

    for b in bytes_to_calc:
        init = crc16_one_byte(init, b)
    return init


def make_up_header(all_flash_data):
    c_crc = cdll.LoadLibrary(env.C_CRC_DLL_PATH_NAME)
    up_header = section()
    up_header.add((0, b'CONFIG'))
    up_header.add((6, int.to_bytes(256, 4, 'little')))
    up_header.add((16, int.to_bytes(len(all_flash_data), 4, 'little')))
    up_header.add((20, int.to_bytes(c_crc.CalcCRC(65535, c_char_p(all_flash_data), len(all_flash_data)), 2, 'little')))
    up_header.add((254, b'U\xaa'))
    return up_header.merge()


def get_up_chip_name_lower(up_file_content):
    if is_upex_file(up_file_content):
        return 'sl6806'
    _chip_name_bytes = None(0)
    for ch in up_file_content[22:32]:
        if ch != 0:
            _chip_name_bytes += int.to_bytes(ch, 1, 'little')
    return _chip_name_bytes.decode().lower()


def is_up_file(up_file_content):
    if up_file_content is None:
        return False
    if None(up_file_content) < 20992:
        return False
    if None != up_file_content[0:6]:
        return False
    bootloader_header = None[256:][0:96]
    if b'HLKJ' != bootloader_header[0:4]:
        return False


def is_upex_file(upex_file_content):
    fc = io.BytesIO(upex_file_content)
    
    try:
        with tarfile.open(fc, **('fileobj',)) as tar:
            None(None, None, None)
            return True
            with None:
                if not None:
                    pass
    finally:
        return None
        return False



class psm_dll:
    
    def get_psm_from_flash(self, all_flash_data):
        bootloader_header = all_flash_data[0:96]
        partition_table_addr = int.from_bytes(bootloader_header[32:35], 'little', **('byteorder',))
        partition_table = all_flash_data[partition_table_addr:partition_table_addr + 256]
        partition_num = int.from_bytes(partition_table[0:4], 'little', **('byteorder',))
        if partition_num > 50:
            return (None, None, None)
        for i in None(partition_num):
            tag = partition_table[(i + 1) * 16 + 0:(i + 1) * 16 + 4]
            addr = partition_table[(i + 1) * 16 + 4:(i + 1) * 16 + 8]
            length = partition_table[(i + 1) * 16 + 8:(i + 1) * 16 + 12]
            if tag.decode('utf-8', 'ignore') == 'PSMP':
                psm_addr = int.from_bytes(addr, 'little', **('byteorder',))
                psm_length = int.from_bytes(length, 'little', **('byteorder',))
                psm_buff = all_flash_data[psm_addr:psm_addr + psm_length]
                if len(psm_buff) < psm_length:
                    self.has_psm_data = False
                    psm_buff += bytes([
                        255] * (psm_length - len(psm_buff)))
                else:
                    self.has_psm_data = True
                return (psm_buff, psm_addr, psm_length)
            return (None, None, None)

    
    def get_all_flash_data_from_new_psm(self, all_flash_data, psm_buff):
        (pb, psm_addr, pl) = self.get_psm_from_flash(all_flash_data)
        if len(all_flash_data) < psm_addr:
            fill = psm_addr - len(all_flash_data)
            all_flash_data += bytes([
                255] * fill)
            all_flash_data += psm_buff
            return all_flash_data
        all_flash_data = None[0:psm_addr] + psm_buff
        return all_flash_data

    
    def __init__(self = None, index = None, up_file_data = None, psm_data = (b'', b'')):
        if up_file_data == b'' and psm_data == b'':
            return None
        self.index = None
        self.up_header = None
        self.flash_data = None
        self.psm_length = None
        self.psm_buff = None
        self.psm_addr = None
        self.wrap_buff = None
        self.has_psm_data = False
        if up_file_data != b'':
            self.up_header = up_file_data[0:256]
            self.flash_data = up_file_data[256:]
            (self.psm_buff, self.psm_addr, self.psm_length) = self.get_psm_from_flash(self.flash_data)
        elif psm_data != b'':
            self.psm_buff = psm_data
            self.psm_length = len(psm_data)
            self.has_psm_data = True
        if self.psm_buff is None or self.psm_buff == b'':
            return None
        self.wrap_buff = None(self.psm_length)
        self.library = cdll.LoadLibrary(env.PSM_NVDS_DLL_PATH_NAME)
        ret = self.library.pc_psm_init(self.index, c_char_p(self.psm_buff), self.psm_length, c_char_p(self.wrap_buff), self.psm_length)
        if ret != 0:
            raise MemoryError

    
    def get_psm_buff(self):
        ret = self.library.pc_psm_uninit(self.index, c_char_p(self.psm_buff), self.psm_length, c_char_p(self.wrap_buff), self.psm_length)
        if ret != 0:
            raise MemoryError
        return self.psm_buff

    
    def get_up_file_data(self):
        if self.psm_buff is None or self.psm_buff == b'':
            return b''
        :
            if self.psm_buff is None or self.psm_buff == b'':
                return b''
            
            return self.up_header + self.get_all_flash_data_from_new_psm(self.flash_data, self.get_psm_buff())
        return self.up_header + self.get_all_flash_data_from_new_psm(self.flash_data, self.get_psm_buff())
    # WARNING: Decompyle incomplete

    
    def get_vars(self):
        if self.wrap_buff is None:
            return None
        wrap_data = None.wrap_buff
        item_num = int.from_bytes(wrap_data[0:4], 'little', **('byteorder',))
        offset = 4
        for i in range(item_num):
            value_name_len = 0
            if wrap_data[offset + value_name_len] != 0:
                value_name_len += 1
                if value_name_len >= 256:
                    pass
                elif not wrap_data[offset + value_name_len] != 0:
                    value_name = wrap_data[offset:offset + value_name_len]
                    offset += 256
                    value_len = int.from_bytes(wrap_data[offset:offset + 4], 'little')
                    offset += 4
                    value = wrap_data[offset:offset + value_len]
                    offset += value_len
                    yield (value_name_len, value_name, value_len, value)
                    continue
                    return None

    
    def set_vars(self, total_num, value_name_lens, value_names, value_lens, values):
        self.wrap_buff = int.to_bytes(total_num, 4, 'little')
        for i in range(total_num):
            self.wrap_buff += value_names[i]
            self.wrap_buff += bytes(256 - len(value_names[i]))
            self.wrap_buff += int.to_bytes(value_lens[i], 4, 'little')
            self.wrap_buff += values[i]
        self.wrap_buff += bytes(self.psm_length - len(self.wrap_buff))


