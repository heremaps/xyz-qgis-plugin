# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.PyQt.QtWidgets import QDialog

from . import get_ui_class
from ..xyz_qgis.models import SpaceConnectionInfo, XYZSpaceModel
from ..xyz_qgis.controller import make_qt_args
from .space_info_dialog import EditSpaceDialog, NewSpaceDialog
from .util_dialog import ConfirmDialog
from .ux import ConnectUX, ManageUX, SpaceUX, UploadUX, BasemapUX, SettingUX

ConnDialogUI = get_ui_class('tab_dialog.ui')

class MainDialog(QDialog, ConnDialogUI, ConnectUX, ManageUX, UploadUX, SpaceUX, BasemapUX, SettingUX):
    title="XYZ Hub Connection"
    def __init__(self, parent=None):
        """init window"""
        QDialog.__init__(self, parent)
        ConnDialogUI.setupUi(self, self)
        self.setWindowTitle(self.title)
    def config(self, *a):
        SpaceUX.config(self, *a)
        ConnectUX.config(self, *a)
        ManageUX.config(self, *a)
        UploadUX.config(self, *a)
        SettingUX.config(self, *a)
    def ui_enable_ok_button(self, *a):
        ConnectUX.ui_enable_ok_button(self,*a)
        ManageUX.ui_enable_ok_button(self,*a)
        UploadUX.ui_enable_ok_button(self,*a)
    def ui_valid_token(self, *a):
        flag = SpaceUX.ui_valid_token(self,*a)
        return ManageUX.ui_valid_token(self, flag)
