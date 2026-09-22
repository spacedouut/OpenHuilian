# Source Generated with Decompyle++
# File: env.pyc (Python 3.10)

import os
import sys
if getattr(sys, 'frozen', False):
    __EXE_PATH__ = os.path.dirname(sys.executable)
    __DEBUG = False
else:
    __EXE_PATH__ = os.getcwd()
    __DEBUG = True
curpath = __EXE_PATH__ + os.sep + 'burn_service' + os.sep + 'flash_loader'
RESTART_BIN_PATH = os.path.join(curpath, 'ram_run_bin', 'reset_6801.bin')
CODEFILE6806_BIN_PATH = os.path.join(curpath, 'ram_run_bin', '6806_codefile.bin')
SL6801_INTEL_FLASH_BIN_PATH = os.path.join(curpath, 'ram_run_bin', '6801_intel_flash.bin')
RF_CHECK_6801_BIN_PATH = os.path.join(curpath, 'ram_run_bin', 'cal_frequent_drift.bin')
RF_CHECK_6806_BIN_PATH = os.path.join(curpath, 'ram_run_bin', 'base_board.bin')
UART_LOADER_6801_BIN_PATH = os.path.join(curpath, 'ram_run_bin', 'cal_frequent_drift_gyro_ur.bin')
UART_LOADER_6806_BIN_PATH = os.path.join(curpath, 'ram_run_bin', 'mp_uart_6806.bin')
MASS_STORAGE_DLL_PATH = os.path.join(curpath, 'MASSSTORAGE.dll')
COM_DLL_PATH = os.path.join(curpath, 'COM.dll')
COM_6806_DLL_PATH = os.path.join(curpath, 'COM_6806.dll')
PSM_NVDS_DLL_PATH = os.path.join(curpath)
PSM_NVDS_DLL_PATH_NAME = os.path.join(curpath, 'psm-nvds.dll')
C_CRC_DLL_PATH_NAME = os.path.join(curpath, 'c_crc.dll')
UP_FILE_SAVED_PATH = os.path.join(__EXE_PATH__, 'download.up')
os.environ['path'] = os.environ['path'] + ';' + __EXE_PATH__
os.environ['path'] = os.environ['path'] + ';' + PSM_NVDS_DLL_PATH
