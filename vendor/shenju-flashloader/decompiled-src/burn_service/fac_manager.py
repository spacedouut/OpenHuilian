# Source Generated with Decompyle++
# File: fac_manager.pyc (Python 3.10)

import threading
import queue
import json
import copy
import time
import urllib.request as urllib
from urllib import parse as url_parser
from flash_loader import env
from flash_loader import util_func, loader_factory_uart, util_notifyer, up_parser
from fac_config import fac_config as conf
from fac_protocol import *
from  import fac_protocol

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
            'start_bron_update'], self.__notify)
        self.controls = {
            'controls': [] }
        self.slots = {
            'slots': [] }
        self.items = new_slot_items()
        self.loader = loader_factory_uart.factory_devices_loader(self.notifier, conf)
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
                
                print(get_time_stamp(), protocol_type, json.dumps(protocol_payload))
                if protocol_type == 'com_polling':
                    self.controls = protocol_payload
                    template = COM_POLLING
                elif protocol_type == 'slot_polling':
                    self.slots = protocol_payload
                    template = SLOT_POLLING
                elif protocol_type == 'start_bron':
                    template = START_BRON
                
                res_d = copy.deepcopy(template)
                res_d['payload'].update(protocol_payload)
                self.__report_func(res_d)

    
    def request(self, msg):
        print(get_time_stamp(), msg)
    # WARNING: Decompyle incomplete

    
    def __report_func(self, json_body):
        to_send = json.dumps(json_body)
        self.send_out_func(to_send.encode('utf-8').decode())


