# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.PyQt.QtWidgets import QDialog
from . import get_ui_class
from .ux import strip_list_string

FilterEditUI = get_ui_class('edit_filter_dialog.ui')

class FilterInfoDialog(QDialog, FilterEditUI):
    title = "XYZ"
    OPERATORS = ["=", "!=", ">=", "<=", ">", "<"]
    ALIAS_OPS = ["=", "!=", "=gte=", "=lte=", "=gt=", "=lt="]
    ALIAS_OPERATORS = dict(zip(OPERATORS, ALIAS_OPS))

    def __init__(self, parent=None):
        """init window"""
        QDialog.__init__(self, parent)
        FilterEditUI.setupUi(self,self)
        self.setWindowTitle(self.title)
        
        self.comboBox_operator.addItems(self.OPERATORS)
        self.lineEdit_name.textChanged.connect(self.ui_enable_btn)
        self.lineEdit_values.textChanged.connect(self.ui_enable_btn)
        self.comboBox_operator.currentIndexChanged.connect(self.ui_enable_btn)
        self.ui_enable_btn()
        
    def ui_enable_btn(self):
        flag = all([
            self.lineEdit_name.text().strip(),
            self.lineEdit_values.text().strip(),
            self.comboBox_operator.currentText().strip(),
            ])
        self.buttonBox.button(self.buttonBox.Ok).setEnabled(flag)
        self.buttonBox.button(self.buttonBox.Ok).clearFocus()

    def get_alias_operator(self):
        return self.ALIAS_OPERATORS[self.comboBox_operator.currentText()]
        
    def get_info(self):
        d = {
            "name": self.lineEdit_name.text(),
            "operator": self.comboBox_operator.currentText().strip(),
            "values": strip_list_string(self.lineEdit_values.text().strip())
        }
        return d

    def get_alias_info(self):
        d = {
            "name": self.lineEdit_name.text(),
            "operator": self.get_alias_operator(),
            "values": strip_list_string(self.lineEdit_values.text().strip())
        }
        return d
        
    def set_info(self, info):
        self.lineEdit_name.setText(info.get("name",""))
        self.lineEdit_values.setText(info.get("values",""))
        operator = info.get("operator")
        if not operator:
            idx = 0
        elif operator in self.ALIAS_OPS:
            idx = self.ALIAS_OPS.index(operator)
        elif operator in self.OPERATORS:
            idx = self.OPERATORS.index(operator)
        else:
            idx = 0
        self.comboBox_operator.setCurrentIndex(idx)
        
class NewFilterInfoDialog(FilterInfoDialog):
    title = "Add New Property Query"
class EditFilterInfoDialog(FilterInfoDialog):
    title = "Edit Property Query"
