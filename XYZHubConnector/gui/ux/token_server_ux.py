# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


from .token_ux import TokenUX
from .server_ux import ServerUX


class TokenWithServerUX(TokenUX, ServerUX):
    """ UX for Token comboBox with token button, use token button, connection info,
    combine with Server comboBox
    """
    def __init__(self):
        TokenUX.__init__(self)
        ServerUX.__init__(self)

    def config(self, token_model, server_model):
        ServerUX.config(self, server_model) # config server first
        TokenUX.config(self, token_model)

        self.token_dialog.config_server(server_model, self.comboBox_server_url)

        # explicitly init ui
        self.comboBox_server_url.setCurrentIndex(-1)
        self.comboBox_server_url.setCurrentIndex(0) 
        self.comboBox_token.setCurrentIndex(0)
        self.ui_valid_input() # valid_input initially (explicit)

    def cb_enable_token_ui(self,flag=True):
        TokenUX.cb_enable_token_ui(self, flag)
        self.comboBox_server_url.setEnabled(flag)
        
    def open_token_dialog(self):
        server_idx = self.comboBox_server_url.currentIndex()
        self.token_dialog.set_active_server_idx(server_idx)
        return super().open_token_dialog()
        
    def set_server(self,server):
        """ Server change triggered token_model change
        """
        self.conn_info.set_server(server)
        self.token_model.set_server(server)

    def get_input_server(self):
        return ServerUX.get_input_server(self)
