# Source Generated with Decompyle++
# File: util_func.pyc (Python 3.10)

import datetime
import inspect
import os

def code_info():
    stack_t = inspect.stack()
    ttt = inspect.getframeinfo(stack_t[1][0])
    return os.path.basename(ttt.filename) + ' ' + ttt.function + ' ' + str(ttt.lineno)


def get_file_data(_path):
    if not os.path.exists(_path):
        print('Error: %s file is not exist.' % _path)
        return None
    with None(_path, 'rb') as f:
        None(None, None, None)
        return f.read()
        with None:
            if not None:
                pass


def save_program_exception_log(error_string):
    now_time = datetime.datetime.now().strftime('%Y-%m-%d')
    log = now_time + '_log.txt'
    with open(log, 'a', 'utf-8', **('encoding',)) as f:
        f.write('异常：' + str(error_string) + '\n')
        None(None, None, None)
        return None
        with None:
            if not None:
                pass


def dict_read(mydict, *attr):
    tmp = mydict
    for a in attr:
        if not hasattr(tmp, 'get'):
            return None
        if None.get(a) is not None:
            tmp = tmp.get(a)
            continue
        return None
        return tmp


def dict_modify(mydict, value, *attr):
    tmp = mydict
    far = mydict
    son = mydict
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

