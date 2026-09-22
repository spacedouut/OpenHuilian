# Source Generated with Decompyle++
# File: ui_dev_setting.pyc (Python 3.10)

from PyQt6 import QtCore, QtGui, QtWidgets

class Ui_Dialog(object):
    
    def setupUi(self, Dialog):
        Dialog.setObjectName('Dialog')
        Dialog.resize(800, 600)
        Dialog.setWhatsThis('')
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(Dialog)
        self.verticalLayout_2.setObjectName('verticalLayout_2')
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName('verticalLayout')
        self.verticalLayout_2.addLayout(self.verticalLayout)
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog, **('parent',))
        self.buttonBox.setOrientation(QtCore.Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.StandardButton.Save)
        self.buttonBox.setCenterButtons(False)
        self.buttonBox.setObjectName('buttonBox')
        self.verticalLayout_2.addWidget(self.buttonBox)
        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    
    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate('Dialog', '配置信息'))


