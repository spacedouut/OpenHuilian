# Source Generated with Decompyle++
# File: com_dll.pyc (Python 3.10)

from ctypes import *
from  import env

class com_dll_loader:
    
    def __init__(self):
        self.library = None

    
    def open(self, port, index, bitrate):
        return self.library.com_device_open(port, index, bitrate)

    
    def close(self, index):
        return self.library.com_device_close(index)

    
    def connect_boot(self, index):
        return self.library.com_device_connect_boot_rom(index)

    
    def connect_startup(self, index):
        return self.library.com_device_connect_startup(index)

    
    def ram_download(self, index, data, data_len, addr):
        return self.library.com_device_update_boot_ram(index, data, data_len, addr)

    
    def ram_run(self, index, addr):
        return self.library.com_device_run_boot_ram(index, addr)

    
    def chip_erase(self, index):
        return self.library.com_device_chip_erase_flash(index)

    
    def write(self, index, data, length, addr):
        return self.library.com_device_write_flash(index, data, length, addr)

    
    def read(self, index, data, length, addr):
        return self.library.com_device_read_flash(index, data, length, addr)

    
    def get_crc(self, index, addr, length, out):
        return self.library.com_device_get_check_sum(index, addr, length, out)

    
    def start_drift(self, index):
        return self.library.com_device_start_drift(index)

    
    def get_drift_val(self, index, out, out_len):
        return self.library.com_device_get_drift_val(index, out, out_len)

    
    def reset_baudrate(self, index, bautrate):
        return self.library.com_device_reset_baudrate(index, bautrate)

    
    def get_gyro_offset(self, index, two, out, out_len):
        return self.library.com_device_get_gyro_offset(index, two, out, out_len)

    
    def set_partiton(self, index, pct_0, pct_1):
        out = bytes(1)
        result = self.library.com_device_set_partition(index, pct_0, pct_1, out)
        return (result, out)

    
    def fopen(self, index, path):
        return self.library.com_device_fopen(index, path)

    
    def fwrite(self, index, data, length):
        return self.library.com_device_fwrite(index, data, length)

    
    def fclose(self, index):
        return self.library.com_device_fclose(index)



class com6801_dll_loader(com_dll_loader):
    
    def __init__(self = None):
        super().__init__()
        self.library = cdll.LoadLibrary(env.COM_DLL_PATH)

    
    def set_partiton(self, index, pct_0, pct_1):
        pass

    
    def fopen(self, index, path):
        pass

    
    def fwrite(self, index, data, length):
        pass

    
    def fclose(self, index):
        pass

    __classcell__ = None


class com6806_dll_loader(com_dll_loader):
    
    def __init__(self = None):
        super().__init__()
        self.library = cdll.LoadLibrary(env.COM_6806_DLL_PATH)

    
    def get_gyro_offset(self, index, two, out, out_len):
        pass

    __classcell__ = None

