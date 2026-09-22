# Source Generated with Decompyle++
# File: loader_factory_usb.pyc (Python 3.10)

import os
from ctypes import *
import threading
import time
from  import env
from  import util_func
from serial_stm32 import uart_stm32
from mass_storage_dll import dll_get, dll_size, dll_msg, dll_reset, dll_set_working_mode
from  import flash_usb_6801 as flash_usb
from loader_factory import factory_loader
DEVICE_ON_TIME_OUT = 15

class factory_devices_loader(factory_loader):
    
    def __init__(self = None, owner_notifyer = None, this_config = None):
        super().__init__(owner_notifyer)
        self.this_config = this_config
        self._factory_devices_loader__devices = []
        self._factory_devices_loader__mt_thread_stop_ev = threading.Event()
        self._factory_devices_loader__uart_comm_thread = None
        self.bron_slot_num = int(self.this_config.read('bron_slot', 'current'))
        self._factory_devices_loader__uart = uart_stm32(self.owner_notifyer)
        self._factory_devices_loader__power_on_index = -1
        self._factory_devices_loader__serial_name = ''
        self._factory_devices_loader__slot_list = []
        dll_set_working_mode('factory')

    
    def __mt_thread_init(self):
        self._factory_devices_loader__mt_thread_stop_ev.clear()
        self._factory_devices_loader__devices.clear()
        dll_reset()
        for i in range(self.bron_slot_num):
            dev = flash_usb.flash_usb(self.owner_notifyer, self.this_config, i)
            self._factory_devices_loader__devices.append(dev)
        return True

    
    def __mt_thread_next_power_on(self):
        if self.current_can_alive_devices_num <= 0:
            return False
        if None._factory_devices_loader__power_on_index >= len(self._factory_devices_loader__slot_list) - 1:
            return False
        None._factory_devices_loader__power_on_index += 1
        self.current_can_alive_devices_num -= 1
        self._factory_devices_loader__uart.send_cmd('REQUEST_POWERON', self._factory_devices_loader__slot_list[self._factory_devices_loader__power_on_index], 0)
        return True

    
    def __mt_thread(self):
        if self.__mt_thread_init() is False:
            return None
        self.current_can_alive_devices_num = None(self.this_config.read('bron_threading', 'current'))
        no_response_try_times = 60
        total_processed = 0
        self._factory_devices_loader__power_on_index = -1
        self._factory_devices_loader__remaining_device = self.bron_slot_num
        self._factory_devices_loader__uart.start(self._factory_devices_loader__serial_name)
        self._factory_devices_loader__uart.send_cmd('READY', 0, 0)
        if no_response_try_times > 0:
            if self._factory_devices_loader__mt_thread_stop_ev.wait(0):
                print('User force stop! go to finish.')
                self._factory_devices_loader__uart.send_cmd('FINISH', 0, 0)
            ev = self._factory_devices_loader__uart.uart_one_command_do()
            if ev is True:
                no_response_try_times -= 2
                continue
            if ev is False:
                print('UART send or recv failed, go to finish.')
                self.owner_notifyer.write(('start_bron', {
                    'error_code': 1002,
                    'error_message': util_func.code_info(),
                    'total_finish': True,
                    'item': { } }))
            else:
                no_response_try_times = 60
                (func, payload0, payload1, recv_time) = ev
                if func == 'READY':
                    print('received CMD READY, this is the first time request power on.')
                    self.__mt_thread_next_power_on()
                elif func == 'REQUEST_POWERON':
                    bb = self.__device_mount_get(1, DEVICE_ON_TIME_OUT)
                    if bb is not None:
                        (pid, vid, path, vol) = bb
                        self._factory_devices_loader__devices[payload0].set_attrib(pid, vid, path, vol, True)
                        print('payload0:', payload0, 'pid', pid, 'vid', vid, 'path', path, 'vol', vol)
                        self.download(payload0)
                    else:
                        self._factory_devices_loader__uart.send_cmd('REQUEST_POWEROFF', payload0, 0)
                        print('Can not mount a new disk in 15 seconds, then power on next.')
                        self.owner_notifyer.write(('start_bron_update', {
                            'index': payload0,
                            'is_finish': True,
                            'is_success': False,
                            'error_code': 1012,
                            'error_message': util_func.code_info() }))
                    self.__mt_thread_next_power_on()
                elif func == 'PROCESS_RESULT':
                    self._factory_devices_loader__remaining_device -= 1
                    self.current_can_alive_devices_num += 1
                    total_processed += 1
                    self.__mt_thread_next_power_on()
                    if self._factory_devices_loader__remaining_device == 0:
                        print('All device process finished, go to finish.')
                        self._factory_devices_loader__uart.send_cmd('FINISH', 0, 0)
                    elif func == 'FINISH':
                        pass
                    elif not no_response_try_times > 0:
                        self._factory_devices_loader__uart.stop()
                        self.owner_notifyer.write(('start_bron', {
                            'total_finish': True,
                            'item': { } }))
                        print('UART control MT finished, total process board: %d.' % total_processed)
                        return None

    
    def __device_mount_get(self, is_mount, timeout = (1,)):
        msg = dll_msg()
        if dll_size(is_mount) > 0:
            dll_get(is_mount, byref(msg))
            return (msg.pid, msg.vid, msg.path, msg.volume)
        if None == 0:
            return None
        timeout = None - 1
        time.sleep(1)
        continue

    
    def start(self, serial_name, slot_list, is_rebron):
        if os.path.exists(env.UP_FILE_SAVED_PATH) is False:
            print('Download file does not exists!')
            self.owner_notifyer.write(('start_bron', {
                'error_code': 1014,
                'error_message': util_func.code_info(),
                'total_finish': True,
                'item': { } }))
            return None
        self._factory_devices_loader__serial_name = None
        if slot_list is not None:
            self._factory_devices_loader__slot_list = slot_list
        else:
            self._factory_devices_loader__slot_list = (lambda .0: [ i for i in .0 ])(range(self.bron_slot_num))
        if self._factory_devices_loader__uart_comm_thread is not None:
            self._factory_devices_loader__uart_comm_thread.join()
        self._factory_devices_loader__uart_comm_thread = threading.Thread(self.__mt_thread, True, **('target', 'daemon'))
        self._factory_devices_loader__uart_comm_thread.start()

    
    def stop(self):
        self._factory_devices_loader__mt_thread_stop_ev.set()

    
    def download(self, index):
        if index >= len(self._factory_devices_loader__devices):
            return False
        None.Thread(self._factory_devices_loader__devices[index].download_only, True, (env.UP_FILE_SAVED_PATH,), **('target', 'daemon', 'args')).start()
        return True

    
    def erase(self, index, sync = (False,)):
        if index >= len(self._factory_devices_loader__devices):
            return False
        if None:
            return self._factory_devices_loader__devices[index].erase_only()
        None.Thread(self._factory_devices_loader__devices[index].erase_only, True, **('target', 'daemon')).start()
        return True

    
    def upload(self, index, bin_file_path):
        if index >= len(self._factory_devices_loader__devices):
            return False
        None.Thread(self._factory_devices_loader__devices[index].upload_only, True, (bin_file_path,), **('target', 'daemon', 'args')).start()
        return True

    
    def finish(self, index):
        if index >= len(self._factory_devices_loader__devices):
            return None
        None._factory_devices_loader__uart.send_cmd('PROCESS_RESULT', index, 0)

    __classcell__ = None

