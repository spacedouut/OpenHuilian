# Source Generated with Decompyle++
# File: ui_psmp.pyc (Python 3.10)

from PyQt6 import QtCore, QtGui, QtWidgets

class Ui_Dialog_psmp(object):
    
    def setupUi(self, Dialog_psmp):
        Dialog_psmp.setObjectName('Dialog_psmp')
        Dialog_psmp.resize(640, 480)
        self.verticalLayout = QtWidgets.QVBoxLayout(Dialog_psmp)
        self.verticalLayout.setObjectName('verticalLayout')
        self.horizontalLayout_10 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_10.setObjectName('horizontalLayout_10')
        self.verticalLayout.addLayout(self.horizontalLayout_10)
        self.gridLayout_3 = QtWidgets.QGridLayout()
        self.gridLayout_3.setObjectName('gridLayout_3')
        self.pushButton_delitem = QtWidgets.QPushButton(Dialog_psmp, **('parent',))
        self.pushButton_delitem.setStyleSheet('QPushButton {\n        color: white;\n}\nQPushButton:enabled {\n        background: rgb(56,148,148);\n        color: white;\n}\nQPushButton:!enabled {\n        background: rgb(180, 180, 180);\n        color: white;\n}\nQPushButton:enabled:hover {\n        background: rgb(2, 65, 132);\n}\nQPushButton:enabled:pressed {\n        background: rgb(6, 94, 187);\n}')
        self.pushButton_delitem.setObjectName('pushButton_delitem')
        self.gridLayout_3.addWidget(self.pushButton_delitem, 1, 0, 1, 1)
        self.pushButton_addpsm = QtWidgets.QPushButton(Dialog_psmp, **('parent',))
        self.pushButton_addpsm.setStyleSheet('QPushButton {\n        color: white;\n}\nQPushButton:enabled {\n        background: rgb(56,148,148);\n        color: white;\n}\nQPushButton:!enabled {\n        background: rgb(180, 180, 180);\n        color: white;\n}\nQPushButton:enabled:hover {\n        background: rgb(2, 65, 132);\n}\nQPushButton:enabled:pressed {\n        background: rgb(6, 94, 187);\n}')
        self.pushButton_addpsm.setObjectName('pushButton_addpsm')
        self.gridLayout_3.addWidget(self.pushButton_addpsm, 1, 1, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum)
        self.gridLayout_3.addItem(spacerItem, 1, 2, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout_3)
        self.gridLayout = QtWidgets.QGridLayout()
        self.gridLayout.setObjectName('gridLayout')
        self.pushButton_generate = QtWidgets.QPushButton(Dialog_psmp, **('parent',))
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButton_generate.sizePolicy().hasHeightForWidth())
        self.pushButton_generate.setSizePolicy(sizePolicy)
        self.pushButton_generate.setMinimumSize(QtCore.QSize(200, 60))
        self.pushButton_generate.setLayoutDirection(QtCore.Qt.LayoutDirection.LeftToRight)
        self.pushButton_generate.setStyleSheet('QPushButton {\n        color: white;\n}\nQPushButton:enabled {\n        background: rgb(56,148,148);\n        color: white;\n}\nQPushButton:!enabled {\n        background: rgb(180, 180, 180);\n        color: white;\n}\nQPushButton:enabled:hover {\n        background: rgb(2, 65, 132);\n}\nQPushButton:enabled:pressed {\n        background: rgb(6, 94, 187);\n}')
        self.pushButton_generate.setObjectName('pushButton_generate')
        self.gridLayout.addWidget(self.pushButton_generate, 0, 0, 1, 1)
        self.verticalLayout.addLayout(self.gridLayout)
        self.retranslateUi(Dialog_psmp)
        QtCore.QMetaObject.connectSlotsByName(Dialog_psmp)

    
    def retranslateUi(self, Dialog_psmp):
        _translate = QtCore.QCoreApplication.translate
        Dialog_psmp.setWindowTitle(_translate('Dialog_psmp', 'PSMP修改'))
        self.pushButton_delitem.setText(_translate('Dialog_psmp', '删除选中成员'))
        self.pushButton_addpsm.setText(_translate('Dialog_psmp', '添加成员'))
        self.pushButton_generate.setText(_translate('Dialog_psmp', '更新固件文件'))


