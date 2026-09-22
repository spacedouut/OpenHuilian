# Source Generated with Decompyle++
# File: flash_uart_6801.pyc (Python 3.10)

import time
from  import util_func
from flash_base import flash
from com_dll import *
from  import up_parser
null_ptr = POINTER(c_int)()
POLY_CRC16 = 4129
CRC16_INIT = 65535
RAM_FLASH_OP_LENGTH = 128
UART_RECV_TIME_OUT = 10

def crc16_onebyte(lastcrc, data):
    for i in range(8):
        if (data << i ^ lastcrc >> 8) & 128:
            lastcrc <<= 1
            lastcrc = lastcrc ^ POLY_CRC16
            continue
        lastcrc <<= 1
    return lastcrc & 65535


def calc_crc(init, data, length):
    for i in range(length):
        init = crc16_onebyte(init, data[i])
    return init


class flash_uart(flash):
    
    def __init__(self = None, owner_notifyer = None, this_config = None, index = None, com_port = None, download_up_file_path = None):
        super().__init__(owner_notifyer, this_config, index)
        self.chip_name = up_parser.get_up_chip_name_lower(util_func.get_file_data(download_up_file_path))
        if self.chip_name == 'sl6806':
            self.UR_DLL = com6806_dll_loader()
        else:
            self.UR_DLL = com6801_dll_loader()
        self.rf_check = self.this_config.read('rf_check', 'current')
        self.gyro_check = self.this_config.read('gyroscope_check', 'current')
        self.com_port = com_port
        self.download_is_ex = False
        self.reinit()

    
    def reinit(self):
        self.prepare_result = ''
        self.rf_result = ''
        self.dcxo_trim = 0
        self.rf_power = 0
        self.freq_drift = 0
        self.gyro_result = ''
        self.gyro_data = bytes(18)
        self.gyro_data_dict = {
            'gyro_x': 0,
            'gyro_y': 0,
            'gyro_z': 0,
            'accel_x': 0,
            'accel_y': 0,
            'accel_z': 0 }
        self.download_present = 0
        self.UR_DLL.close(self.index)
        self.UR_DLL.open(self.com_port, self.index, 115200)

    
    def sync_boot(self):
        ret = self.UR_DLL.connect_boot(self.index)
        if ret:
            return True

    
    def sync_startup(self):
        ret = self.UR_DLL.connect_startup(self.index)
        if ret:
            return True

    
    def reset_bautrate(self, bautrate):
        ret = self.UR_DLL.reset_baudrate(self.index, bautrate)
        if ret:
            return True

    
    def write_ram(self, data, addr, data_len):
        ret = self.UR_DLL.ram_download(self.index, data, data_len, addr)
        if ret == 0:
            return False

    
    def run_ram(self, data, addr, data_len):
        ret = self.UR_DLL.ram_download(self.index, data, data_len, addr)
        if ret == 0:
            return False
        ret = None.UR_DLL.ram_run(self.index, addr)
        if ret == 0:
            return False

    
    def read_from_ram(self, addr, length):
        data = b''
        return data

    
    def erase_all(self):
        ret = self.UR_DLL.chip_erase(self.index)
        if ret == 0:
            return False

    
    def write_flash(self, addr, data, length):
        ret = self.UR_DLL.write(self.index, data, length, addr)
        if ret == 0:
            return (False, 'Write block 0x%x fail.' % addr)
        return (None, 'Write block 0x%x success.' % addr)

    
    def read_flash(self, addr, length):
        data = b''
        return data

    
    def get_flash_crc(self, addr, length):
        out = bytes(4)
        ret = self.UR_DLL.get_crc(self.index, addr, length, out)
        if ret == 0:
            return (False, out)
        return (None, out)

    
    def set_partiton(self, pct_0, pct_1):
        (ret, is_emmc) = self.UR_DLL.set_partiton(self.index, pct_0, pct_1)
        if ret == 0:
            return (False, is_emmc)
        return (None, is_emmc)

    
    def fopen(self, path):
        ret = self.UR_DLL.fopen(self.index, path)
        if ret == 0:
            return False

    
    def fwrite(self, data):
        ret = self.UR_DLL.fwrite(self.index, data, len(data))
        if ret == 0:
            return False

    
    def fclose(self):
        ret = self.UR_DLL.fclose(self.index)
        if ret == 0:
            return False

    
    def _rf_check_start(self):
        ret = self.UR_DLL.start_drift(self.index)
        if ret == 0:
            return False

    
    def _rf_check_get_result(self):
        out = bytes(14)
        ret = self.UR_DLL.get_drift_val(self.index, out, len(out))
        if ret == 0:
            return (False, out)
        return (None, out)

    
    def _rf_check_only(self):
        self.owner_notifyer.write(('start_bron_update', {
            'index': self.index,
            'error_code': 0,
            'error_message': util_func.code_info(),
            'rf_result': 'Doing' }))
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
                'error_message': util_func.code_info(),
                'rf_result': self.rf_result,
                'dcxo_trim': self.dcxo_trim }))
            return True
        self.error_code = None
        self.rf_result = False
        return False

    
    def _gyro_check(self):
        self.owner_notifyer.write(('start_bron_update', {
            'index': self.index,
            'error_code': 0,
            'error_message': util_func.code_info(),
            'gyroscope_result': 'Doing' }))
        out = bytes(18)
        if self.UR_DLL.get_gyro_offset(self.index, 2, out, len(out)) == 0:
            self.error_code = 1021
            self.gyro_result = False
            return False
        self.error_code = None
        self.gyro_result = True
        self.gyro_data = out[0:12]
        self.gyro_data_dict = {
            'gyro_x': int.from_bytes(self.gyro_data[0:2], 'little', True, **('signed',)),
            'gyro_y': int.from_bytes(self.gyro_data[2:4], 'little', True, **('signed',)),
            'gyro_z': int.from_bytes(self.gyro_data[4:6], 'little', True, **('signed',)),
            'accel_x': int.from_bytes(self.gyro_data[6:8], 'little', True, **('signed',)),
            'accel_y': int.from_bytes(self.gyro_data[8:10], 'little', True, **('signed',)),
            'accel_z': int.from_bytes(self.gyro_data[10:12], 'little', True, **('signed',)) }
        self.owner_notifyer.write(('start_bron_update', {
            'index': self.index,
            'error_code': 0,
            'error_message': util_func.code_info(),
            'gyroscope_result': self.gyro_result,
            'gyroscope_data': self.gyro_data_dict }))
        return True

    
    def _download_only(self, bin_data):
        erase_length = 4096
        if self.erase_all() is not True:
            self.error_code = 1006
            return False
        fc = None
        fl = len(fc)
        blocks = (lambda .0 = None: [ fc[i:i + erase_length] for i in .0 ])(range(0, fl, erase_length))
        self.download_present = 0
        _percent = 0
        _precent_base = 49 if self.download_is_ex else 99
        res = False
        for i in range(len(blocks) - 1, -1, -1):
            (res, reason) = self.write_flash(erase_length * i, blocks[i], len(blocks[i]))
            if res is False:
                self.download_present = self.download_present + len(blocks[i]) / fl / _precent_base
                self.error_code = 1007
            else:
                _percent = _percent + len(blocks[i]) / fl / _precent_base
                if int(_percent) != int(self.download_present):
                    self.download_present = _percent
                    self.owner_notifyer.write(('start_bron_update', {
                        'index': self.index,
                        'percent': int(self.download_present) }))
            if res:
                old_crc = 0
                for i in range(0, fl):
                    old_crc += fc[i]
                (ret, crc32) = self.get_flash_crc(0, fl)
                if ret is False:
                    self.error_code = 1008
                    return False
                new_crc = None.from_bytes(crc32, 'little', True, **('byteorder', 'signed'))
                if old_crc != new_crc:
                    self.error_code = 1008
                    return False
                return None
            return None

    
    def _download_prepare(self):
        self.owner_notifyer.write(('start_bron_update', {
            'index': self.index,
            'error_code': 0,
            'error_message': util_func.code_info(),
            'prepare': 'Doing' }))
        baudrate = int(self.this_config.read('bron_uart_bitrate', 'current'))
        if self.chip_name == 'sl6806':
            self.intel_flash_vector = util_func.get_file_data(env.UART_LOADER_6806_BIN_PATH)[0:1024]
            if self.write_ram(self.intel_flash_vector, 8863744, len(self.intel_flash_vector)) is not True:
                self.error_code = 1109
                self.prepare_result = False
                return False
            self.intel_flash_data = None.get_file_data(env.UART_LOADER_6806_BIN_PATH)[1088:]
            if self.run_ram(self.intel_flash_data, 8454208, len(self.intel_flash_data)) is not True:
                self.error_code = 1009
                self.prepare_result = False
                return False
        if self.chip_name == 'sl6801':
            self.intel_flash_data = util_func.get_file_data(env.UART_LOADER_6801_BIN_PATH)[1088:]
            if self.run_ram(self.intel_flash_data, 8716288, len(self.intel_flash_data)) is not True:
                self.error_code = 1009
                self.prepare_result = False
                return False
        self.error_code = 1009
        self.prepare_result = False
        return False
        time.sleep(0.2)
        if self.sync_startup() is not True:
            self.error_code = 1010
            self.prepare_result = False
            return False
        if None.reset_bautrate(baudrate) is not True:
            self.error_code = 1011
            self.prepare_result = False
            return False
        self.prepare_result = None
        self.UR_DLL.close(self.index)
        self.UR_DLL.open(self.com_port, self.index, baudrate)
        if self.chip_name == 'sl6806':
            time.sleep(0.5)
        else:
            time.sleep(0.1)
        self.owner_notifyer.write(('start_bron_update', {
            'index': self.index,
            'error_code': 0,
            'error_message': util_func.code_info(),
            'prepare': self.prepare_result }))
        return True

    
    def _download_flash(self, bin_data):
        self._prepare_new_add_kvs()
        bin_data = self.acquire_up_file_content_by_factory_index(bin_data)
        self.bt_name = self.all_psm_dict.get('bt_name', b'null').decode('utf-8')
        if self._download_only(bin_data):
            self.owner_notifyer.write(('start_bron_update', {
                'index': self.index,
                'percent': 50 if self.download_is_ex else 100 }))
            return True

    
    def download_only(self, download_file_path):
        self.error_code = 0
        if self._download_prepare() is False:
            self._report()
            return None
        if None.rf_check and self._rf_check_only() is False:
            self._report()
            return None
        if None.gyro_check and self._gyro_check() is False:
            self._report()
            return None
        _up_file_content_ex = None.get_file_data(download_file_path)
        if up_parser.is_up_file(_up_file_content_ex):
            self.download_is_ex = False
            self._download_flash(_up_file_content_ex)
        elif up_parser.is_upex_file(_up_file_content_ex):
            self.download_is_ex = True
            fd = self._get_tar_name_contents_dict(download_file_path)
            if self._download_flash(fd['restore.up']) is True:
                fd.pop('restore.up')
                self._download_nand(fd)
        self._report()

    
    def upload_only(self, upload_file_path):
        return False

    
    def erase_only(self):
        return self.erase_all()

    __classcell__ = None

