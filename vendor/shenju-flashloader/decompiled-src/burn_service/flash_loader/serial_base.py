# Source Generated with Decompyle++
# File: serial_base.pyc (Python 3.10)

import serial
import serial.tools.list_ports as serial
import threading
import time
from  import util_notifyer

def try_to_decode_string(str1, encoding = ('utf-8',)):
    pass
# WARNING: Decompyle incomplete


class yqSerialBase(util_notifyer.notifyer):
    __exit = None
    thread = None
    opened = False
    mode = 'text'
    
    def __init__(self = None, notifyer = None, polling_instance = None):
        super().__init__(notifyer)
        self.serial_run_ev = threading.Event()
        self.bin_magic = None
        self.bin_length = None
        self.polling = polling_instance
        self.opened = False

    
    def run(self):
        self.__exit = threading.Event()
    # WARNING: Decompyle incomplete

    
    def cut(self, obj, sec):
        return (lambda .0 = None: [ obj[i:i + sec] for i in .0 ])(range(0, len(obj), sec))

    
    def send(self, sendline):
        if sendline is not None and self.opened is True:
            if self.mode == 'bin':
                self.serial_dev.write(self.bin_magic + sendline)
                return True
            if None.mode == 'text':
                to_send_bytes = bytes('%s\n' % sendline, 'utf-8', **('encoding',))
                for chars in to_send_bytes:
                    self.serial_dev.write(int.to_bytes(chars, 1, 'little', **('byteorder',)))
                    time.sleep(0.01)
            return True

    
    def setConfig(self, pt, br, py, sb, mode, bin_magic, bin_length = ('text', b'\r\n', 16)):
        (self.pt, self.br, self.py, self.sb, self.mode, self.bin_magic, self.bin_length) = (pt, br, py, sb, mode, bin_magic, bin_length)

    
    def start(self):
        self.thread = threading.Thread(self.run, True, **('target', 'daemon'))
        self.thread.start()
        self.serial_run_ev.wait()
        self.serial_run_ev.clear()

    
    def stop(self):
        if self.opened is True:
            if self.__exit is not None:
                self.__exit.set()
            if self.thread is not None:
                self.thread.join()
                return None
            return None

    __classcell__ = None

