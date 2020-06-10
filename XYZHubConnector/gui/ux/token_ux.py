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

from ...xyz_qgis.models import SpaceConnectionInfo
from ...xyz_qgis.models.token_model import GroupTokenModel, ComboBoxProxyModel
from ...xyz_qgis.controller import make_qt_args
from ..token_dialog import TokenDialog
from ..util_dialog import ConfirmDialog
from .ux import UXDecorator
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem

class ServerUX(UXDecorator):
    def __init__(self):
        # these are like abstract variables
        self.comboBox_server = None
    def config_secret(self, secret):
        self._secret_cnt = 0
        self._secret = secret
        if secret.activated():
            self.comboBox_server.setVisible(True) # show for internal
            self._check_secret = lambda:None
        else:
            self.comboBox_server.setCurrentIndex(0)
            self.comboBox_server.setVisible(False) # disable for external
    def _check_secret(self):
        self._secret_cnt += 1
        if self._secret_cnt == 5:
            self._secret.activate()
            self.comboBox_server.setVisible(True) # show for internal
            self._check_secret = lambda:None
    def mouseDoubleClickEvent(self, event):
        self._check_secret()

class TokenUX(ServerUX):
    signal_use_token = pyqtSignal(object)
    def __init__(self):
        # these are like abstract variables
        self.comboBox_token = None
        self.btn_use = None
        self.btn_token = None
        self.comboBox_server = None
        self.conn_info = None
        #
    def config(self, token_model: GroupTokenModel):
        self.conn_info = SpaceConnectionInfo()

        self.token_model = token_model
        token_model.set_invalid_token_idx(-1)

        proxy_model = ComboBoxProxyModel()
        proxy_model.setSourceModel( token_model)
        proxy_model.set_keys(token_model.INFO_KEYS)

        self.comboBox_token.setModel( proxy_model)
        self.comboBox_token.setInsertPolicy(self.comboBox_token.NoInsert)
        self.comboBox_token.setDuplicatesEnabled(False)

        self.comboBox_server.currentIndexChanged[str].connect(token_model.set_server)
        self.comboBox_server.currentIndexChanged[str].connect(self.set_server)
        self.comboBox_server.currentIndexChanged[str].connect(self.ui_valid_input)

        token_model.set_server(self.comboBox_server.currentText())
        self.conn_info.set_server(self.comboBox_server.currentText())

        self.token_dialog = TokenDialog(self)
        self.token_dialog.config(token_model)

        # self.comboBox_token.currentIndexChanged[int].connect(self.cb_comboxBox_token_selected)
        self.comboBox_token.currentIndexChanged[int].connect(self.ui_valid_input)
        # self.comboBox_token.editTextChanged.connect(self.ui_valid_input)

        self.btn_use.clicked.connect(self.cb_token_used)
        self.btn_token.clicked.connect(self.open_token_dialog)

        self.comboBox_token.setCurrentIndex(0)
        self.ui_valid_input() # valid_input initially (explicit)

    def open_token_dialog(self):
        idx = self.comboBox_token.currentIndex()
        self.token_dialog.set_current_idx(idx)
        self.token_dialog.exec_()
        idx = self.token_dialog.current_idx
        self.comboBox_token.setCurrentIndex(idx)
        return self.token_dialog.is_used_token_changed

    def set_server(self,server):
        self.conn_info.set_server(server)
        self.token_model.reset_used_token_idx()

    def get_input_token(self):
        proxy_model = self.comboBox_token.model()
        return proxy_model.get_token(self.comboBox_token.currentIndex())
    def cb_enable_token_ui(self,flag=True):
        txt_clicked = "Checking.."
        txt0 = "Use"
        if not flag:
            self.btn_use.setText(txt_clicked)
        elif self.btn_use.text() == txt_clicked:
            self.btn_use.setText(txt0)
        self.btn_use.setEnabled(flag)
        self.comboBox_server.setEnabled(flag)
        self.comboBox_token.setEnabled(flag)
    def cb_token_used(self):
        token = self.get_input_token()
        if len(token) == 0: 
            return
        # disable button
        self.cb_enable_token_ui(False)
        # gui -> pending token
        self.token_model.set_used_token_idx(self.comboBox_token.currentIndex())
        self.conn_info.set_(token=token)
        conn_info = SpaceConnectionInfo(self.conn_info)
        self.signal_use_token.emit( make_qt_args(conn_info) )
    def cb_comboxBox_token_selected(self, index):
        flag_edit = True if index == 0 else False
        self.comboBox_token.setEditable(flag_edit)

    def ui_valid_token(self, *a):
        """ Return true when token is used and shows Ok!
        """
        flag_token = len(self.get_input_token()) > 0
        self.btn_use.setEnabled(flag_token)
        # self.btn_clear_token.setEnabled(flag_token)
        idx = self.comboBox_token.currentIndex()
        flag = (
            idx != self.token_model.get_invalid_token_idx()
            and idx == self.token_model.get_used_token_idx()
        )
        txt = "Ok!" if flag else "Use"
        self.btn_use.setText(txt)
        return flag
