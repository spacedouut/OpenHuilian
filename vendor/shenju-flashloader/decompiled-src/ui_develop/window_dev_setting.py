# Source Generated with Decompyle++
# File: window_dev_setting.pyc (Python 3.10)

from ui_develop.ui_dev_setting import Ui_Dialog
from PyQt6 import QtCore
from PyQt6.QtWidgets import QDialog, QApplication
from PyQt6.QtCore import QTranslator
from util_ui.widget_property import PropertyWidget
from burn_client2q import bc
import re

class window_setting(Ui_Dialog, QDialog):
    SignalWin = QtCore.pyqtSignal(dict)
    
    def _trans_to_english(self):
        self.trans = QTranslator()
        self.trans.load('ui_develop/ui_dev_setting')
        app = QApplication.instance()
        app.installTranslator(self.trans)
        self.retranslateUi(self)

    
    def __init__(self, parent, flags, *args, **kwargs):
        QDialog.__init__(self, parent, **('parent',))
        self.setupUi(self)
        self.buttonBox.accepted.connect(self.UI_save)
        self.SignalWin.connect(self.update_data)
        bc.do_register((self, [
            'get_config']))
        bc.do_send({
            'request': 'get_config' })

    
    def update_data(self, protocol):
        if protocol.get('response') == 'get_config':
            self.page = PropertyWidget(self)
            self.verticalLayout.addWidget(self.page)
            changgui_root = self.page.addGroup('Burn')
            self.checkAutoDownLoad = self.page.addCheckBoxItem(changgui_root, '自动下载:', '', protocol.get('payload').get('auto_download').get('current'))
            self.checkRebootAfterDownLoad = self.page.addCheckBoxItem(changgui_root, '烧录完后自动重启:', '', protocol.get('payload').get('restart_after_burn').get('current'))
            self.restoreFactoryAfterReboot = self.page.addCheckBoxItem(changgui_root, '烧录完重启后恢复出厂设置:', '', protocol.get('payload').get('restore_factory').get('current'))
            self.checkEraseOnly = self.page.addCheckBoxItem(changgui_root, '仅擦除:', '', protocol.get('payload').get('erase_only').get('current'))
            self.combFlashSize = self.page.addComBoxItem(changgui_root, 'Flash size(KB):', protocol.get('payload').get('flash_size').get('selects'), protocol.get('payload').get('flash_size').get('selects').index(protocol.get('payload').get('flash_size').get('current')))
            self.checkBox_rf_check = self.page.addCheckBoxItem(changgui_root, '频偏校准（清除PSM变量）:', '', protocol.get('payload').get('rf_check').get('current'))
            self.bluethAddrNow = self.page.addEditLineItem(changgui_root, '蓝牙地址递增基数:', str(protocol.get('payload').get('firmware_bt_incr')))
            self.bt_addr = self.page.addEditLineItem(changgui_root, '蓝牙地址基值:', protocol.get('payload').get('firmware_bt_addr'))
            self.bt_addr.setInputMask('HH:HH:HH:HH:HH:HH;_')
            self.page.expandAll()
            return None

    
    def UI_save(self):
        if not re.compile('^\\s*([0-9a-fA-F]{2,2}:){5,5}[0-9a-fA-F]{2,2}\\s*$').match(self.bt_addr.text()):
            return False
        None.do_unregister(self)
        bc.do_send({
            'request': 'set_config',
            'payload': {
                'auto_download': self.checkAutoDownLoad.isChecked(),
                'restart_after_burn': self.checkRebootAfterDownLoad.isChecked(),
                'restore_factory': self.restoreFactoryAfterReboot.isChecked(),
                'erase_only': self.checkEraseOnly.isChecked(),
                'rf_check': self.checkBox_rf_check.isChecked(),
                'firmware_bt_incr': int(self.bluethAddrNow.text()),
                'firmware_bt_addr': self.bt_addr.text(),
                'flash_size': int(self.combFlashSize.currentText()) } })

    
    def closeEvent(self, ev):
        bc.do_unregister(self)


