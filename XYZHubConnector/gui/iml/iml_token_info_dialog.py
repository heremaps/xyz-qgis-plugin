# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2021 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.PyQt.QtWidgets import QDialog
from .. import get_ui_class
from ..token_info_dialog import ServerInfoDialog
from ...xyz_qgis.models import API_TYPES
from ...xyz_qgis.iml.models.iml_token_model import get_api_type


IMLTokenEditUI = get_ui_class("edit_iml_token_dialog.ui")


class IMLTokenInfoDialog(QDialog, IMLTokenEditUI):
    ui_class = IMLTokenEditUI
    txt_value = "App Credentials"
    file_filter = "*.properties"

    def __init__(self, parent=None):
        """init window"""
        QDialog.__init__(self, parent)
        IMLTokenEditUI.setupUi(self, self)
        self.setWindowTitle(self.title)
        self.label_value.setText(self.txt_value)
        self.mQgsFileWidget.setFilter(self.file_filter)

        self.checkBox_user_login.toggled.connect(self._cb_user_login)
        self.lineEdit_name.textChanged.connect(self.ui_enable_btn)
        self.mQgsFileWidget.fileChanged.connect(self.ui_enable_btn)
        self.lineEdit_email.textChanged.connect(self.ui_enable_btn)
        self.checkBox_user_login.toggled.connect(self.ui_enable_btn)
        self.checkBox_user_login.setChecked(True)
        self.ui_enable_btn()

    def _cb_user_login(self, flag):
        self.label_value.setEnabled(not flag)
        self.mQgsFileWidget.setEnabled(not flag)
        self.mQgsFileWidget.setFilePath("")
        self.label_email.setEnabled(flag)
        self.lineEdit_email.setEnabled(flag)
        self.lineEdit_email.setText("")

    def ui_enable_btn(self, *a):
        flag = all(
            [
                self.lineEdit_name.text().strip(),
                self.mQgsFileWidget.filePath().strip() or self.lineEdit_email.text().strip(),
            ]
        )
        self.buttonBox.button(self.buttonBox.Ok).setEnabled(flag)
        self.buttonBox.button(self.buttonBox.Ok).clearFocus()

    def get_info(self):
        d = {
            "name": self.lineEdit_name.text().strip(),
            "here_credentials": self.mQgsFileWidget.filePath().strip(),
            "user_login": self.lineEdit_email.text().strip(),
        }
        return d

    def set_info(self, token_info):
        self.checkBox_user_login.setChecked(bool(token_info.get("user_login")))
        self.lineEdit_email.setText(token_info.get("user_login"))
        self.lineEdit_name.setText(token_info.get("name", ""))
        self.mQgsFileWidget.setFilePath(
            token_info.get("token", "")
        )  # TODO: rename token_model output to here_credentials


class NewIMLTokenInfoDialog(IMLTokenInfoDialog):
    title = "Add New Platform Credentials"


class EditIMLTokenInfoDialog(IMLTokenInfoDialog):
    title = "Edit Platform Credentials"


class IMLServerInfoDialog(ServerInfoDialog):
    PLATFORM_SERVERS = ["PLATFORM_PRD", "PLATFORM_SIT"]

    def __init__(self, parent=None):
        """init window"""
        super().__init__(parent)
        self.label_api_type.setVisible(True)
        self.comboBox_api_type.setVisible(True)
        self.comboBox_api_type.addItems([s.upper() for s in API_TYPES])
        self.comboBox_token.addItems(self.PLATFORM_SERVERS)

        self.comboBox_api_type.currentIndexChanged.connect(self.cb_change_api_type)
        self.comboBox_api_type.currentIndexChanged.connect(self.ui_enable_btn)

    def cb_change_api_type(self, idx):
        api_type = API_TYPES[idx]
        if api_type == API_TYPES.PLATFORM:
            self.lineEdit_token.setVisible(False)
            self.comboBox_token.setVisible(True)
        else:
            self.comboBox_token.setVisible(False)
            self.lineEdit_token.setVisible(True)

    def get_platform_server(self):
        idx = self.comboBox_token.currentIndex()
        return self.PLATFORM_SERVERS[idx]

    def get_server(self):
        return self.lineEdit_token.text().strip()

    def get_api_type(self):
        idx = self.comboBox_api_type.currentIndex()
        return API_TYPES[idx]

    def set_info(self, token_info):
        server = token_info.get("server", "")
        api_type = get_api_type(server)
        self.lineEdit_name.setText(token_info.get("name", ""))
        if api_type == API_TYPES.PLATFORM:
            idx = API_TYPES.index(api_type) if api_type in API_TYPES else 0
            self.comboBox_api_type.setCurrentIndex(idx)
            idx = self.PLATFORM_SERVERS.index(server) if server in self.PLATFORM_SERVERS else 0
            self.comboBox_token.setCurrentIndex(idx)
        else:
            self.lineEdit_token.setText(token_info.get("server", ""))

    def get_value(self):
        api_type = self.get_api_type()
        if api_type == API_TYPES.PLATFORM:
            return self.get_platform_server()
        else:
            return self.get_server()


class NewIMLServerInfoDialog(IMLServerInfoDialog):
    title = "Add New HERE Server"


class EditIMLServerInfoDialog(IMLServerInfoDialog):
    title = "Edit HERE Server"
