# Source Generated with Decompyle++
# File: mass_storage_dll.pyc (Python 3.10)

from ctypes import *
from  import env

class mass_storage_dll_loader:
    
    class DevMsg(Structure):
        _fields_ = [
            ('pid', c_wchar * 260),
            ('vid', c_wchar * 260),
            ('connect', c_long),
            ('path', c_wchar * 260),
            ('volume', c_wchar * 10),
            ('serial', c_char * 260)]

    
    def __init__(self):
        self.library = cdll.LoadLibrary(env.MASS_STORAGE_DLL_PATH)
        v = c_char_p('SMTLINK'.encode())
        p = c_char_p('DEVICE'.encode())
        self.library.mass_storage_init(v, p)

    
    def API_reset(self):
        return self.library.mass_storage_reset

    
    def API_size(self):
        return self.library.mass_storage_size

    
    def API_get(self):
        return self.library.mass_storage_get

    
    def API_read(self):
        return self.library.mass_storage_device_read

    
    def API_write(self):
        return self.library.mass_storage_device_write

    
    def API_download_file_check(self):
        return self.library.mass_storage_download_file_parse

    
    def API_calc_crc16(self):
        return self.library.mass_storage_calc_data_crc16


dll = mass_storage_dll_loader()
dll_reset = dll.library.mass_storage_reset
dll_size = dll.library.mass_storage_size
dll_get = dll.library.mass_storage_get
dll_read = dll.library.mass_storage_device_read
dll_write = dll.library.mass_storage_device_write
dll_download_file_check = dll.library.mass_storage_download_file_parse
dll_calc_crc16 = dll.library.mass_storage_calc_data_crc16
dll_set_working_mode = dll.library.mass_storage_set_working_mode

def dll_msg():
    return mass_storage_dll_loader.DevMsg()

