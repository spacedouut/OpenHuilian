# Source Generated with Decompyle++
# File: util_notifyer.pyc (Python 3.10)

import threading

class data_notifyer:
    
    def __init__(self):
        self.writers = []
        self.lock = threading.Lock()

    
    def __append_writer(self, protocol_type, method):
        for writer in self.writers:
            (in_writer_protocol_type, in_writer_method) = writer
            if in_writer_protocol_type == protocol_type:
                self.writers.remove(writer)
            
            self.writers.append((protocol_type, method))
            return None

    
    def write(self, protocol):
        (protocol_type, protocol_payload) = protocol
        for writer in self.writers:
            (in_writer_protocol_type, in_writer_method) = writer
            if in_writer_protocol_type == protocol_type:
                in_writer_method(protocol)

    
    def register_writer(self, protocol_type, method):
        if method is not None:
            with self.lock:
                if type(protocol_type) == str:
                    self.__append_writer(protocol_type, method)
                elif type(protocol_type) == list:
                    for pt in protocol_type:
                        self.__append_writer(pt, method)
                None(None, None, None)
                return None
                None(None, None, None)
                return None
                None(None, None, None)
                return None
                with None:
                    if not None:
                        pass
            return None



class notifyer:
    
    def __init__(self, owner_notifyer):
        self.owner_notifyer = owner_notifyer


