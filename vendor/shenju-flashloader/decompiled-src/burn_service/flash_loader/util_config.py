# Source Generated with Decompyle++
# File: util_config.pyc (Python 3.10)

import os
import json

class config_json_file:
    _path = ''
    _dict = { }
    
    def __init__(self, file_path, input_dict = (None, None)):
        if file_path is None or input_dict is None:
            return None
        self._path = None
        self._dict = input_dict
        if os.path.exists(self._path):
            with open(self._path, 'r', 'utf-8', **('encoding',)) as f:
                fm = json.load(f)
                if fm.keys() == self._dict.keys() and fm['cfg_version'] == self._dict['cfg_version']:
                    self._dict = fm
                None(None, None, None)
            with None:
                if not None:
                    pass
        self.save()

    
    def get_all(self):
        return self._dict

    
    def _read(self, *attr):
        tmp = self._dict
        for a in attr:
            if not hasattr(tmp, 'get'):
                return None
            if None.get(a) is not None:
                tmp = tmp.get(a)
                continue
            return None
            return tmp

    
    def _modify(self, value, *attr):
        tmp = self._dict
        far = self._dict
        son = self._dict
        for a in attr:
            if not hasattr(tmp, 'get'):
                return None
            if None.get(a) is not None:
                far = tmp
                son = a
                tmp = tmp.get(a)
                continue
            return None
            far[son] = value
            return son

    
    def read(self, *attr):
        pass
    # WARNING: Decompyle incomplete

    
    def modify(self, value, *attr):
        pass
    # WARNING: Decompyle incomplete

    
    def save(self):
        if self._path != '':
            with open(self._path, 'w', 'utf-8', **('encoding',)) as fop:
                json.dump(self._dict, fop, 4, **('indent',))
                None(None, None, None)
                return None
                with None:
                    if not None:
                        pass
            return None


