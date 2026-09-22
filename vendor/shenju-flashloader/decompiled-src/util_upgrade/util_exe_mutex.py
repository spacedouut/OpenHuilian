# Source Generated with Decompyle++
# File: util_exe_mutex.pyc (Python 3.10)

import win32api
import win32event
import winerror

def create(app_name):
    obtain_mutex = 1
    mutex = win32event.CreateMutex(None, obtain_mutex, app_name)
    mutex.Detach()
    lasterror = win32api.GetLastError()
    if lasterror == winerror.ERROR_ALREADY_EXISTS:
        print('Global mutex already created.')
        return False

