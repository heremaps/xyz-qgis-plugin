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

from ...xyz_qgis.controller import make_qt_args
from ..space_info_dialog import EditSpaceDialog, NewSpaceDialog
from ..util_dialog import ConfirmDialog
from .space_ux import SpaceUX, SpaceConnectionInfo


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
        token = self.get_input_token()
        server = self.get_input_server()
        self.conn_info.set_(token=token, server=server)
        conn_info = SpaceConnectionInfo(self.conn_info)

        dialog = NewSpaceDialog(self)
        dialog.accepted.connect(lambda: self.signal_new_space.emit(
            make_qt_args(conn_info, dialog.get_space_info() )
        ))
        dialog.exec_()

    def ui_edit_space(self):
        token = self.get_input_token()
        server = self.get_input_server()
        index = self._get_current_index()
        space_id = self._get_space_model().get_("id",index)
        space_info = self._get_space_model().get_(dict,index)

        self.conn_info.set_(token=token, space_id=space_id, server=server)
        conn_info = SpaceConnectionInfo(self.conn_info)

        dialog = EditSpaceDialog(self)
        dialog.set_space_info(space_info)

        dialog.accepted.connect(lambda: self.signal_edit_space.emit(
            make_qt_args(conn_info, dialog.get_space_info() )
        ))
        dialog.exec_()

    def ui_del_space(self):
        token = self.get_input_token()
        server = self.get_input_server()
        index = self._get_current_index()
        space_id = self._get_space_model().get_("id",index)
        title = self._get_space_model().get_("title",index)
        
        self.conn_info.set_(token=token, space_id=space_id, server=server)
        
        dialog = ConfirmDialog("Do you want to Delete space: %s?"%title)
        ret = dialog.exec_()
        if ret != dialog.Ok: return
            
        conn_info = SpaceConnectionInfo(self.conn_info)
        self.signal_del_space.emit(make_qt_args(conn_info))
