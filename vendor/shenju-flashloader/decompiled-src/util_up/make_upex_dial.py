# Source Generated with Decompyle++
# File: make_upex_dial.pyc (Python 3.10)

__author__ = 'yangyang'
import tarfile
from make_uti import *

class dial_file:
    
    def __init__(self, _path):
        self.path = _path

    
    def get_thumbnail_jpg(self):
        with open(self.path, 'rb') as f:
            f.seek(48)
            offset = int.from_bytes(f.read(4), 'little')
            f.seek(offset + 2)
            offset_jpg = int.from_bytes(f.read(4), 'little')
            length_jpg = int.from_bytes(f.read(4), 'little')
            f.seek(offset_jpg)
            None(None, None, None)
            return f.read(length_jpg)
            with None:
                if not None:
                    pass


