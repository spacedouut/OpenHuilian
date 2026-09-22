# Source Generated with Decompyle++
# File: burn_client2q.pyc (Python 3.10)

import threading
import queue
import json
from burn_service import service2q

class burn_client2q:
    
    def __init__(self):
        self.putlock = threading.Lock()
        self.for_service_q_in = queue.Queue()
        self.for_service_q_out = queue.Queue()
        self.signals = []
        self.sev = service2q.burns2q(self.for_service_q_in, self.for_service_q_out, 'dev', **('mode',))
        threading.Thread(self._start, True, **('target', 'daemon')).start()

    
    def _start(self):
        msg = self.for_service_q_out.get()
        d = json.loads(msg)
        d_res = d.get('response')
        for sig in self.signals:
            (s, protocol_list) = sig
            if d_res in protocol_list:
                s.SignalWin.emit(d)
        continue

    
    def do_send(self, msg):
        with self.putlock:
            self.for_service_q_in.put(json.dumps(msg))
            None(None, None, None)
            return None
            with None:
                if not None:
                    pass

    
    def do_register(self, sig):
        with self.putlock:
            self.signals.append(sig)
            None(None, None, None)
            return None
            with None:
                if not None:
                    pass

    
    def do_unregister(self, signal):
        for sig in self.signals:
            (s, protocol_list) = sig
            if id(signal) == id(s):
                self.signals.remove(sig)
                return None
            return None


bc = burn_client2q()
