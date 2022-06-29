# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2021 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from .iml_token_info_dialog import NewIMLTokenInfoDialog, EditIMLTokenInfoDialog
from ..token_dialog import TokenDialog
from ..token_info_dialog import NewTokenInfoDialog, EditTokenInfoDialog
from ...models import API_TYPES


class IMLTokenDialog(TokenDialog):
    title = "Setup Credentials"
    message = ""

    def set_server(self, server):
        super().set_server(server)
        api_type = self.token_model.get_api_type()
        if api_type == API_TYPES.DATAHUB:
            self.NewInfoDialog = NewTokenInfoDialog
            self.EditInfoDialog = EditTokenInfoDialog
            self.token_info_keys = ["name", "token"]
            self.title = "Setup Data Hub Token"
            self.message = ""
        elif api_type == API_TYPES.PLATFORM:
            self.NewInfoDialog = NewIMLTokenInfoDialog
            self.EditInfoDialog = EditIMLTokenInfoDialog
            self.token_info_keys = ["name", "here_credentials", "user_login", "realm"]
            self.title = "Setup HERE Credentials"
            self.message = ""
        self.setWindowTitle(self.title)
        if self.message:
            self.label_msg.setText(self.message)
            self.label_msg.setVisible(True)
