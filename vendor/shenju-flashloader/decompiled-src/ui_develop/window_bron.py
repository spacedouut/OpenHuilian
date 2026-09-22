# Source Generated with Decompyle++
# File: window_bron.pyc (Python 3.10)

import os
import threading
import time
import datetime
from burn_service.flash_loader.env import __EXE_PATH__
from ui_develop.ui_main import *
from PyQt6.QtCore import QSize, QObject, Qt, QEvent
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QHBoxLayout, QWidget, QMainWindow, QFileDialog, QListWidgetItem, QProgressBar, QPushButton, QLabel
from util_ui.combox_histroy import ComboxHistory
from burn_client2q import bc
HISTROY_BURN_PATH = os.path.join(__EXE_PATH__, 'histroy_burn.txt')

class mass_item_widget(QWidget):
    BUTTON_STYLE = 'QPushButton{color:blue;}QPushButton:enabled{background:rgb(56, 148, 148);color:white;}QPushButton:!enabled{background:rgb(180, 180, 180);color:white;}QPushButton:enabled:hover{background:rgb(2, 65, 132);}QPushButton:enabled:pressed{background:rgb(6, 94, 187);}'
    SUCCESS_STYLE = 'QProgressBar {border: 2px solid grey;border-radius: 5px;text-align: center;}QProgressBar::chunk {background-color: #00FF00;width: 20px;}'
    ERROR_STYLE = 'QProgressBar {border: 2px solid grey;border-radius: 5px;text-align: center;}QProgressBar::chunk {background-color: #FF0000;width: 20px;}'
    clicked_func = None
    
    def __init__(self, parent, bron_func, read_func, volume = (None, None, ''), *args, **kwargs):
        QWidget.__init__(self, parent, **('parent',))
        self.bron_func = bron_func
        self.read_func = read_func
        self.volume = volume
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.item = QListWidgetItem()
        self.item.setSizeHint(QSize(300, 30))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        self.no = QLabel(volume)
        self.no.setFixedSize(24, 30)
        font = QFont()
        font.setBold(True)
        font.setPointSize(20)
        self.no.setFont(font)
        self.no.setStyleSheet('color: blue;')
        layout.addWidget(self.no)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setMinimumSize(QSize(60, 24))
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(mass_item_widget.SUCCESS_STYLE)
        self.bron_button = QPushButton('Burn')
        self.bron_button.setStyleSheet(mass_item_widget.BUTTON_STYLE)
        self.bron_button.clicked.connect(self.wrap_bron_func)
        layout.addWidget(self.bron_button)
        layout.addWidget(self.progress_bar)
        self.read_button = QPushButton('Read')
        if self._dev_access_rights():
            self.read_button.setStyleSheet(mass_item_widget.BUTTON_STYLE)
            self.read_button.clicked.connect(self.wrap_read_func)
            layout.addWidget(self.read_button)
            return None

    
    def _dev_access_rights(self):
        if os.path.exists(__EXE_PATH__ + os.sep + '_dev_access_.txt'):
            return True

    
    def _burn_read_button_enable(self, enable):
        self.bron_button.setEnabled(enable)
        self.read_button.setEnabled(enable)

    
    def wrap_bron_func(self, st):
        self._burn_read_button_enable(False)
        self.bron_func(self)

    
    def wrap_read_func(self, st):
        self._burn_read_button_enable(False)
        self.read_func(self)

    
    def set_error_style(self):
        self.progress_bar.setStyleSheet(mass_item_widget.ERROR_STYLE)
        self._burn_read_button_enable(True)

    
    def set_success_style(self):
        self.progress_bar.setStyleSheet(mass_item_widget.SUCCESS_STYLE)
        if self.progress_bar.value() == 100:
            self._burn_read_button_enable(True)
            return None
        if None.progress_bar.value() > 0:
            self._burn_read_button_enable(False)
            return None



class QEventHandler(QObject):
    
    def eventFilter(self = None, obj = None, event = None):
        '''
        处理窗体内出现的事件，如果有需要则自行添加if判断语句；
        目前已经实现将拖到控件上文件的路径设置为控件的显示文本；
        '''
        if event.type() == QEvent.Type.DragEnter:
            event.acceptProposedAction()
        elif event.type() == QEvent.Type.Drop:
            md = event.mimeData()
            if md.hasUrls():
                url = md.urls()[0]
                obj.setText(url.toLocalFile())
                return True
            return None().eventFilter(obj, event)

    __classcell__ = None


class FileWatcher(threading.Thread):
    
    def __init__(self, _get_url, _sig):
        threading.Thread.__init__(self, True, **('daemon',))
        self._get_url = _get_url
        self.last_modified = None
        self.current_modified = None
        self.running = False
        self._sig = _sig

    
    def run(self):
