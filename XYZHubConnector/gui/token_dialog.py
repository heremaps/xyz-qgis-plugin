# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


from ..xyz_qgis.models.token_model import (
    TokenModel,
    ServerModel)
from .base_token_dialog import BaseTokenDialog
from .ux.server_ux import ServerUX


class TokenDialog(BaseTokenDialog, ServerUX):
    
    def __init__(self, parent=None):
        """init window"""
        super().__init__(parent)
        self.comboBox_server_url.setVisible(True)
        self.btn_server.setVisible(True)

    def exec_(self):
        self.comboBox_server_url.setCurrentIndex(self.get_active_server_idx())
        return super().exec_()

    def config(self, token_model: TokenModel):
        BaseTokenDialog.config(self, token_model)

    def config_server(self, server_model: ServerModel, comboBox_server_url):
        self.comboBox_server_url.currentIndexChanged[int].connect(comboBox_server_url.setCurrentIndex)
        ServerUX.config(self, server_model) # trigger outer server combo box first
        
        self.btn_server.clicked.connect(self.open_server_dialog)
        
    def cb_comboBox_server_selected(self, index):
        ServerUX.cb_comboBox_server_selected(self, index)
        self.tableView.selectRow(0)
        self.ui_enable_btn()
