# Source Generated with Decompyle++
# File: ui_add_psm.pyc (Python 3.10)

from PyQt6 import QtCore, QtGui, QtWidgets

class Ui_DialogAddPsm(object):
    
    def setupUi(self, DialogAddPsm):
        DialogAddPsm.setObjectName('DialogAddPsm')
        DialogAddPsm.resize(800, 240)
        self.verticalLayout = QtWidgets.QVBoxLayout(DialogAddPsm)
        self.verticalLayout.setObjectName('verticalLayout')
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName('gridLayout')
        self.label_name = QtWidgets.QLabel(DialogAddPsm, **('parent',))
        self.label_name.setObjectName('label_name')
        self.gridLayout.addWidget(self.label_name, 0, 0, 1, 1)
        self.lineEdit_newvalue = QtWidgets.QLineEdit(DialogAddPsm, **('parent',))
        self.lineEdit_newvalue.setObjectName('lineEdit_newvalue')
        self.gridLayout.addWidget(self.lineEdit_newvalue, 1, 1, 1, 1)
        self.label_value = QtWidgets.QLabel(DialogAddPsm, **('parent',))
        self.label_value.setObjectName('label_value')
        self.gridLayout.addWidget(self.label_value, 1, 0, 1, 1)
        self.lineEdit_newname = QtWidgets.QComboBox(DialogAddPsm, **('parent',))
        self.lineEdit_newname.setEditable(True)
        self.lineEdit_newname.setObjectName('lineEdit_newname')
        self.gridLayout.addWidget(self.lineEdit_newname, 0, 1, 1, 1)
        self.checkBox_edit_mode = QtWidgets.QCheckBox(DialogAddPsm, **('parent',))
        self.checkBox_edit_mode.setChecked(True)
        self.checkBox_edit_mode.setObjectName('checkBox_edit_mode')
        self.gridLayout.addWidget(self.checkBox_edit_mode, 1, 2, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)
        self.buttonBox = QtWidgets.QDialogButtonBox(DialogAddPsm, **('parent',))
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Cancel | QtWidgets.QDialogButtonBox.StandardButton.Ok)
        self.buttonBox.setObjectName('buttonBox')
        self.verticalLayout.addWidget(self.buttonBox)
        self.retranslateUi(DialogAddPsm)
        self.buttonBox.accepted.connect(DialogAddPsm.accept)
        self.buttonBox.rejected.connect(DialogAddPsm.reject)
        QtCore.QMetaObject.connectSlotsByName(DialogAddPsm)

    
    def retranslateUi(self, DialogAddPsm):
        _translate = QtCore.QCoreApplication.translate
        DialogAddPsm.setWindowTitle(_translate('DialogAddPsm', '添加PSM新变量'))
        self.label_name.setText(_translate('DialogAddPsm', '名称'))
        self.label_value.setText(_translate('DialogAddPsm', '值'))
        self.checkBox_edit_mode.setText(_translate('DialogAddPsm', '按照字符串方式编辑'))


