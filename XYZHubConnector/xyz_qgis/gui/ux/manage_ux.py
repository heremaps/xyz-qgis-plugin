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

from .space_ux import SpaceUX
from ..space_info_dialog import NewSpaceDialog, EditSpaceDialog
from ..iml.iml_space_info_dialog import IMLNewSpaceDialog, IMLEditSpaceDialog

from ..util_dialog import ConfirmDialog
from ...models import API_TYPES
from ...controller import make_qt_args


class ManageUX(SpaceUX):
    """Dialog that contains table view of spaces + Token UX + Param input + Connect UX
    + Manage (New, Edit, Delete)
    """

    signal_new_space = pyqtSignal(object)
    signal_edit_space = pyqtSignal(object)
    signal_del_space = pyqtSignal(object)

    def __init__(self, *a):
        SpaceUX.__init__(self, *a)
        # these are like abstract variables
        self.btn_new = None
        self.btn_edit = None
        self.btn_delete = None
        self.checkBox_manage = None

    def config(self, *a):
        # super().config(*a)

        self.btn_new.clicked.connect(self.ui_new_space)
        self.btn_edit.clicked.connect(self.ui_edit_space)
        self.btn_delete.clicked.connect(self.ui_del_space)

    def ui_valid_token(self, flag):
        # flag = super().ui_valid_token()
        self.btn_new.setEnabled(flag)
        self.btn_new.clearFocus()
        return flag

    def ui_enable_ok_button(self, flag):
        # super().ui_enable_ok_button(flag)
        self.btn_edit.setEnabled(flag)
        self.btn_delete.setEnabled(flag)

        self.btn_edit.clearFocus()
        self.btn_delete.clearFocus()

    def ui_new_space(self):
        conn_info = self._get_input_conn_info(use_prior=True)

        api_type = self.token_model.get_api_type()
        if api_type == API_TYPES.PLATFORM:
            dialog = IMLNewSpaceDialog(self)
            dialog.set_space_info({"catalog_hrn": conn_info.get_("catalog_hrn")})

        else:
            dialog = NewSpaceDialog(self)

        dialog.accepted.connect(
            lambda: self.signal_new_space.emit(
                make_qt_args(dialog.get_updated_conn_info(conn_info), dialog.get_space_info())
            )
        )
        dialog.exec_()

    def ui_edit_space(self):
        index = self._get_source_index()
        space_info = self._get_space_model().get_(dict, index)

        conn_info = self._get_input_conn_info()

        api_type = self.token_model.get_api_type()
        if api_type == API_TYPES.PLATFORM:
            dialog = IMLEditSpaceDialog(self)
        else:
            dialog = EditSpaceDialog(self)
        dialog.set_space_info(space_info)

        dialog.accepted.connect(
            lambda: self.signal_edit_space.emit(make_qt_args(conn_info, dialog.get_space_info()))
        )
        dialog.exec_()

    def ui_del_space(self):
        conn_info = self._get_input_conn_info()
        title = conn_info.get_name()
        dialog = ConfirmDialog("Do you want to Delete space: %s?" % title)
        ret = dialog.exec_()
        if ret != dialog.Ok:
            return

        self.signal_del_space.emit(make_qt_args(conn_info))
