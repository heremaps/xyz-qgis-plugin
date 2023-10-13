# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from typing import Dict

from qgis.PyQt.QtCore import pyqtSignal, QSortFilterProxyModel
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtGui import QStandardItem

from . import get_ui_class
from .ux.token_server_ux import TokenWithServerUX
from ..common.signal import make_qt_args
from ..models import SpaceConnectionInfo
from ..models.token_model import TokenModel, ServerModel

PlatformAuthUI = get_ui_class("platform_auth_dialog.ui")


class FilterServerModel(QSortFilterProxyModel):
    def setSourceModel(self, server_model):
        super().setSourceModel(server_model)
        self.setFilterKeyColumn(server_model.get_info_keys().index(server_model.TOKEN_KEY))

        self.INFO_KEYS = server_model.INFO_KEYS
        self.submit_cache = server_model.submit_cache
        self.refresh_model = server_model.refresh_model

    def item(self, row, col):
        return QStandardItem(self.data(self.index(row, col)))


class PlatformAuthDialog(QDialog, PlatformAuthUI, TokenWithServerUX):
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

    def config(
        self,
        token_model: TokenModel,
        server_model: ServerModel,
        map_conn_info: Dict[str, SpaceConnectionInfo],
    ):
        self._set_connected_conn_info(map_conn_info)

        proxy_server_model = FilterServerModel()
        proxy_server_model.setSourceModel(server_model)
        proxy_server_model.setFilterRegExp("^PLATFORM_.+")
        TokenWithServerUX.config(self, token_model, proxy_server_model)

        self.btn_use.clicked.connect(self._do_auth)
        self.comboBox_server_url.currentIndexChanged[int].connect(self._cb_server_changed)
        self.comboBox_token.currentIndexChanged[int].connect(self._cb_token_changed)

        self.comboBox_server_url.setCurrentIndex(-1)
        self.comboBox_server_url.setCurrentIndex(0)

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
        return self._connected_conn_info.get(self.get_input_server())

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

    def cb_login_fail(self):
        # ui token
        self.cb_enable_token_ui()
        self.ui_valid_token()
        # ui status
        self._change_status_fail()

    # ui

    def _set_connected_conn_info(
        self,
        map_conn_info: Dict[str, SpaceConnectionInfo],
    ):
        self._connected_conn_info = map_conn_info

    def _cb_server_changed(self):
        connected = self.get_connected_conn_info()
        if not (connected and connected.is_valid()):
            return

        # if connected and connected.is_valid():
        #     self._connected_conn_info = connected

        proxy_model = self.comboBox_token.model()
        token_model = proxy_model.sourceModel()
        for row in range(proxy_model.rowCount()):
            if self._ui_connected_conn_info(connected, row):
                self.comboBox_token.setCurrentIndex(row)
                # token_model.set_used_token_idx(row) # show success button
                break

                # if not connected.is_valid():
                #     self._connected_conn_info = self._get_input_conn_info_without_id()

    def _cb_token_changed(self, row):
        connected = self.get_connected_conn_info()
        return self._ui_connected_conn_info(connected, row)

    def _ui_connected_conn_info(self, connected: SpaceConnectionInfo, row):
        proxy_model = self.comboBox_token.model()
        if (
            connected
            and connected.get_("here_credentials", "") == proxy_model.get_here_credentials(row)
            and connected.get_("user_login", "") == proxy_model.get_user_login(row)
            and connected.get_("realm", "") == proxy_model.get_realm(row)
        ):
            if connected.has_valid_here_credentials() or connected.has_token():
                self._change_status_success()
            else:
                self._change_status_fail()
            return True
        else:
            self._change_status_fail()
        return False

    def _change_status_success(self):
        self._change_status(text="Connected", color="green")

    def _change_status_fail(self):
        self._change_status(text="Not connected", color="red")

    def _change_status(self, text="Not connected", color="red"):
        self.label_auth_status.setText(text)
        self.label_auth_status.setStyleSheet(
            "QLabel {{ color : {color}; font-weight: 600; }}".format(color=color)
        )
