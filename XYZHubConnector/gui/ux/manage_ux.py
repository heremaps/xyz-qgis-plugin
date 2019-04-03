# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.PyQt.QtCore import QRegExp, pyqtSignal

from ...modules.controller import make_qt_args
from ..space_info_dialog import EditSpaceDialog, NewSpaceDialog
from ..util_dialog import ConfirmDialog
from .space_ux import SpaceUX


class ManageUX(SpaceUX):
    """ Dialog that contains table view of spaces + Token UX + Param input + Connect UX
    + Manage (New, Edit, Delete)
    """
    signal_new_space = pyqtSignal(object)
    signal_edit_space = pyqtSignal(object)
    signal_del_space = pyqtSignal(object)
    
    def __init__(self, *a):
        # these are like abstract variables
        self.btn_new = None
        self.btn_edit = None
        self.btn_delete = None
        self.groupBox_manage = None
        self.checkBox_manage = None
    def config(self, *a):
        # super().config(*a)

        self.btn_new.clicked.connect(self.ui_new_space)
        self.btn_edit.clicked.connect(self.ui_edit_space)
        self.btn_delete.clicked.connect(self.ui_del_space)

        self.groupBox_manage.setEnabled(False)
        self.checkBox_manage.stateChanged.connect(self.ui_enable_manage)
    def ui_valid_token(self, flag):
        # flag = super().ui_valid_token()
        self.btn_new.setEnabled(flag)
        return flag
    def ui_enable_ok_button(self, flag):
        # super().ui_enable_ok_button(flag)
        self.btn_edit.setEnabled(flag)
        self.btn_delete.setEnabled(flag)
        
        self.btn_edit.clearFocus()
        self.btn_delete.clearFocus()

    def ui_enable_manage(self, check_state):
        self.groupBox_manage.setEnabled(check_state > 0)

    def _exec_info_dialog(self, dialog, signal, copy_space_info=False):
        token = self.get_input_token()
        index = self._get_current_index()
        space_id = self._get_space_model().get_("id",index)
        space_info = self._get_space_model().get_(dict,index)

        self.conn_info.set_(token=token,space_id=space_id)
        if copy_space_info:
            dialog.set_space_info(space_info)
        # dialog.accepted.connect(lambda: self.network.edit_space(token, space_id, dialog.get_space_info()))
        
        dialog.accepted.connect(lambda: signal.emit(
            make_qt_args(self.conn_info, dialog.get_space_info() )
        ))
        dialog.exec_()
    def ui_new_space(self):
        self._exec_info_dialog(
            NewSpaceDialog(self), 
            self.signal_new_space,
            copy_space_info=False
        )
    def ui_edit_space(self):
        self._exec_info_dialog(
            EditSpaceDialog(self), 
            self.signal_edit_space,
            copy_space_info=True
        )
    def ui_del_space(self):
        token = self.get_input_token()
        index = self._get_current_index()
        space_id = self._get_space_model().get_("id",index)
        title = self._get_space_model().get_("title",index)
        
        self.conn_info.set_(token=token,space_id=space_id)
        
        dialog = ConfirmDialog("Do you want to Delete space: %s?"%title)
        ret = dialog.exec_()
        if ret != dialog.Ok: return

        self.signal_del_space.emit(make_qt_args(self.conn_info))
