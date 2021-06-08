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

class NameValueDialog(QDialog, TokenEditUI):
    title = "XYZ"
    txt_value="Value"
    def __init__(self, parent=None):
        """init window"""
        QDialog.__init__(self, parent)
        TokenEditUI.setupUi(self,self)
        self.setWindowTitle(self.title)
        self.label_value.setText(self.txt_value)
        
        self.lineEdit_name.textChanged.connect(self.ui_enable_btn)
        self.lineEdit_token.textChanged.connect(self.ui_enable_btn)
        self.ui_enable_btn()
        
    def ui_enable_btn(self, *a):
        flag = all([
            self.get_name(),
            self.get_value()
            ])
        self.buttonBox.button(self.buttonBox.Ok).setEnabled(flag)
        self.buttonBox.button(self.buttonBox.Ok).clearFocus()

    def get_value(self):
        return self.lineEdit_token.text().strip()

    def get_name(self):
        return self.lineEdit_name.text().strip()


class TokenInfoDialog(NameValueDialog):
    txt_value="Token"
    def get_info(self):
        d = {
            "name": self.get_name(),
            "token": self.get_value(),
        }
        return d
    def set_info(self, token_info):
        self.lineEdit_name.setText(token_info.get("name",""))
        self.lineEdit_token.setText(token_info.get("token",""))
        
class NewTokenInfoDialog(TokenInfoDialog):
    title = "Add New HERE Token"
class EditTokenInfoDialog(TokenInfoDialog):
    title = "Edit HERE Token"


class ServerInfoDialog(NameValueDialog):
    txt_value="Server"
    def get_info(self):
        d = {
            "name": self.get_name(),
            "server": self.get_value(),
        }
        return d
    def set_info(self, token_info):
        self.lineEdit_name.setText(token_info.get("name",""))
        self.lineEdit_token.setText(token_info.get("server",""))
        
class NewServerInfoDialog(ServerInfoDialog):
    title = "Add New HERE Server"
    
class EditServerInfoDialog(ServerInfoDialog):
    title = "Edit HERE Server"
