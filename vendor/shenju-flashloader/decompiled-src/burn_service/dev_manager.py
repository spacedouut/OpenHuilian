# Source Generated with Decompyle++
# File: dev_manager.pyc (Python 3.10)

import threading
import queue
import json
import copy
import time
import tkinter
import tkinter.filedialog as tkinter
from urllib import parse as url_parser
from flash_loader.env import __EXE_PATH__
from flash_loader import util_func, util_notifyer
from flash_loader import loader_engineer_usb
from flash_loader import flash_base
from flash_loader import serial_base, polling_base
from flash_loader import up_parser
from dev_config import dev_config as conf
from dev_protocol import *
from  import dev_protocol

def get_time_stamp():
    ct = time.time()
    local_time = time.localtime(ct)
    data_head = time.strftime('%H:%M:%S', local_time)
    data_secs = (ct - int(ct)) * 1000
    time_stamp = '[%s.%03d]: ' % (data_head, data_secs)
    return time_stamp


def new_slot_items():
    tss = []
    for i in range(conf.read('bron_slot', 'current')):
        new_item = copy.deepcopy(ITEM)
        new_item['index'] = i
        tss.append(new_item)
    return tss


class burn_manager:
    
    def __init__(self, send_out_func, callback_func, version):
        self.version = version
        self.q = queue.Queue()
        self.notifier = util_notifyer.data_notifyer()
        self.notifier.register_writer([
            'com_polling',
            'slot_polling',
            'start_bron',
            'start_serial',
            'start_bron_update'], self.__notify)
        self.controls = {
            'controls': [] }
        self.slot = { }
        self.items = new_slot_items()
        self.loader = loader_engineer_usb.engineer_devices_loader(self.notifier, conf)
        self.serial = serial_base.yqSerialBase(self.notifier, polling_base.yqSerialPoll(self.notifier), **('polling_instance',))
        self.send_out_func = send_out_func
        self.callback_func = callback_func
        threading.Thread(self.__proc, True, **('target', 'daemon')).start()

    
    def __notify(self, protocol):
        self.q.put(protocol)

    
    def __proc(self):
        (protocol_type, protocol_payload) = self.q.get()
        if protocol_type == 'start_bron_update':
            if 'error_code' in protocol_payload.keys():
                print(get_time_stamp(), protocol_type, json.dumps(protocol_payload))
            index = protocol_payload['index']
            for item in self.items:
                if item['index'] == index:
                    item.update(protocol_payload)
                    res_d = copy.deepcopy(START_BRON)
                    res_d['payload']['item'] = item
                    self.__report_func(res_d)
                
                if protocol_type == 'com_polling':
                    self.controls = protocol_payload
                    template = COM_POLLING
                elif protocol_type == 'slot_polling':
                    self.slot = protocol_payload
                    template = SLOT_POLLING
                elif protocol_type == 'start_bron':
                    template = START_BRON
                elif protocol_type == 'start_serial':
                    template = START_SERIAL
                
                res_d = copy.deepcopy(template)
                res_d['payload'].update(protocol_payload)
                self.__report_func(res_d)

    
    def request(self, msg):
        pass
    # WARNING: Decompyle incomplete

    
    def __report_func(self, json_body):
        to_send = json.dumps(json_body)
        self.send_out_func(to_send.encode('utf-8').decode())


