# Source Generated with Decompyle++
# File: flash_usb_6801.pyc (Python 3.10)

import struct
from ctypes import *
import time
from  import env
from  import util_func
from mass_storage_dll import dll_read, dll_write, dll_msg, dll_calc_crc16
from flash_base import flash
from  import up_parser
_flash_index = 0

def _usb_serial_to_chip_name(serial_no):
    if serial_no == b'20201111000001':
        return 'sl6801'
    if None == b'20220320000001':
        return 'sl6806'


def set_init(clkDiv, lineMode, chipSelIndirect, chipSelDirect, chipTypeId = (9, 0, 0, 0, 0)):
    return bytes([
        192 | _flash_index & 15,
        129,
        clkDiv,
        lineMode,
        chipSelIndirect,
        chipSelDirect,
        chipTypeId,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0])


def set_read_id():
    return bytes([
        192 | _flash_index & 15,
        0,
        4,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0])


def set_read_rf_check():
    return bytes([
        192 | _flash_index & 15,
        30,
        5,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0])


def set_start_rf_check():
    return bytes([
        192 | _flash_index & 15,
        31,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0])


def set_reset():
    return bytes([
        192 | _flash_index & 15,
        131,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0])


def set_crc(addr, length):
    return bytes([
        192 | _flash_index & 15,
        130,
        length & 255,
        length >> 8 & 255,
        length >> 16 & 255,
        length >> 24 & 255,
        addr & 255,
        addr >> 8 & 255,
        addr >> 16 & 255,
        addr >> 24 & 255,
        0,
        0,
        0,
        0,
        0,
        0])


def set_chip_ver():
    return bytes([
        192 | _flash_index & 15,
        132,
        4,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0])


def set_encrypt(is_encrypt, key):
    return bytes([
        192 | _flash_index & 15,
        133,
        is_encrypt,
        key & 255,
        key >> 8,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0])


def set_write_byte(addr, length):
    return bytes([
        192 | _flash_index & 15,
        129,
        length & 255,
        length >> 8 & 255,
        length >> 16 & 255,
        length >> 24 & 255,
        addr & 255,
        addr >> 8 & 255,
        addr >> 16 & 255,
        addr >> 24 & 255,
        0,
        0,
        0,
        0,
        0,
        0])


def set_write_page(addr, length):
    return bytes([
        192 | _flash_index & 15,
        2,
        length & 255,
        length >> 8 & 255,
        length >> 16 & 255,
        length >> 24 & 255,
        addr & 255,
        addr >> 8 & 255,
        addr >> 16 & 255,
        addr >> 24 & 255,
        0,
        0,
        0,
        0,
        0,
        0])


def set_write_page_2(addr, length):
    return bytes([
        192 | _flash_index & 15,
        27,
        length & 255,
        length >> 8 & 255,
        length >> 16 & 255,
        length >> 24 & 255,
        addr & 255,
        addr >> 8 & 255,
        addr >> 16 & 255,
        addr >> 24 & 255,
        0,
        0,
        0,
        0,
        0,
        0])


def set_erase_4K(addr):
    return bytes([
        192 | _flash_index & 15,
        3,
        0,
        0,
        0,
        0,
        addr & 255,
        addr >> 8 & 255,
        addr >> 16 & 255,
        addr >> 24 & 255,
        0,
        0,
        0,
        0,
        0,
        0])


def set_erase_4K_2(addr):
    return bytes([
        192 | _flash_index & 15,
        28,
        0,
        0,
        0,
        0,
        addr & 255,
        addr >> 8 & 255,
        addr >> 16 & 255,
        addr >> 24 & 255,
        0,
        0,
        0,
        0,
        0,
        0])


def set_erase_32K(addr):
    return bytes([
        192 | _flash_index & 15,
        4,
        0,
        0,
        0,
        0,
        addr & 255,
        addr >> 8 & 255,
        addr >> 16 & 255,
        addr >> 24 & 255,
        0,
        0,
        0,
        0,
        0,
        0])


