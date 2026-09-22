# Source Generated with Decompyle++
# File: loader_factory_uart.pyc (Python 3.10)

import copy
import threading
import time
import os
from  import env
from  import flash_uart_6801 as flash_uart
from loader_factory import factory_loader
from serial_stm32 import uart_stm32
from  import util_func
DEVICE_ON_TIME_OUT = 15
DEVICE_NO_RESPONSE_TIME = 3600

class factory_devices_loader(factory_loader):
    
    def __init__(self = None, owner_notifyer = None, this_config = None):
        super().__init__(owner_notifyer)
        self.this_config = this_config
        self.valid_slot_list = []
        self.coms_map_list = [
            (0, 0)] * 32
        self._factory_devices_loader__mt_thread_running_ev = threading.Event()
        self._factory_devices_loader__mt_thread_stop_ev = threading.Event()
        self.owner_notifyer.register_writer([
            'bron_com_polling'], self.__update_born_coms_map)
        self._factory_devices_loader__uart = uart_stm32(self.owner_notifyer)
        self._factory_devices_loader__devices = []
        self.__devices_clear()

    
    def __devices_clear(self):
        self._factory_devices_loader__power_on_index = -1
        self._factory_devices_loader__remaining_device = []
        self._factory_devices_loader__sync_device = []

    
    def __update_born_coms_map(self, protocol):
        
        def _factory_devices_loader__add_com_to_map_list(name = None, serial_number = None):
            pos = serial_number.find('SL')
            if pos != 0 or len(serial_number) != 7:
                print('FT serial number error! pos:%d len：%d' % (pos, len(serial_number)))
                return False
            bank = None(serial_number[pos + 2:pos + 6])
            if bank < 0 or bank > 7:
                print('FT serial number error! bank:%d' % bank)
                return False
            suffix = None(serial_number[pos + 6:]) - ord('A')
            if suffix < 0 or suffix > 3:
                print('FT serial number error! suffix:%d' % suffix)
                return False
            index = None * 4 + suffix
            com_num = int(name[3:])
            (used, c111) = self.coms_map_list[index]
            if used == 0:
                print('index:%d com_num:%d' % (index, com_num))
                self.coms_map_list[index] = (1, com_num)
            return True

        (protocol, d_born_coms) = protocol
        self.coms_map_list = [
            (0, 0)] * 32
        for key, value in d_born_coms.items():
            _factory_devices_loader__add_com_to_map_list(key, value)
        self.valid_slot_list = []
        for u, c222 in enumerate(self.coms_map_list):
            if i < int(self.this_config.read('bron_slot', 'current')) and u == 1:
                self.valid_slot_list.append(i)
        self.owner_notifyer.write(('slot_polling', {
            'slots': self.valid_slot_list }))

    
    def __mt_thread(self, serial_name, slot_list, is_rebron):
        
        def _factory_devices_loader__total_finish():
            self.owner_notifyer.write(('start_bron', {
                'total_finish': True,
                'item': { } }))
            print('UART control MT finished')
            self._factory_devices_loader__mt_thread_running_ev.clear()

        
        def _factory_devices_loader__mt_thread_next_power_on():
            if self._factory_devices_loader__power_on_index >= len(slot_list) - 1:
                return False
            None._factory_devices_loader__power_on_index += 1
            self._factory_devices_loader__uart.send_cmd('REQUEST_POWERON', slot_list[self._factory_devices_loader__power_on_index], 0)
            return True

        slot_list = (lambda .0 = None: [ val for val in .0 if val in self.valid_slot_list ])(slot_list)
        if len(slot_list) == 0:
            _factory_devices_loader__total_finish()
            return None
        None._factory_devices_loader__mt_thread_running_ev.set()
        self._factory_devices_loader__mt_thread_stop_ev.clear()
        self.__devices_clear()
        if is_rebron is False:
            self._factory_devices_loader__devices = []
            for i in range(int(self.this_config.read('bron_slot', 'current'))):
                if self.coms_map_list[i][0]:
                    dev = flash_uart.flash_uart(self.owner_notifyer, self.this_config, i, self.coms_map_list[i][1], env.UP_FILE_SAVED_PATH)
                    self._factory_devices_loader__devices.append(dev)
                    continue
                self._factory_devices_loader__devices.append(None)
        else:
            for dev in self._factory_devices_loader__devices:
                if dev is not None:
                    dev.reinit()
        if len(self._factory_devices_loader__devices) == 0:
            _factory_devices_loader__total_finish()
            return None
        None._factory_devices_loader__uart.start(serial_name)
        self._factory_devices_loader__uart.send_cmd('READY', 0, 0)
        self._factory_devices_loader__remaining_device = copy.deepcopy(slot_list)
        no_response_try_times = DEVICE_NO_RESPONSE_TIME
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
                no_response_try_times = DEVICE_NO_RESPONSE_TIME
                (func, payload0, payload1, recv_time) = ev
                if func == 'READY':
                    print('received CMD READY, this is the first time request power on.')
                    time.sleep(0.5)
                    _factory_devices_loader__mt_thread_next_power_on()
                elif func == 'REQUEST_POWERON':
                    self.t1 = time.time()
                    ret = self._factory_devices_loader__devices[payload0].sync_boot()
                    self.t2 = time.time()
                    print('==========================================')
                    print('index %d delay0 %f delay1 %f' % (payload0, self.t1 - recv_time, self.t2 - recv_time))
                    if ret is True:
                        self._factory_devices_loader__devices[payload0].set_attrib('', '', '', '', True)
                        self._factory_devices_loader__sync_device.append(payload0)
                        self.owner_notifyer.write(('start_bron_update', {
                            'index': payload0,
                            'error_code': 0,
                            'error_message': util_func.code_info(),
                            'power': True }))
                    else:
                        self._factory_devices_loader__uart.send_cmd('REQUEST_POWEROFF', payload0, 0)
                        print('Can not sync board%d, then power on next.' % payload0)
                        self.owner_notifyer.write(('start_bron_update', {
                            'index': payload0,
                            'is_finish': True,
                            'is_success': False,
                            'error_code': 1012,
                            'error_message': util_func.code_info(),
                            'power': False }))
                    if _factory_devices_loader__mt_thread_next_power_on() is False:
                        for item in self._factory_devices_loader__sync_device:
                            self.download(item)
                    elif func == 'PROCESS_RESULT':
                        if payload0 in self._factory_devices_loader__remaining_device:
                            self._factory_devices_loader__remaining_device.remove(payload0)
                        if len(self._factory_devices_loader__remaining_device) == 0:
                            print('All device process finished, go to finish.')
                            self._factory_devices_loader__uart.send_cmd('FINISH', 0, 0)
                        elif func == 'FINISH':
                            pass
                        elif not no_response_try_times > 0:
                            self._factory_devices_loader__uart.stop()
                            _factory_devices_loader__total_finish()
                            return None

    
    def start(self, serial_name, slot_list, is_rebron):
        if self._factory_devices_loader__mt_thread_running_ev.is_set():
            print('burn threading is running!')
            return None
        if None(slot_list) != list or len(slot_list) == 0:
            print('input parameter slot_list is wrong!')
            return None
        if None.path.exists(env.UP_FILE_SAVED_PATH) is False:
            print('Download file does not exists!')
            self.owner_notifyer.write(('start_bron', {
                'error_code': 1014,
                'error_message': util_func.code_info(),
                'total_finish': True,
                'item': { } }))
            return None
        None.Thread(self.__mt_thread, (serial_name, slot_list, is_rebron), True, **('target', 'args', 'daemon')).start()

    
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

