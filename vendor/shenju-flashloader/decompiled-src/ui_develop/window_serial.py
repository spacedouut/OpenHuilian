# Source Generated with Decompyle++
# File: window_serial.pyc (Python 3.10)

import time
import os
import threading
from burn_service.flash_loader.env import __EXE_PATH__
from ui_develop.ui_main import *
from PyQt6.QtCore import QObject, QSize, Qt
from PyQt6.QtGui import QTextCursor, QIntValidator
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QListWidgetItem, QWidget, QLineEdit, QPushButton, QHBoxLayout, QMessageBox
from util_ui.widget_right_menu import RMenu
from util_ui.text_color import Colored
from burn_client2q import bc
from verno import software_upgrade_text
HISTROY_FILE_PATH = os.path.join(__EXE_PATH__, 'histroy_cmd.txt')
MAX_HISTROY_NUM = 50
MAX_LINES = 500000

def QStringToString(q_string):
    ret = ''
# WARNING: Decompyle incomplete


def get_time_string():
    ct = time.time()
    local_time = time.localtime(ct)
    data_head = time.strftime('%H:%M:%S', local_time)
    data_secs = (ct - int(ct)) * 1000
    time_stamp_color = "<font color=BLUE size='4'>[%s.%03d]</font>" % (data_head, data_secs)
    time_stamp = '[%s.%03d]' % (data_head, data_secs)
    return (time_stamp, time_stamp_color)


class CustomLineEdit(QLineEdit):
    
    def __init__(self = None, parent = None):
        super().__init__(parent)

    
    def keyPressEvent(self = None, event = None):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self.parent().wrap_func(None)
            return None
        None().keyPressEvent(event)

    __classcell__ = None


class CmdItemWidget(QWidget):
    BUTTON_STYLE = 'QPushButton{color:blue;}QPushButton:enabled{background:rgb(56, 148, 148);color:white;}QPushButton:!enabled{background:rgb(180, 180, 180);color:white;}QPushButton:enabled:hover{background:rgb(2, 65, 132);}QPushButton:enabled:pressed{background:rgb(6, 94, 187);}'
    SUCCESS_STYLE = 'QProgressBar {border: 2px solid grey;border-radius: 5px;text-align: center;}QProgressBar::chunk {background-color: #00FF00;width: 20px;}'
    ERROR_STYLE = 'QProgressBar {border: 2px solid grey;border-radius: 5px;text-align: center;}QProgressBar::chunk {background-color: #FF0000;width: 20px;}'
    CMD_STYLE = 'QLineEdit {border: 1px solid #A0A0A0; border-radius: 3px; padding-left: 5px; background-color: #F2F2F2; color: #000000; selection-background-color: #A0A0A0; selection-color: #F2F2F2;font-family: "Microsoft YaHei";font-size: 10pt;}'
    
    def __init__(self = None, parent = None, send_func = None, txt = None, *args, **kwargs):
        pass
    # WARNING: Decompyle incomplete

    
    def wrap_func(self, st):
        if self.send_btn.isEnabled():
            self.send_func(self.line.text())
            return None

    
    def enable(self, flag):
        self.send_btn.setEnabled(flag)

    __classcell__ = None


class win_serial(RMenu, QObject):
    SignalWin = QtCore.pyqtSignal(dict)
    
    def __init__(self = None, win = None, ui = None):
        super().__init__()
        self.com_desc = ''
        self.cmditems = []
        self.ui = ui
        self.win = win
        self.opened = False
        self.auto_save_log = None
        int_validator = QIntValidator(1, 100000, self)
        self.ui.lineEdit_auto_sec.setValidator(int_validator)
        self.auto_send_timer = None
        self.auto_send_timer_stop = True
        self.serial_txt_lines = 0
        self.ui.lineEdit_cmd.setStyleSheet(CmdItemWidget.CMD_STYLE)
        self.ui.ui_open_com.clicked.connect(self.UI_Com_connect)
        self.ui.ui_pushbtn_send.clicked.connect(self.UI_Send)
        self.ui.checkBox_auto_send.clicked.connect(self.UI_check_auto_send)
        self.doCmdHistory('load')
        self.UI_Com_connected(False)
        self.SignalWin.connect(self.update_data)
        bc.do_register((self, [
            'com_polling',
            'get_config',
            'start_serial']))
        bc.do_send({
            'request': 'com_polling' })
        bc.do_send({
            'request': 'get_config' })
        self.ui.ui_combox_bron_select.setToolTip('右击打开文件位置')
        self.ui.ui_combox_bron_select.setContextMenuPolicy(Qt.Cont