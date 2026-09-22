# Source Generated with Decompyle++
# File: polling_stm32.pyc (Python 3.10)

import time
import serial
from polling_base import yqSerialPoll

class yqSerialUartPoll(yqSerialPoll):
    born_coms = []
    name = []
    serial_number = []
    
    def _check_coms(self):
        plist = list(serial.tools.list_ports.comports())
        self.description.clear()
        self.device.clear()
        self.name.clear()
        self.serial_number.clear()
        for item in plist:
            if (item.vid == 1027) & (item.pid == 24593):
                self.name.append(item.name)
                self.serial_number.append(item.serial_number)
                continue
            if '通信端口' in item.description and item.device == 'COM1':
                continue
            self.description.append(item.description)
            self.device.append(item.device)
        old_coms = self.coms
        self.coms = dict(zip(self.description, self.device))
        if old_coms != self.coms:
            self.owner_notifyer.write(('com_polling', {
                'controls': self.coms }))
            print('polling and update control coms:%d' % len(self.coms))
        old_born_coms = self.born_coms
        self.born_coms = dict(zip(self.name, self.serial_number))
        if old_born_coms != self.born_coms:
            self.owner_notifyer.write(('bron_com_polling', self.born_coms))
            print('polling and update burn coms:%d' % len(self.born_coms))
            return None

    
    def loop_check_coms(self):
        time.sleep(1)
        self._check_coms()
        continue


