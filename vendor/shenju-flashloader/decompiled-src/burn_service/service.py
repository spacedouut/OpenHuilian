# Source Generated with Decompyle++
# File: service.pyc (Python 3.10)

import time
import threading
from websocket_server import WebsocketServer
from fac_manager import burn_manager as facbm
from dev_manager import burn_manager as decbm
from verno import FLASH_LOADER_PRO_VERSION

class burns:
    
    def __init__(self, port, mode, gui = (5005, 'fac', None)):
        self.exit_ev = threading.Event()
        self.exit_delay_ev = threading.Event()
        self.client_lock = threading.Lock()
        self.client = None
        self.mgr = None
        self.port = port
        self.mode = mode
        self.gui = gui
        threading.Thread(self._proc_monitor, True, **('target', 'daemon')).start()
        threading.Thread(self._proc, True, **('target', 'daemon')).start()

    
    def _proc(self):
        self.server = WebsocketServer(self.port, **('port',))
        self.server.set_fn_new_client(self._new_client)
        self.server.set_fn_message_received(self._on_received)
        self.server.set_fn_client_left(self._new_left)
        if self.mode == 'fac':
            self.mgr = facbm(self._on_send_out, self._on_callback, FLASH_LOADER_PRO_VERSION)
        else:
            self.mgr = decbm(self._on_send_out, self._on_callback, FLASH_LOADER_PRO_VERSION)
        self.server.run_forever()

    
    def _proc_monitor(self):
