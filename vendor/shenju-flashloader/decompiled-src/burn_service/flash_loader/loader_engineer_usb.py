# Source Generated with Decompyle++
# File: loader_engineer_usb.pyc (Python 3.10)

from ctypes import *
import threading
import time
import os
from mass_storage_dll import dll_get, dll_size, dll_msg, dll_set_working_mode
from  import flash_usb_6801 as flash_usb
from urllib import parse as url_parser
from  import util_func

class engineer_devices_loader:
    
    def __init__(self, owner_notifyer, this_config):
        self.owner_notifyer = owner_notifyer
        self.this_config = this_config
        self._engineer_devices_loader__devices = []
        dll_set_working_mode('engineer')
        threading.Thread(self.__run, True, **('target', 'daemon')).start()

    
    def __device_mount_get(self, is_mount, timeout = (1,)):
        msg = dll_msg()
        if dll_size(is_mount) > 0:
            dll_get(is_mount, byref(msg))
            return (msg.pid, msg.vid, msg.path, msg.volume, msg.serial)
        if None == 0:
            return None
        timeout = None - 1
        time.sleep(1)
        continue

    
    def __run(self):
        bb = self.__device_mount_get(1, 1)
        if bb is not None:
            (pid, vid, path, vol, serial_no) = bb
            dev = flash_usb.flash_usb(self.owner_notifyer, self.this_config, len(self._engineer_devices_loader__devices), bb)
            self._engineer_devices_loader__devices.append(dev)
            print(f'''append device path:{path}, vol:{vol}''')
            dev.index = self._engineer_devices_loader__devices.index(dev)
            dev.set_attrib(pid, vid, path, vol, True)
            self.owner_notifyer.write(('slot_polling', {
                'slot': vol,
                'slot_on': True,
                'error_code': 0,
                'error_message': 'chip name: %s' % dev.chip_name }))
            if self.this_config.read('auto_download', 'current'):
                self.download(dev.index)
        bb = self.__device_mount_get(0, 1)
        if bb is not None:
            (pid, vid, path, vol, serial_no) = bb
            for dev in self._engineer_devices_loader__devices:
                if dev.volume == vol:
                    dev.set_attrib(pid, vid, path, vol, False)
                    self._engineer_devices_loader__devices.remove(dev)
                    print(f'''remove device path:{path}, vol:{vol}''')
                    for d in self._engineer_devices_loader__devices:
                        d.index = self._engineer_devices_loader__devices.index(d)
                    self.owner_notifyer.write(('slot_polling', {
                        'slot': vol,
                        'slot_on': False }))
        continue

    
    def download(self, index):
        if self.this_config.read('erase_only', 'current'):
            self.erase(index)
            return None
        url = None.unquote(self.this_config.read('bron_up_file_url'))
        if os.path.exists(url) is False:
            self.owner_notifyer.write(('start_bron_update', {
                'index': index,
                'is_success': False,
                'error_code': 1014,
                'percent': 0,
                'error_message': '要烧录的文件不存在.' }))
            return False
        if None(self._engineer_devices_loader__devices) >= index + 1:
            threading.Thread(self._engineer_devices_loader__devices[index].download_only, True, (url,), **('target', 'daemon', 'args')).start()
            return None

    
    def upload(self, index, bin_file_path):
        threading.Thread(self._engineer_devices_loader__devices[index].upload_only, True, (bin_file_path,), **('target', 'daemon', 'args')).start()

    
    def erase(self, index):
        threading.Thread(self._engineer_devices_loader__devices[index].erase_only, True, **('target', 'daemon')).start()


