# Source Generated with Decompyle++
# File: serial_stm32.pyc (Python 3.10)

import queue
import time
import struct
import json
from util_notifyer import data_notifyer
from  import serial_base, polling_stm32
UART_MSG_TYPE = {
    'CMD': 0,
    'RESP': 1,
    'IND': 2 }
UART_MSG_FUNC = {
    'READY': 255,
    'FINISH': 254,
    'REQUEST_POWERON': 3,
    'REQUEST_POWEROFF': 4,
    'PROCESS_RESULT': 18,
    'PARDON': 249 }
UART_RECV_TIME_OUT = 2
UART_SEND_TIME_OUT = 2

def bytes4_to_int(bytes4):
    result = 0
    for b in reversed(bytes4):
        result = result * 256 + int(b)
    return result


def crc_32(pbuf, size):
    st_const_value = 79764919
    crc_value = 0xFFFFFFFF
    for i in range(size):
        int_pbuf_item = bytes4_to_int(pbuf[i * 4:i * 4 + 4])
        xbit = 0x80000000
        for bits in range(32):
            if crc_value & 0x80000000 != 0:
                crc_value <<= 1
                crc_value = crc_value & 0xFFFFFFFF
                crc_value ^= st_const_value
            else:
                crc_value <<= 1
                crc_value = crc_value & 0xFFFFFFFF
            if int_pbuf_item & xbit != 0:
                crc_value ^= st_const_value
            xbit >>= 1
            xbit = xbit & 0xFFFFFFFF
    return crc_value


class uart_stm32:
    
    def __init__(self, owner_notifyer):
        self.notifyer = data_notifyer()
        self.notifyer.register_writer([
            'start_serial'], self.__recv)
        self.mySerial = serial_base.yqSerialBase(self.notifyer, polling_stm32.yqSerialUartPoll(owner_notifyer))
        self.queue_uart_recv = queue.Queue()
        self.queue_uart_send = queue.Queue()
        self.right_now_command = None

    
    def __recv(self, protocol):
        (protocol_type, protocol_payload) = protocol
        if 'com_data' in protocol_payload.keys():
            d = protocol_payload['com_data']
            self.queue_uart_recv.put(d)
            return None

    
    def encode_command(self, type, func, payload0, payload1):
        crc = crc_32(struct.pack('IBBBBII', 0, type, func, payload0, payload1, 0, 0), 4)
        return struct.pack('IBBBBII', crc, type, func, payload0, payload1, 0, 0)

    
    def decode_command(self, body):
        
        try:
            pass
        finally:
            return None
            return (0, 0, 0, 0, 0, 0, 0)


    
    def get_func_name(self, func):
        func_name = ''
        for key, value in UART_MSG_FUNC.items():
            if value == func:
                func_name = key
                return func_name
            return func_name

    
    def get_type_name(self, type):
        type_name = ''
        for key, value in UART_MSG_TYPE.items():
            if value == type:
                type_name = key
                return type_name
            return type_name

    
    def print_command(self, is_send, body, with_hex = (False,)):
        pass

    
    def uart_one_command_do(self):
        
        try:
            data = self.queue_uart_send.get(UART_SEND_TIME_OUT, **('timeout',)) if self.right_now_command is None else self.right_now_command
            self.print_command(True, data)
            self.last_send = data
            send_result = self.mySerial.send(data)
            self.right_now_command = None
            if send_result is False:
                pass
        finally:
            return False
        send_result = False
        if send_result:
            recv_time = time.time()
            
            try:
                ev = self.queue_uart_recv.get(UART_RECV_TIME_OUT, **('timeout',))
                self.print_command(False, ev, True, **('with_hex',))
                (crc, type, func, payload0, payload1, pri, bodylen) = self.decode_command(ev)
                crc_mycalc = crc_32(struct.pack('IBBBBII', 0, type, func, payload0, payload1, 0, 0), 4)
                if crc != crc_mycalc:
                    print('crc check diff! from UART: 0x%x, my calc: 0x%x pardon !!!' % (crc, crc_mycalc))
                    self.right_now_command = self.encode_command(UART_MSG_TYPE['RESP'], UART_MSG_FUNC['PARDON'], 0, 0)
                elif type == UART_MSG_TYPE['RESP'] and func == UART_MSG_FUNC['PARDON']:
                    self.queue_uart_send.put(self.last_send)
            finally:
                return None
                return False
                return True



    
    def start(self, serial_name):
