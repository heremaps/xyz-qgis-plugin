# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2020 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from .base_token_dialog import BaseTokenDialog
from .iml.iml_token_info_dialog import NewIMLServerInfoDialog, EditIMLServerInfoDialog
from .token_info_dialog import EditServerInfoDialog, NewServerInfoDialog


class ServerDialog(BaseTokenDialog):
    title = "Setup HERE Server"
    message = ""
    token_info_keys = ["name", "server"]
    NewInfoDialog = NewIMLServerInfoDialog
    EditInfoDialog = EditIMLServerInfoDialog
    
    def _make_delete_message(self, token_info):
        token_msg = ", ".join("%s: %s"%it for it in token_info.items())
        return "Do you want to Delete server (%s)?"%token_msg
