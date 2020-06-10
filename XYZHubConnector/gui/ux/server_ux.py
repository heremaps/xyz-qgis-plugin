# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


from ...xyz_qgis.models.token_model import (
    ComboBoxProxyModel, TokenModel,
    ServerModel)
from ..server_dialog import ServerDialog
from .ux import UXDecorator


class ServerUX(UXDecorator):
    """ UX for Server ComboBox
    """
    
    def __init__(self):
        # these are like abstract variables
        self.comboBox_server_url = None

    def config(self, server_model):
        self.server_model = server_model

        proxy_server_model = ComboBoxProxyModel(token_key="server", nonamed_token="")
        proxy_server_model.setSourceModel( server_model)
        proxy_server_model.set_keys(server_model.INFO_KEYS)
        
        self.comboBox_server_url.setModel( proxy_server_model)
        self.comboBox_server_url.setInsertPolicy(self.comboBox_server_url.NoInsert)
        self.comboBox_server_url.setDuplicatesEnabled(False)
        
        self.comboBox_server_url.currentIndexChanged[int].connect(self.cb_comboBox_server_selected)
        self.comboBox_server_url.currentIndexChanged[int].connect(self.ui_valid_input)

        self.server_dialog = ServerDialog(self)
        self.server_dialog.config(server_model)
        
    def open_server_dialog(self):
        idx = self.comboBox_server_url.currentIndex()
        self.server_dialog.set_active_idx(idx)
        self.server_dialog.exec_()
        idx = self.server_dialog.get_active_idx()
        self.comboBox_server_url.setCurrentIndex(idx)
        return self.server_model.is_used_token_modified()

    def cb_comboBox_server_selected(self, index):
        if index < 0: return
        server = self.comboBox_server_url.model().get_token(index)
        self.set_server(server)
        
    def set_server(self,server):
        pass

    def get_input_server(self):
        proxy_server_model = self.comboBox_server_url.model()
        return proxy_server_model.get_token(self.comboBox_server_url.currentIndex())

    def ui_valid_input(self, *a):
        return self.comboBox_server_url.currentIndex() > -1
