# Source Generated with Decompyle++
# File: window_param.pyc (Python 3.10)

from PyQt6.QtWidgets import QMessageBox, QFileDialog, QDialog, QApplication
from PyQt6.QtCore import Qt, QTranslator, QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator, QCursor, QIcon, QPixmap
from util_ui.widget_property import PropertyWidget
from ui_develop.ui_add_psm import *
from ui_develop.ui_psmp import *
from burn_client2q import bc
UP_CFG = {
    'customer_name': ('', None, '客户名称'),
    'chip_serial_id': ('TWS206', [
        'P262',
        '247',
        'TWS206',
        'TWS208',
        'MP3_01'], '芯片型号'),
    'board_name': ('', None, '方案名称'),
    'bt_name': ('', None, '蓝牙名称'),
    'bt_addr': ('AA:BB:CC:DD:EE:FF', None, '蓝牙地址'),
    'sn_info': ('1234567890', None, 'SN序列号'),
    'freq_drift': ('0', None, '频偏校准信息'),
    'rfparam': ('0', None, 'RF参数信息'),
    'bootup_flag': ('1', [
        '1',
        '2',
        '3',
        '4'], '开关机方式\n(开关机码/中间电平/5V常在/vbus out)'),
    'paired_flag': ('U', [
        'P',
        'U'], '配对标记'),
    'ear_type': ('L', [
        'L',
        'R'], '左右耳信息'),
    'bat_level': ('0', None, '电池电量信息'),
    'en_info': ('0', None, '公版开关'),
    'baseboard_ver_info': ('0', None, '公版固件版本号'),
    'customer_ver_info': ('0', None, '客户固件版本号') }

class class_psm_add_item_dialog(Ui_DialogAddPsm, QDialog):
    
    def _trans_to_english(self):
        self.trans = QTranslator()
        self.trans.load('ui_develop/ui_add_psm')
        app = QApplication.instance()
        app.installTranslator(self.trans)
        self.retranslateUi(self)

    
    def __init__(self = None, *args, **kwargs):
        pass
    # WARNING: Decompyle incomplete

    
    def UI_value_mode(self):
        self.switch_value_edit_mode(self.checkBox_edit_mode.isChecked())

    
    def switch_value_edit_mode(self, isString = (False,)):
        self.lineEdit_newvalue.clear()
        if not isString:
            reg = QRegularExpression('^[0-9a-fA-F ]+$')
            validator = QRegularExpressionValidator(reg, self)
            self.lineEdit_newvalue.setValidator(validator)
            return None
        reg = None('^[a-zA-Z0-9\\-:_]+$')
        validator = QRegularExpressionValidator(reg, self)
        self.lineEdit_newvalue.setValidator(validator)

    __classcell__ = None


class class_psm_item:
    
    def __init__(self, page, root, name, value):
        (self.page, self.root, self.name, self.value) = (page, root, name, value)
        v_string = ' '.join((lambda .0: [ '%02X' % b for b in .0 ])(self.value))
        self.editor = self.page.addEditLineItem(self.root, self.name, v_string, self.UI_try_visible_value(v_string), '^[0-9a-fA-F ]+$', **('reg_exp_str',))
        self.editor.textChanged.connect(self.UI_change_value)

    
    def UI_try_visible_value(self, hex_txt):
        
        try:
            hex_data = bytes.fromhex(hex_txt)
            tool_tip = hex_data.decode('ascii')
        finally:
            return tool_tip
            tool_tip = hex_txt
            return tool_tip


    
    def UI_change_value(self):
        self.editor.setToolTip(self.UI_try_visible_value(self.editor.text()))



class win_param(Ui_Dialog_psmp, QDialog):
    SignalWin = QtCore.pyqtSignal(dict)
    
    def _trans_to_english(self):
        self.trans = QTranslator()
        self.trans.load('ui_develop/ui_psmp')
        app = QApplication.instance()
        app.installTranslator(self.trans)
        self.retranslateUi(self)

    
    def __init__(self, parent, flags, *args, **kwargs):
        QDialog.__init__(self, parent, **('parent',))
        self.setupUi(self)
        self.pushButton_generate.clicked.connect(self.UI_gen)
        self.pushButton_addpsm.clicked.connect(self.UI_add)
        self.pushButton_delitem.clicked.connect(self.UI_del)
        self.pushButton_delitem.setEnabled(False)
        self.page = PropertyWidget(self, self.item_change, **('itemChanged',))
        self.horizontalLayout_10.addWidget(self.page)
        self.psm_root = self.page.addGroup('PSM info')
        self.page.expandAll()
        self.up_file_name = kwargs.get('up_file_name', '')
        self.psms = []
        self.enable_action(False)
        self.SignalWin.connect(self.update_data)
        bc.do_register((self, [
            'psm_get',
            'psm_set']))
        self.modified = False
        bc.do_send({
            'request': 'psm_get',
            'payload': {
                'up_file_url': self.up_file_name } })

    
    def enable_action(self, true_false):
        self.pushButton_generate.setEnabled(true_false)
        self.pushButton_addpsm.setEnabled(true_false)

    
    def item_change(self):
        if self.page.focus_at() != -1:
            self.pushButton_delitem.setEnabled(True)
            return None
        None.pushButton_delitem.setEnabled(False)

    
    def update_data(self, protocol):
        if protocol.get('response') == 'psm_get':
            self.psms = []
            self.page.remove_items()
            self.enable_action(True)
            if 'keys' in protocol.get('payload').keys():
                vars_dict = protocol.get('payload')['keys']
                for k, v in vars_dict.items():
                    self.psms.append(class_psm_item(self.page, self.psm_root, k, bytes.fromhex(v)))
            return None
        return None
        if protocol.get('response') == 'psm_set':
            self.modified = True
            self.close()
            return None

    
    def UI_add(self):
        d = class_psm_add_item_dialog()
        if d.exec() == QDialog.DialogCode.Accepted:
            
            try:
                n = d.lineEdit_newname.currentText().encode()
                if len(n) == 0:
                    pass
            finally:
                return None
                n += bytes(256 - len(n))
                if not d.checkBox_edit_mode.isChecked():
                    v = bytes.fromhex(d.lineEdit_newvalue.text())
                else:
                    v = d.lineEdit_newvalue.text().encode()
                if v != b'':
                    new_item = True
                    for item in self.psms:
                        if item.name == n.decode():
                            v_string = ' '.join((lambda .0: [ '%02X' % b for b in .0 ])(v))
                            item.editor.setText(v_string)
                            new_item = False
                    if new_item:
                        self.psms.append(class_psm_item(self.page, self.psm_root, n.decode(), v))
                    return None
                return None
                return None
                QMessageBox.information(self, 'Tips', 'Invalid format!', QMessageBox.StandardButton.Ok)
                return None
                return None


    
    def UI_del(self, ind = (None,)):
        ind = self.page.focus_at()
        if ind != -1:
            self.psms.remove(self.psms[ind])
            self.page.remove_item(ind)
            return None

    
    def UI_gen(self):
        self.setCursor(QCursor(Qt.CursorShape.WaitCursor))
        pl_dict = {
            'up_file_url': self.up_file_name,
            'keys': { } }
    # WARNING: Decompyle incomplete

    
    def closeEvent(self, event = (None,)):
        bc.do_unregister(self)


