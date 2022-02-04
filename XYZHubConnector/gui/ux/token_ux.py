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

from ...xyz_qgis.controller import make_qt_args
from ...xyz_qgis.models import SpaceConnectionInfo
from ...xyz_qgis.models.token_model import ComboBoxProxyModel, TokenModel
from ..token_dialog import TokenDialog

from ..iml.iml_token_dialog import IMLTokenDialog
from ...xyz_qgis.iml.models.iml_token_model import IMLComboBoxProxyModel

from .ux import UXDecorator


class SecretServerUX(UXDecorator):
    def __init__(self):
        # these are like abstract variables
        self.comboBox_server = None

    def config_secret(self, secret):
        self._secret_cnt = 0
        self._secret = secret
        if secret.activated():
            self.comboBox_server.setVisible(True)  # show for internal
            self._check_secret = lambda: None
        else:
            self.comboBox_server.setCurrentIndex(0)
            self.comboBox_server.setVisible(False)  # disable for external

    def _check_secret(self):
        self._secret_cnt += 1
        if self._secret_cnt == 5:
            self._secret.activate()
            self.comboBox_server.setVisible(True)  # show for internal
            self._check_secret = lambda: None

    def mouseDoubleClickEvent(self, event):
        self._check_secret()


class TokenUX(UXDecorator):
    """UX for Token comboBox with token button, use token button and connection info"""

    signal_use_token = pyqtSignal(object)

    def __init__(self):
        # these are like abstract variables
        self.comboBox_token = None
        self.btn_use = None
        self.btn_token = None

        self.conn_info = None

    def config(self, token_model: TokenModel):
        self.used_token_status_txt = "Connect"
        self.conn_info = SpaceConnectionInfo()

        self.token_model = token_model
        token_model.set_invalid_token_idx(-1)

        proxy_model = IMLComboBoxProxyModel()
        proxy_model.setSourceModel(token_model)
        proxy_model.set_keys(token_model.INFO_KEYS)

        self.comboBox_token.setModel(proxy_model)
        self.comboBox_token.setInsertPolicy(self.comboBox_token.NoInsert)
        self.comboBox_token.setDuplicatesEnabled(False)

        self.token_dialog = IMLTokenDialog(self)
        self.token_dialog.config(token_model)

        self.comboBox_token.currentIndexChanged[int].connect(self.ui_valid_input)
        # self.comboBox_token.editTextChanged.connect(self.ui_valid_input)

        self.btn_use.clicked.connect(self.cb_token_used)
        self.btn_token.clicked.connect(self.open_token_dialog)

        self.comboBox_token.setCurrentIndex(0)
        self.ui_valid_input()  # valid_input initially (explicit)

    def open_token_dialog(self):
        idx = self.comboBox_token.currentIndex()
        self.token_dialog.set_active_idx(idx)
        self.token_dialog.exec_()
        idx = self.token_dialog.get_active_idx()
        self.comboBox_token.setCurrentIndex(idx)
        return self.token_model.is_used_token_modified()

    def get_input_token(self):
        proxy_model = self.comboBox_token.model()
        return proxy_model.get_token(self.comboBox_token.currentIndex())

    def get_input_server(self):
        return self.token_model.get_server()

    def get_input_here_credentials(self):
        proxy_model = self.comboBox_token.model()
        return proxy_model.get_here_credentials(self.comboBox_token.currentIndex())

    def get_input_user_login(self):
        proxy_model = self.comboBox_token.model()
        return proxy_model.get_user_login(self.comboBox_token.currentIndex())

    def get_input_realm(self):
        proxy_model = self.comboBox_token.model()
        return proxy_model.get_realm(self.comboBox_token.currentIndex())

    def _get_input_conn_info_without_id(self):
        token = self.get_input_token()
        server = self.get_input_server()
        here_credentials = self.get_input_here_credentials()
        user_login = self.get_input_user_login()
        realm = self.get_input_realm()
        conn_info = SpaceConnectionInfo()
        conn_info.set_(
            token=token,
            server=server,
            here_credentials=here_credentials,
            user_login=user_login,
            realm=realm,
        )
        return conn_info

    def cb_update_conn_info(self, conn_info: SpaceConnectionInfo, *a, **kw):
        realm = conn_info.get_realm()
        if realm:
            row = self.comboBox_token.currentIndex()
            token_info = self.token_model.get_data(row)
            token_info["realm"] = realm
            info_keys = self.token_model.get_info_keys()
            for col, (key, qitem,) in enumerate(
                zip(info_keys, self.token_model.qitems_from_data(token_info, info_keys=info_keys))
            ):
                if key in ["realm"]:
                    self.token_model.setItem(row, col, qitem)
            self.token_model.modify_token_idx(row)
            self.token_model.submit_cache()

    def cb_enable_token_ui(self, flag=True):
        txt_clicked = "Checking.."
        txt0 = "Connect"
        if not flag:
            self.btn_use.setText(txt_clicked)
        elif self.btn_use.text() == txt_clicked:
            self.btn_use.setText(txt0)
        self.btn_use.setEnabled(flag)
        self.comboBox_token.setEnabled(flag)

    def cb_token_used_success(self, *a):
        self.used_token_status_txt = "Success"

    def cb_token_used(self, *a):
        conn_info = self._get_input_conn_info_without_id()
        if not conn_info.is_valid():
            return
        self.used_token_status_txt = "Connect"
        # disable button
        self.cb_enable_token_ui(False)
        # gui -> pending token
        self.token_model.set_used_token_idx(self.comboBox_token.currentIndex())
        # emit
        self.signal_use_token.emit(make_qt_args(conn_info))
        self.conn_info = conn_info

    def ui_valid_token(self, *a):
        """Return true when token is used and shows Ok!"""
        flag_token = (
            len(self.get_input_token()) > 0
            or len(self.get_input_here_credentials()) > 0
            or bool(self.get_input_user_login())
        )
        self.btn_use.setEnabled(flag_token)
        # self.btn_clear_token.setEnabled(flag_token)
        idx = self.comboBox_token.currentIndex()
        flag = self.token_model.is_used_token_idx(idx)
        txt = self.used_token_status_txt if flag else "Connect"
        self.btn_use.setText(txt)
        return flag

    def ui_valid_input(self, *a):
        return self.ui_valid_token()
