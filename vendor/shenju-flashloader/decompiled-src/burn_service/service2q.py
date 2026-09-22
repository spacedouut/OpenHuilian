# Source Generated with Decompyle++
# File: service2q.pyc (Python 3.10)

import threading
from fac_manager import burn_manager as facbm
from dev_manager import burn_manager as decbm
from verno import FLASH_LOADER_PRO_VERSION

class burns2q:
    
    def __init__(self, q_in, q_out, mode = ('fac',)):
        self.putlock = threading.Lock()
        self.exit_ev = threading.Event()
        self.mgr = None
        self.mode = mode
        self.q_in = q_in
        self.q_out = q_out
        if self.mode == 'fac':
            self.mgr = facbm(self._on_send_out, self._on_callback, FLASH_LOADER_PRO_VERSION)
        else:
            self.mgr = decbm(self._on_send_out, self._on_callback, FLASH_LOADER_PRO_VERSION)
        threading.Thread(self._proc, True, **('target', 'daemon')).start()

    
    def _proc(self):
