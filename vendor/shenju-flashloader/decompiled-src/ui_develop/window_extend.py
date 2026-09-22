# Source Generated with Decompyle++
# File: window_extend.pyc (Python 3.10)

import ctypes
import threading
import os
from ui_develop.ui_main import *
from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QFileDialog, QMainWindow, QTreeView, QSplitter, QVBoxLayout, QWidget, QLabel, QWidgetAction, QMenu, QHBoxLayout
from PyQt6.QtGui import QFileSystemModel, QStandardItemModel, QStandardItem, QPixmap, QFont
from PyQt6.QtCore import QDir, Qt, QSize
from functools import partial
from ui_develop.ui_add_psm import *
from ui_develop.window_param import win_param
from util_up.make_uti import *
from util_up.make_upex import upex_file
from util_up.make_upex_dial import dial_file
from util_up.make_up import up_file
from util_ui.widget_right_menu import RightMenu
from util_ui.msg_box import AutoCloseDialog
from burn_service.flash_loader.env import __EXE_PATH__

class upTreeView(QTreeView):
    SignalWin = QtCore.pyqtSignal(str)
    
    class PartitionModel(QStandardItemModel):
        
        def __init__(self = None, data = None):
            super().__init__()
            self.setHorizontalHeaderLabels([
                'Partition',
                'Offset',
                'Length',
                'Capacity(n*4KB)',
                'Comments'])
            self.setupModelData(data)

        
        def setupModelData(self, data):
            for partition, offset, Length, capacity in data:
                offset_hex = format_hex(offset)
                tail_hex = format_hex(Length)
                capacity_hex = format_hex(capacity)
                if partition == 'PSMP':
                    tip = '系统信息存储在Flash的变量(可右键点击修改)'
                elif partition == 'WELC':
                    tip = ' jpg开机图像(可右键点击修改)'
                elif partition == 'PICS':
                    tip = '皮肤资源(可右键点击修改)'
                else:
                    tip = ''
                row = [
                    QStandardItem(partition),
                    QStandardItem(offset_hex),
                    QStandardItem(tail_hex),
                    QStandardItem(capacity_hex),
                    QStandardItem(tip)]
                for item in row:
                    item.setFlags(item.flags() & ~(Qt.ItemFlag.ItemIsEditable))
                self.appendRow(row)

        __classcell__ = None

    
    def __init__(self = None, parent = None, cb = None, _dir = None):
        super(upTreeView, self).__init__(parent)
        self._dir = _dir
        self.cb = cb
        self.SignalWin.connect(self.cb)
        self.contextMenu = None
        self._file = None
        self.up = None
        self.up_parts = None
        empty_model = QStandardItemModel()
        self.setModel(empty_model)
        self.setEnabled(False)

    
    def update_data(self = None, _up = None):
        self._file = self._dir + os.sep + os.path.basename(_up)
        if _up != self._file:
            shutil.copy(_up, self._file)
        if self._file is None:
            self.setEnabled(False)
        else:
            self.setEnabled(True)
            self.up = up_file(self._file)
            self.up_parts = []
            for k, v in self.up.parts.items():
                self.up_parts.append((k, v[0], v[1], v[2]))
            self.setModel(upTreeView.PartitionModel(self.up_parts))
            self.expandAll()
            self.cb(f'''Chip name: {self.up.get_chip_name_lower()}\nDevice type: {self.up.get_device_type()}\nSoftware version: {self.up.get_up_software_version()}''')
        super(QTreeView, self).update()

    
    def update_cache(self = None):
        if self._file is not None:
            self.up_parts = []
            for k, v in self.up.parts.items():
                self.up_parts.append((k, v[0], v[1], v[2]))
            self.setModel(upTreeView.PartitionModel(self.up_parts))
            self.expandAll()
        super(QTreeView, self).update()

    
    def contextMenuEvent(self, event):
        index = self.indexAt(event.pos())
        if index.isValid():
            item_text = self.model().data(index.siblingAtColumn(0))
            if item_text == 'WELC':
                _pics = self.up.get_welc_pics()
                self.contextMenu = QMenu()
                for i, _pic in enumerate(_pics):
                    label = QLabel()
                    pixmap = QPixmap()
                    pixmap.loadFromData(_pics[0])
                    pixmap = pixmap.scaled(QSize(160, 192))
                    label.setPixmap(pixmap)
                    custom_widget = QWidget()
                    layout = QHBoxLayout()
                    layout.addWidget(QLabel('修改开机画面'))
                    layout.addWidget(label)
                    custom_widget.setLayout(layout)
                    action = QWidgetAction(self.contextMenu)
                    action.setDefaultWidget(custom_widget)
                    action.triggered.connect(partial(self.modify_welc, i))
                    self.contextMenu.addAction(action)
                self.contextMenu.exec(event.globalPos())
                return None
            if None == 'PICS':
                self.contextMenu = RightMenu([
                    '修改皮肤图标'], [
                    self.modify_face])
                return None
            if None == 'PSMP':
                self.contextMenu = RightMenu([
                    '修改 PSMP 变量'], [
                    self.modify_psmp])
                return None
            return None

    
    def modify_psmp(self):
        self.up.save(self._file)
        dig = win_param(self, None, self._file, **('parent', 'flags', 'up_file_name'))
        dig.exec()
        if dig.modified:
            self.up = up_file(self._file)
            self.update_cache()
            return None

    
    def modify_welc(self, pic_index):
        print(f'''Selected pic index: {pic_index}''')
        filepath = QFileDialog.getOpenFileName(self, 'open file dialog', '', 'jpg files(*.jpg)')
        if filepath is not None or filepath[0] != '':
            self.up.make_welc_partition([
                filepath[0]], self._emit_add_text)
            self.update_cache()
            return None
        return None

    
    def _emit_add_text(self, txt):
        self.SignalWin.emit(txt)

    
    def modify_face(self):
        
        def _face_do():
            pics_count = self.up.get_pics_partition_pics_count()
            self._emit_add_text('固件中图像个数： %d\n正在制作图像...' % pics_count)
            self.up.make_pics_partition(png_list, self._emit_add_text)

        directory = QFileDialog.getExistingDirectory(self, 'Select Directory')
        if directory:
            png_list = get_file_list(directory)
            if png_list is not None:
                threading.Thread(_face_do, True, **('target', 'daemon')).start()
                return None
            return None

    
    def save(self, _path = (None,)):
        if self.up is not None:
            if _path is None:
                self.up.save(self._file)
            else:
                self.up.save(_path)
            self.setModel(None)
            self.setEnabled(False)
            return None

    __classcell__ = None


class upexTreeView(QTreeView):
    
    def __init__(self = None, parent = None, cb = None, _dir = None):
        super(upexTreeView, self).__init__(parent)
        self.contextMenu = None
        self.upex = None
        self.cb = cb
        self.setEnabled(False)
        self._dir = _dir

    
    def contextMenuEvent(self, event):
