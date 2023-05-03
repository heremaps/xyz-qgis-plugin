# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import QDialog

from . import get_ui_class
from .ux import TokenUX
from ..common.signal import make_qt_args
from ..models import SpaceConnectionInfo
from ..models.token_model import TokenModel

PlatformAuthUI = get_ui_class("platform_auth_dialog.ui")


class PlatformAuthDialog(QDialog, PlatformAuthUI, TokenUX):
    title = "HERE Platform Credentials"
    message = ""

    signal_open_login_view = pyqtSignal(object)
    signal_login_view_closed = pyqtSignal(object)

    def __init__(self, parent=None):
        """init window"""
        QDialog.__init__(self, parent)
        PlatformAuthUI.setupUi(self, self)
        self.setWindowTitle(self.title)
        if self.message:
            self.label_msg.setText(self.message)
            self.label_msg.setVisible(True)
        self._connected_conn_info = None

    def config(self, token_model: TokenModel, conn_info: SpaceConnectionInfo):
        TokenUX.config(self, token_model)
        token_model.set_server(conn_info.get_server())
        self.btn_use.clicked.connect(self._do_auth)
        self._set_connected_conn_info(conn_info)

    # methods

    def _do_auth(self):
        conn_info = self._get_input_conn_info_without_id()
        conn_info.mark_protected()
        if conn_info.get_user_email():
            self.signal_open_login_view.emit(
                make_qt_args(
                    conn_info,
                    callback=lambda: self.signal_login_view_closed.emit(make_qt_args(conn_info)),
                )
            )
        else:
            self.signal_login_view_closed.emit(make_qt_args(conn_info))

    def get_connected_conn_info(self):
        return self._connected_conn_info

    # callback

    def cb_login_finish(self, conn_info: SpaceConnectionInfo, *a):
        # do not show success button
        # self.comboBox_token.model().sourceModel().set_used_token_idx(-1)
        if conn_info.has_token():
            self.cb_login_success()
        else:
            self.cb_login_fail()

    def cb_login_success(self):
        # ui token
        self.cb_enable_token_ui()
        self.cb_token_used_success()
        self.ui_valid_token()
        # ui status
        self._change_status_success()
        self._change_auth()

    def cb_login_fail(self):
        # ui token
        self.cb_enable_token_ui()
        self.ui_valid_token()
        # ui status
        self._change_status_fail()
        self._clear_auth()

    # ui

    def _set_connected_conn_info(self, conn_info: SpaceConnectionInfo):
        if conn_info.is_valid():
            self._connected_conn_info = conn_info

        proxy_model = self.comboBox_token.model()
        token_model = proxy_model.sourceModel()
        for row in range(proxy_model.rowCount()):
            if row == 0 or (
                conn_info.get_("here_credentials", "") == proxy_model.get_here_credentials(row)
                and conn_info.get_("user_login", "") == proxy_model.get_user_login(row)
                and conn_info.get_("realm", "") == proxy_model.get_realm(row)
            ):
                self.comboBox_token.setCurrentIndex(row)
                # token_model.set_used_token_idx(row) # show success button

                self._change_auth()
                if conn_info.has_valid_here_credentials() or conn_info.has_token():
                    self._change_status_success()
                else:
                    self._change_status_fail()

                if not conn_info.is_valid():
                    self._connected_conn_info = self._get_input_conn_info_without_id()

    def _get_auth_name(self):

        proxy_model = self.comboBox_token.model()
        return proxy_model.get_name(self.comboBox_token.currentIndex())

    def _change_auth(self):
        name = self._get_auth_name()
        self.label_auth_name.setText(name)

    def _clear_auth(self):
        self.label_auth_name.setText("")

    def _change_status_success(self):
        self._change_status(text="Connected", color="green")

    def _change_status_fail(self):
        self._change_status(text="Not connected", color="red")

    def _change_status(self, text="Not connected", color="red"):
        self.label_auth_status.setText(text)
        self.label_auth_status.setStyleSheet(
            "QLabel {{ color : {color}; font-weight: 600; }}".format(color=color)
        )
