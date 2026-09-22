# Source Generated with Decompyle++
# File: polling_base.pyc (Python 3.10)

import serial
import serial.tools.list_ports as serial
import threading
import time
from  import util_notifyer

class yqSerialPoll(util_notifyer.notifyer):
    
    def __init__(self = None, owner_notifyer = None):
        super().__init__(owner_notifyer)
        self.device = []
        self.description = []
        self.coms = None
        self._check_coms()
        threading.Thread(self.loop_check_coms, True, **('target', 'daemon')).start()

    
    def _check_coms(self):
        plist = list(serial.tools.list_ports.comports())
        plist = (lambda .0: [ port for port in .0 if '蓝牙链接上的标准串行' not in port.description ])(plist)
        self.description.clear()
        self.device.clear()
        for item in plist:
            self.description.append(item.description)
            self.device.append(item.device)
        old_coms = self.coms
        self.coms = dict(zip(self.description, self.device))
        if old_coms != self.coms:
            self.owner_notifyer.write(('com_polling', {
                'controls': self.coms }))
            print('polling and update control coms:%d' % len(self.coms))
            return None

    
    def loop_check_coms(self):
        time.sleep(1)
        self._check_coms()
        continue

    __classcell__ = None

