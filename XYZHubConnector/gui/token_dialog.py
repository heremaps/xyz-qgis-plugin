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

from ..xyz_qgis.models.token_model import GroupTokenInfoModel
from .util_dialog import ConfirmDialog
from .token_info_dialog import NewTokenInfoDialog, EditTokenInfoDialog
from qgis.PyQt.QtGui import QStandardItem

TokenUI = get_ui_class('token_dialog.ui')

class TokenDialog(QDialog, TokenUI):
    title="Token Manager"
    def __init__(self, parent=None):
        """init window"""
        QDialog.__init__(self, parent)
        TokenUI.setupUi(self, self)
        self.setWindowTitle(self.title)

        self.is_used_token_changed = False
        self.current_idx = -1
    def config(self, token_model: GroupTokenInfoModel):
        
        self.token_model = token_model

        self.tableView.setModel( token_model)
        self.tableView.setSelectionMode(self.tableView.SingleSelection)
        self.tableView.setSelectionBehavior(self.tableView.SelectRows)
        self.tableView.setEditTriggers(self.tableView.NoEditTriggers)


        # dont use pressed, activated
        self.tableView.selectionModel().currentChanged.connect(self.ui_enable_btn)

        self.btn_add.clicked.connect( self.ui_add_token)
        self.btn_edit.clicked.connect( self.ui_edit_token)
        self.btn_delete.clicked.connect( self.ui_delete_token)
        self.btn_up.clicked.connect( self.ui_move_token_up)
        self.btn_down.clicked.connect( self.ui_move_token_down)

        self.accepted.connect( token_model.cb_write_token)
        self.rejected.connect( token_model.cb_refresh_token)
        
    def exec_(self):
        # self.tableView.resizeColumnsToContents()
        # self.tableView.clearFocus()
        self.tableView.selectRow(self.current_idx)
        self.ui_enable_btn()
        self.is_used_token_changed = False
        ret = super().exec_()
        if ret == self.Accepted:
            self.is_used_token_changed = True
            idx = self.tableView.currentIndex().row()
            self.set_current_idx(idx)
        return ret
    def set_current_idx(self,idx):
        self.current_idx = idx
    def ui_enable_btn(self, *a):
        index = self.tableView.currentIndex()
        flag = index.isValid()
        for btn in [
            self.btn_edit,
            self.btn_delete,
            self.btn_up,
            self.btn_down,
        ]:
            btn.setEnabled(flag)

    def _get_current_token_info(self):
        row = self.tableView.currentIndex().row()
        return self.token_model.get_token_info(row)

    def ui_add_token(self):
        dialog = NewTokenInfoDialog(self)
        dialog.accepted.connect(lambda: self._add_token(
            dialog.get_token_info()
        ))
        dialog.exec_()

    def ui_edit_token(self):
        dialog = EditTokenInfoDialog(self)
        token_info = self._get_current_token_info()
        dialog.set_token_info(token_info)
        dialog.accepted.connect(lambda: self._edit_token(
            dialog.get_token_info()
        ))
        dialog.exec_()

    def ui_delete_token(self):
        row = self.tableView.currentIndex().row()
        token_info = self.token_model.get_token_info(row)
        token_msg = ", ".join("%s: %s"%it for it in token_info.items())
        dialog = ConfirmDialog("Do you want to Delete token (%s)?"%token_msg)
        ret = dialog.exec_()
        if ret != dialog.Ok: return

        self.token_model.takeRow(row)
        self.check_used_token_changed(row)

    def ui_move_token_up(self):
        row = self.tableView.currentIndex().row()
        it = self.token_model.takeRow(row)
        self.check_used_token_changed(row)

        row = max(row-1,0)
        self.token_model.insertRow(max(row,0), it)
        self.tableView.selectRow(row)
        self.check_used_token_changed(row)

    def ui_move_token_down(self):
        row = self.tableView.currentIndex().row()
        it = self.token_model.takeRow(row)
        self.check_used_token_changed(row)

        row = min(row+1, self.token_model.rowCount())
        self.token_model.insertRow(row, it)
        self.tableView.selectRow(row)
        self.check_used_token_changed(row)

    def _add_token(self, token_info: dict):
        self.token_model.appendRow([
            QStandardItem(token_info[k])
            for k in ["name", "token"]
        ])
    
    def _edit_token(self, token_info: dict):
        row = self.tableView.currentIndex().row()
        self.token_model.insertRow(row+1, [
            QStandardItem(token_info[k])
            for k in ["name", "token"]
        ])
        it = self.token_model.takeRow(row)
        self.check_used_token_changed(row)
        
    def check_used_token_changed(self, idx):
        flag = idx == self.token_model.get_used_token_idx()
        self.is_used_token_changed = self.is_used_token_changed or flag
