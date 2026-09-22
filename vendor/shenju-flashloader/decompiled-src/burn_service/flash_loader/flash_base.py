# Source Generated with Decompyle++
# File: flash_base.pyc (Python 3.10)

import time
import threading
import hashlib
import re
import tarfile
import io
from  import util_notifyer
from  import util_func
from  import up_parser

def encrypt_data_with_key(data):
    ENCRYPT_POLY_LFSR16 = 53507
    ENCRYPT_KEY = 1878
    
    def encrypt_loop_key(key = None):
        if key & 32768:
            l_temp = ENCRYPT_POLY_LFSR16
        else:
            l_temp = 0
        key = (key << 1) % 65536 ^ l_temp | key >> 15
        return key % 65535

    
    def encrypt_onebyte(l_data = None, key = None):
        l_encdata = 0
        for i in range(8, 0, -1):
            l_encdata = (l_encdata << 1) % 65536
            l_encdata |= (l_data >> i - 1 ^ key >> 15) & 1
            key = encrypt_loop_key(key)
        return (key, l_encdata % 65536)

    
    def encrypt_data(init_key = None, d = None):
        res = bytes(0)
        key = init_key
        for i in range(len(d)):
            (key, lencd) = encrypt_onebyte(d[i], key)
            res += int.to_bytes(lencd, 1, 'little')
        return res

    return encrypt_data(ENCRYPT_KEY, data)


def acquire_up_file_md5(setted_up_path):
    fc = util_func.get_file_data(setted_up_path)
    if fc is not None:
        m = hashlib.md5()
        flash_fc = fc[256:]
        bux16 = len(flash_fc) % 16
        if bux16 != 0:
            bux16 = 16 - bux16
            flash_fc += bytes([
                255] * bux16)
        m.update(flash_fc)
        return m.hexdigest()[8:16].upper() + '-' + m.hexdigest()[16:24].upper()


class flash(util_notifyer.notifyer):
    
    def __init__(self = None, owner_notifyer = None, this_config = None, index = None, pid = None, vid = None, path = None, volume = None):
        super().__init__(owner_notifyer)
        self.chip_name = ''
        self.this_config = this_config
        (self.index, self.pid, self.vid, self.path, self.volume, self.power) = (index, pid, vid, path, volume, False)
        self.bt_addr = '00:00:00:00:00:00'
        self.incr = ''
        self.bt_name = ''
        self.device_id = ''
        self.error_code = 0
        self.new_add_kvs_list = []
        self.all_psm_dict = { }
        self.up_config_mutex = threading.Lock()
        self.prepare_result = ''
        self.rf_check = False
        self.restore_factory = False
        self.rf_result = ''
        self.dcxo_trim = 0
        self.rf_power = 0
        self.freq_drift = 0
        self.gyro_check = False
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

    
    def set_attrib(self, pid, vid, path, volume, power):
        (self.pid, self.vid, self.path, self.volume, self.power) = (pid, vid, path, volume, power)

    
    def mac_self_add(self = None, mac_string = None, v = None, mac_format = (1, ':')):
        hex_str = hex(int(mac_string.replace(':', ''), 16) + v).replace('0x', '')
        for i in range(12 - len(hex_str)):
            hex_str = '0' + hex_str
        return mac_format.join(re.findall('.{2}', hex_str)).upper()

    
    def _get_tar_name_contents_dict(self, tar_path):
        ret = dict()
        file_like_object = io.BytesIO(util_func.get_file_data(tar_path))
        tar = tarfile.open(file_like_object, **('fileobj',))
        for member in tar.getmembers():
            f = tar.extractfile(member)
            ret[member.name] = f.read()
        return ret

    
    def set_partiton(self, pct_0, pct_1):
        return (True, 0)

    
    def fopen(self, path):
        return True

    
    def fwrite(self, data):
        return True

    
    def fclose(self):
        return True

    
    def _upload_only(self, addr, length = (0, 0)):
        return b''

    
    def _download_nand_one(self, is_emmc, fn, fc):
        if int.from_bytes(is_emmc, 'little', True, **('byteorder', 'signed')):
            fn = '1:/' + fn
        else:
            fn = '0:/' + fn
        if self.fopen(fn.encode()) is not True:
            self.error_code = 1112
            return False
        if None.fwrite(fc) is not True:
            self.error_code = 1113
            return False
        if None.fclose() is not True:
            self.error_code = 1114
            return False

    
    def _download_nand(self, fd):
