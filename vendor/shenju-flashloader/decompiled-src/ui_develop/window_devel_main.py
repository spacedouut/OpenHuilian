# Source Generated with Decompyle++
# File: window_devel_main.pyc (Python 3.10)

import verno
from PyQt6.QtWidgets import QMainWindow, QApplication
from PyQt6.QtCore import Qt, QTranslator, QSettings
from PyQt6.QtGui import QIcon, QPixmap, QKeyEvent
from ui_develop.ui_main import *
from util_upgrade import main_upgrade
from ui_develop.window_param import win_param
from ui_develop.window_bron import win_bron
from ui_develop.window_serial import win_serial
from ui_develop.window_dev_setting import window_setting
from ui_develop.window_extend import win_extend

class main_window(Ui_MainWindow, QMainWindow):
    
    def _tigger_english(self):
        self.actionEnglish.setChecked(True)
        self.actionChinese.setChecked(False)
        self.trans.load('ui_develop/ui_main')
        app = QApplication.instance()
        app.installTranslator(self.trans)
        self.retranslateUi(self)
        self.setWindowTitle('Firmware tool ' + verno.FLASH_LOADER_PRO_VERSION)

    
    def _tigger_chinese(self):
        self.actionEnglish.setChecked(False)
        self.actionChinese.setChecked(True)
        app = QApplication.instance()
        app.removeTranslator(self.trans)
        self.retranslateUi(self)
        self.setWindowTitle('固件工具 ' + verno.FLASH_LOADER_PRO_VERSION)

    
    def changePage(self, page_index):
        self.stackedWidget.setCurrentIndex(page_index)
        self.actionBurn.setChecked(page_index == 0)
        self.actionModify.setChecked(page_index == 1)

    
    def __init__(self, parent, flags, *args, **kwargs):
        QMainWindow.__init__(self, parent, **('parent',))
        self.setupUi(self)
        self.readSettings()
        self.trans = QTranslator()
        self._tigger_chinese()
        icon = QtGui.QIcon()
        icon.addPixmap(QPixmap('flashloaderSL-DEV.ico'), QIcon.Mode.Normal, QIcon.State.Off)
        self.setWindowIcon(icon)
        self.statusbar.showMessage('Ready.')
        None((lambda : self.changePage(0)))
        None((lambda : self.changePage(1)))
        cmds = [
            (self.actionSetting, self.UI_Setting),
            (self.actionEnglish, self._tigger_english),
            (self.actionChinese, self._tigger_chinese),
            (self.actionCheck_update, self.UI_update)]
        (lambda .0: [ item[0].triggered.connect(item[1]) for item in .0 ])(cmds)
        self.bron_win = win_bron(self, self)
        self.para_win = win_param(self, self)
        self.serial_win = win_serial(self, self)
        self.extend_win = win_extend(self, self)

    
    def readSettings(self):
        settings = QSettings('shenju', 'flashloaderSL')
        self.restoreGeometry(settings.value('mainWindowGeometry', self.saveGeometry()))
        self.restoreState(settings.value('mainWindowState', self.saveState()))

    
    def writeSettings(self):
        settings = QSettings('shenju', 'flashloaderSL')
        settings.setValue('mainWindowGeometry', self.saveGeometry())
        settings.setValue('mainWindowState', self.saveState())

    
    def keyPressEvent(self = None, e = None):
        if e.key() == Qt.Key.Key_Return or e.key() == Qt.Key.Key_Enter:
            if self.serial_win.ui.ui_pushbtn_send.isEnabled():
                self.serial_win.UI_Send()
                return None
            return None

    
    def closeEvent(self = None, event = None):
        self.bron_win.closeEvent(event)
        self.para_win.closeEvent(event)
        self.serial_win.closeEvent(event)
        self.extend_win.closeEvent(event)
        self.writeSettings()
        super(main_window, self).closeEvent(event)

    
    def UI_Setting(self):
        window_setting(self, None, **('parent', 'flags')).exec()

    
    def UI_update(self):
        main_upgrade.upgrade(self)

    __classcell__ = None