def set_erase_64K(addr):
    return bytes([
        192 | _flash_index & 15,
        5,
        0,
        0,
        0,
        0,
        addr & 255,
        addr >> 8 & 255,
        addr >> 16 & 255,
        addr >> 24 & 255,
        0,
        0,
        0,
        0,
        0,
        0])


def set_erase_64K_2(addr):
    return bytes([
        192 | _flash_index & 15,
        29,
        0,
        0,
        0,
        0,
        addr & 255,
        addr >> 8 & 255,
        addr >> 16 & 255,
        addr >> 24 & 255,
        0,
        0,
        0,
        0,
        0,
        0])


def set_erase_chip():
    return bytes([
        192 | _flash_index & 15,
        6,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0])


def set_read(addr, length):
    return bytes([
        192 | _flash_index & 15,
        7,
        length & 255,
        length >> 8 & 255,
        length >> 16 & 255,
        length >> 24 & 255,
        addr & 255,
        addr >> 8 & 255,
        addr >> 16 & 255,
        addr >> 24 & 255,
        0,
        0,
        0,
        0,
        0,
        0])


def set_fast_read(addr, length):
    return bytes([
        192 | _flash_index & 15,
        8,
        length & 255,
        length >> 8 & 255,
        length >> 16 & 255,
        length >> 24 & 255,
        addr & 255,
        addr >> 8 & 255,
        addr >> 16 & 255,
        addr >> 24 & 255,
        0,
        0,
        0,
        0,
        0,
        0])


def set_write_ram(addr, length):
    return bytes([
        192 | _flash_index & 15,
        9,
        length & 255,
        length >> 8 & 255,
        length >> 16 & 255,
        length >> 24 & 255,
        addr & 255,
        addr >> 8 & 255,
        addr >> 16 & 255,
        addr >> 24 & 255,
        0,
        0,
        0,
        0,
        0,
        0])


def set_run_ram(addr):
    return bytes([
        192 | _flash_index & 15,
        10,
        0,
        0,
        0,
        0,
        addr & 255,
        addr >> 8 & 255,
        addr >> 16 & 255,
        addr >> 24 & 255,
        0,
        0,
        0,
        0,
        0,
        0])

null_ptr = POINTER(c_int)()

