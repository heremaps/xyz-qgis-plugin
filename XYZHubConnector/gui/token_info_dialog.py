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

TokenEditUI = get_ui_class('edit_token_dialog.ui')

class TokenInfoDialog(QDialog, TokenEditUI):
    title = "XYZ"
    def __init__(self, parent=None):
        """init window"""
        QDialog.__init__(self, parent)
        TokenEditUI.setupUi(self,self)
        self.setWindowTitle(self.title)
        
        self.lineEdit_name.textChanged.connect(self.ui_enable_btn)
        self.lineEdit_token.textChanged.connect(self.ui_enable_btn)
        self.ui_enable_btn()
        
    def get_token_info(self):
        d = {
            "name": self.lineEdit_name.text(),
            "token": self.lineEdit_token.text(),
        }
        return d
    def set_token_info(self, token_info):
        self.lineEdit_name.setText(token_info.get("name",""))
        self.lineEdit_token.setText(token_info.get("token",""))
        
    def ui_enable_btn(self):
        flag = all([
            self.lineEdit_name.text().strip(),
            self.lineEdit_token.text().strip()
            ])
        self.buttonBox.button(self.buttonBox.Ok).setEnabled(flag)
        self.buttonBox.button(self.buttonBox.Ok).clearFocus()

class NewTokenInfoDialog(TokenInfoDialog):
    title = "Add new token"
class EditTokenInfoDialog(TokenInfoDialog):
    title = "Edit token"
