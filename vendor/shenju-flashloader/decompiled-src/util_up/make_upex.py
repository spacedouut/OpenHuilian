# Source Generated with Decompyle++
# File: make_upex.pyc (Python 3.10)

__author__ = 'yangyang'
import tarfile
from make_uti import *

class upex_file:
    
    def __init__(self, _path):
        self.org_upex_path = _path
        self.tmp_dir = None

    
    def extract(self, _path):
        with tarfile.open(self.org_upex_path) as tar:
            tar.extractall(_path, **('path',))
            None(None, None, None)
        with None:
            if not None:
                pass
        self.tmp_dir = _path

    
    def generate(self, upex_file_path):
        if self.tmp_dir is not None:
            with tarfile.open(upex_file_path, 'w', tarfile.PAX_FORMAT, **('format',)) as tar:
                for root, dirs, files in os.walk(self.tmp_dir):
                    for file in files:
                        full_path = os.path.join(root, file)
                        relative_path = os.path.relpath(full_path, self.tmp_dir)
                        tar.add(full_path, relative_path, **('arcname',))
                for dir in dirs:
                    full_path = os.path.join(root, dir)
                    relative_path = os.path.relpath(full_path, self.tmp_dir)
                    tar.add(full_path, relative_path, **('arcname',))
                None(None, None, None)
                return True
                with None:
                    if not None:
                        pass
            return True
        return False