class flash_usb(flash):
    
    def __init__(self = None, owner_notifyer = None, this_config = None, index = None, bb = None):
        (pid, vid, path, vol, serial_no) = bb
        super().__init__(owner_notifyer, this_config, index, pid, vid, path, vol, **('pid', 'vid', 'path', 'volume'))
        self.chip_name = _usb_serial_to_chip_name(serial_no)
        self.rf_check = self.this_config.read('rf_check', 'current')
        self.restore_factory = self.this_config.read('restore_factory', 'current')
        if self.chip_name == 'sl6801':
            self.restart_data = util_func.get_file_data(env.RESTART_BIN_PATH)[256:]
            self.cal_frequent_drift = util_func.get_file_data(env.RF_CHECK_6801_BIN_PATH)[1024:]
        elif self.chip_name == 'sl6806':
            self.codefile_data = util_func.get_file_data(env.CODEFILE6806_BIN_PATH)
            self.cal_frequent_drift = util_func.get_file_data(env.RF_CHECK_6806_BIN_PATH)[1088:]
        self.intel_flash_data = util_func.get_file_data(env.SL6801_INTEL_FLASH_BIN_PATH)[256:]

    
    def new_msg(self):
        msg = dll_msg()
        (msg.pid, msg.vid, msg.path, msg.volume) = (self.pid, self.vid, self.path, self.volume)
        return msg

    
    def read(self, cdb_len, cdb, out_len, out):
        return dll_read(byref(self.new_msg()), cdb_len, cdb, out_len, out)

    
    def write(self, cdb_len, cdb, out_len, out):
        return dll_write(byref(self.new_msg()), cdb_len, cdb, out_len, out)

    
    def system_init(self):
        cdb = set_init(2, **('clkDiv',))
        time.sleep(0.002)
        self.write(len(cdb), cdb, 0, null_ptr)

    
    def system_reset(self):
        cdb = set_reset()
        time.sleep(0.002)
        self.write(len(cdb), cdb, 0, null_ptr)

    
    def system_flash_id(self):
        cdb = set_read_id()
        out = bytes(4)
        time.sleep(0.002)
        self.read(len(cdb), cdb, len(out), out)
        return out.hex()

    
    def get_crc_16(self, start_addr, length):
        cdb = set_crc(start_addr, length)
        out = bytes(2)
        time.sleep(0.002)
        self.read(len(cdb), cdb, len(out), out)
        return int.from_bytes(out, 'little', **('byteorder',))

    
    def read_bytes(self, addr, length):
        cdb = set_read(addr, length)
        out = bytes(length)
        if self.read(len(cdb), cdb, length, out) != 0:
            return out

    
    def write_byte(self, data, start_addr, length):
        cdb = set_write_byte(start_addr, length)
        return self.write(len(cdb), cdb, length, data)

    
    def erase_4K(self, start_addr):
        cdb = set_erase_4K(start_addr)
        time.sleep(0.002)
        return self.write(len(cdb), cdb, 0, null_ptr)

    
    def erase_64K(self, start_addr):
        cdb = set_erase_64K(start_addr)
        time.sleep(0.002)
        return self.write(len(cdb), cdb, 0, null_ptr)

    
    def write_page(self, data, start_addr, length):
        cdb = set_write_page(start_addr, length)
        time.sleep(0.002)
        return self.write(len(cdb), cdb, length, data)

    
    def run_ram(self, data, write_addr, run_addr, data_len):
        cdb = set_write_ram(write_addr, data_len)
        self.write(len(cdb), cdb, data_len, data)
        cdb = set_run_ram(run_addr)
        return self.write(len(cdb), cdb, 0, null_ptr)

    
    def run_ram_only(self, run_addr):
        cdb = set_run_ram(run_addr)
        return self.write(len(cdb), cdb, 0, null_ptr)

    
    def erase_4K_2(self, start_addr):
        cdb = set_erase_4K_2(start_addr)
        time.sleep(0.002)
        return self.write(len(cdb), cdb, 0, null_ptr)

    
    def erase_64K_2(self, start_addr):
        cdb = set_erase_64K_2(start_addr)
        time.sleep(0.002)
        return self.write(len(cdb), cdb, 0, null_ptr)

    
    def write_page_2(self, data, start_addr, length):
        cdb = set_write_page_2(start_addr, length)
        time.sleep(0.002)
        return self.write(len(cdb), cdb, length, data)

    
    def write_block(self, addr, data):
        data_length = len(data)
        if data_length % 4096 != 0:
            data += bytes(4096 - data_length % 4096)
            data_length += 4096 - data_length % 4096
        erase_func = self.erase_64K
        for trytime in range(3):
            res = 0
            if data_length < 65536:
                for i in range(int((data_length + 4096 - 1) / 4096)):
                    res = self.erase_4K(addr + i * 4096)
            else:
                res = erase_func(addr)
            if res == 0:
                time.sleep(0.1)
                continue
            if self.chip_name == 'sl6801':
                res = self.write_page_2(data, addr, data_length)
            elif self.chip_name == 'sl6806':
                res = self.write_page(data, addr, data_length)
            if res == 0:
                time.sleep(0.05)
                continue
            crc = self.get_crc_16(addr, data_length)
            datacrc = dll_calc_crc16(data, data_length)
            if crc != datacrc:
                if trytime < 2:
                    self.error_code = 1008
                    continue
                return (False, 'crc check err.')
            return (None, 'Write block 0x%x; length: 0x%x success.' % (addr, data_length))
            return (False, 'Write block 0x%x fail.' % addr)

    
    def _rf_check_start(self):
        cdb = set_start_rf_check()
        time.sleep(0.002)
        self.write(len(cdb), cdb, 0, null_ptr)
        return True

    
    def _rf_check_get_result(self):
        cdb = set_read_rf_check()
        out = bytes(14)
        time.sleep(0.002)
        self.read(len(cdb), cdb, len(out), out)
        return (True, out)

    
    def set_partiton(self, pct_0, pct_1):
        return (True, True)

    
    def fopen(self, path):
        return True

    
    def fwrite(self, data):
        return True

    
    def fclose(self):
        return True

    
    def _sl6806_download_path(self, ram_run_bin, addr_dwon, addr_run):
        self.system_init()
        OFFSET = 128
        codedata124 = self.codefile_data + bytes(OFFSET - 4 - len(self.codefile_data))
        restart128align = ram_run_bin + bytes(OFFSET - len(ram_run_bin) % OFFSET)
        blocks = (lambda .0 = None: [ restart128align[i:i + OFFSET] for i in .0 ])(range(0, len(restart128align), OFFSET))
        for i in range(len(blocks)):
            towrite = struct.pack('124sI128s', codedata124, addr_dwon + i * OFFSET, blocks[i])
            self.write_page(towrite, 4173824, 256)
            self.run_ram_only(8392321)
        self.run_ram_only(addr_run + 1)

    
    def _rf_check_prepare(self):
        if self.chip_name == 'sl6801':
            self.system_init()
            self.run_ram(self.cal_frequent_drift, 8716288, 8716369, len(self.cal_frequent_drift))
            time.sleep(0.1)
            return None
        if None.chip_name == 'sl6806':
            return None

    
    def _rf_check_only(self):
        self.owner_notifyer.write(('start_bron_update', {
            'index': self.index,
            'error_code': 0,
            'error_message': 'RF check begin ...',
            'rf_result': 'Doing' }))
        self._rf_check_prepare()
        ret = self._rf_check_start()
        if ret is not True:
            self.error_code = 1003
            self.rf_result = False
            return False
        try_times = None
        if try_times < 50:
            try_times += 1
            time.sleep(0.1)
            (ret, body) = self._rf_check_get_result()
            if ret is not True:
                self.error_code = 1004
                self.rf_result = False
                return False
            res = None.from_bytes(body[4:6], 'little', True, **('signed',))
            if res == 32767:
                continue
            if res == 32766 or res == 32765:
                self.error_code = 1004
                self.rf_result = False
                return False
            self.dcxo_trim = None.from_bytes(body[0:4], 'little', True, **('signed',))
            self.freq_drift = int.from_bytes(body[6:10], 'little', False, **('signed',))
            self.rf_power = int.from_bytes(body[10:14], 'little', False, **('signed',))
            self.error_code = 0
            self.rf_result = True
            self.owner_notifyer.write(('start_bron_update', {
                'index': self.index,
                'error_code': 0,
                'error_message': 'RF check success: rf_result:%d, dcxo_trim: %d, rf_power: %d' % (self.rf_result, self.dcxo_trim, self.rf_power),
                'rf_result': self.rf_result,
                'dcxo_trim': self.dcxo_trim }))
            return True
        self.error_code = None
        self.rf_result = False
        return False

    
    def _download_only(self, bin_data):
        self.system_init()
        flash_id = self.system_flash_id()
        self.owner_notifyer.write(('start_bron_update', {
            'index': self.index,
            'percent': 2,
            'error_code': 0,
            'error_message': 'Flash data ID: %s' % flash_id }))
        if self.chip_name == 'sl6801':
            self.run_ram(self.intel_flash_data, 8585472, 8585475, len(self.intel_flash_data))
        elif self.chip_name == 'sl6806':
            pass
        else:
            self.error_code = 1007
            return None
        erase_length = None
        fc = bin_data
        fl = len(fc)
        blocks = (lambda .0 = None: [ fc[i:i + erase_length] for i in .0 ])(range(0, fl, erase_length))
        self.download_present = 0
        _percent = 0
        res = False
        for i in range(len(blocks) - 1, -1, -1):
            (res, reason) = self.write_block(erase_length * i, blocks[i])
            if res is False:
                self.download_present = self.download_present + len(blocks[i]) / fl / 100
                self.error_code = 1007
                return None
            _percent = None + len(blocks[i]) / fl / 100
            if i == 0:
                _percent = 100
            if _percent != self.download_present:
                self.download_present = _percent
                self.owner_notifyer.write(('start_bron_update', {
                    'index': self.index,
                    'percent': int(self.download_present),
                    'error_code': self.error_code,
                    'error_message': reason }))

    
    def _upload_only(self, addr, length = (0, 0)):
        self.system_init()
        flash_id = self.system_flash_id()
        self.owner_notifyer.write(('start_bron_update', {
            'index': self.index,
            'percent': 0,
            'error_code': 0,
            'error_message': 'Flash data ID: %s' % flash_id }))
        bin_file_bytes = bytes(0)
        if length == 0:
            blocks = int(256)
        else:
            blocks = int(length / 8192)
        for i in range(blocks):
            _len = 8192
            _start = i * 8192 + addr
            out = self.read_bytes(_start, _len)
            time.sleep(0.1)
            if out is not None:
                bin_file_bytes += out
                self.owner_notifyer.write(('start_bron_update', {
                    'index': self.index,
                    'percent': int((100 / blocks) * i),
                    'error_code': self.error_code,
                    'error_message': 'upload ... 0x%x.' % _start }))
                continue
            self.error_code = 1007
            return bin_file_bytes
            return bin_file_bytes

    
    def download_only(self, download_file_path):
        self.owner_notifyer.write(('start_bron_update', {
            'index': self.index,
            'percent': 1,
            'error_code': 0 }))
        if self.chip_name == 'sl6806':
            self._sl6806_download_path(self.cal_frequent_drift, 8781888, 8785984)
        _up_file_content = util_func.get_file_data(download_file_path)
        if self.rf_check:
            if self._rf_check_only():
                self._prepare_new_add_kvs()
                bin_data = self.acquire_up_file_content_by_factory_index(_up_file_content)
                self.bt_name = self.all_psm_dict.get('bt_name', b'null').decode('utf-8')
            else:
                return None
            bin_data = None.acquire_up_file_content_by_engineer_device(_up_file_content)
            self._download_only(bin_data)
            if up_parser.is_upex_file(_up_file_content):
                fd = self._get_tar_name_contents_dict(download_file_path)
                if self.error_code == 0:
                    self._download_nand(fd)
        self._report()
        if self.this_config.read('restart_after_burn', 'current'):
            if self.chip_name == 'sl6801':
                self.run_ram(self.restart_data, 8519936, 8519937, len(self.restart_data))
                return None
            if None.chip_name == 'sl6806':
                self.system_reset()
                return None
            return None

    
    def upload_only(self, upload_file_path):
        _size = self.this_config.read('flash_size', 'current') * 1024
        bin_file_bytes = self._upload_only(0, _size, **('addr', 'length'))
        self.owner_notifyer.write(('start_bron_update', {
            'index': self.index,
            'is_success': True,
            'percent': 99,
            'error_message': 'saving to up file: %s, please wait...' % upload_file_path }))
        with open(upload_file_path, 'wb') as f:
            f.write(up_parser.make_up_header(bin_file_bytes) + bin_file_bytes)
            None(None, None, None)
        with None:
            if not None:
                pass
        self.owner_notifyer.write(('start_bron_update', {
            'index': self.index,
            'is_success': True,
            'percent': 100,
            'error_message': 'Done.' }))
        return True

    
    def erase_only(self):
        self.owner_notifyer.write(('start_bron_update', {
            'index': self.index,
            'percent': 0,
            'error_code': 0,
            'is_success': True,
            'is_finish': False,
            'error_message': 'Begin erase chip...' }))
        self.system_init()
        self.owner_notifyer.write(('start_bron_update', {
            'index': self.index,
            'percent': 25,
            'error_code': 0,
            'is_success': True,
            'is_finish': False,
            'error_message': 'Erase chip init OK.' }))
        cdb = set_erase_chip()
        self.write(len(cdb), cdb, 0, null_ptr)
        self.owner_notifyer.write(('start_bron_update', {
            'index': self.index,
            'percent': 75,
            'error_code': 0,
            'is_success': True,
            'is_finish': False,
            'error_message': 'Erase chip OK.' }))
        self.system_reset()
        self.owner_notifyer.write(('start_bron_update', {
            'index': self.index,
            'percent': 100,
            'error_code': 0,
            'is_success': True,
            'is_finish': True,
            'error_message': 'Erase chip success.' }))
        return True

    __classcell__ = None

