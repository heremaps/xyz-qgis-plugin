# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

# from qgis.core import QgsSettings
from qgis.PyQt.QtWidgets import (QDialog)
from qgis.PyQt.QtGui import QRegExpValidator
from qgis.PyQt.QtCore import pyqtSignal, Qt, QRegExp, QSortFilterProxyModel
from ..models import XYZSpaceModel, SpaceConnectionInfo
from .space_info_dialog import EditSpaceDialog, NewSpaceDialog
from .util_dialog import ConfirmDialog
from .token_ux import TokenUX
from ..modules.controller import make_qt_args

from . import get_ui_class

ConnDialogUI = get_ui_class('new_connection_layer_dialog.ui')
class SpaceDialog(QDialog, ConnDialogUI, TokenUX):
    """ Base dialog that contains table view of spaces + Token UX
    """
    title="XYZ"
    
    signal_space_count = pyqtSignal(object)
    def __init__(self, parent=None):
        """init window"""
        QDialog.__init__(self, parent)
        ConnDialogUI.setupUi(self, self)
        self.setWindowTitle(self.title)

    def exec_(self):
        QDialog.exec_(self)
    def config_ui_token(self, token_model):
        TokenUX.config(self, token_model)

    def config(self, token_model, conn_info):
        
        self.conn_info = SpaceConnectionInfo()

        space_model = XYZSpaceModel(self)

        proxy_model = QSortFilterProxyModel()
        proxy_model.setSourceModel(space_model)
        self.tableView_space.setModel( proxy_model)
        self.tableView_space.setSelectionMode(self.tableView_space.SingleSelection)
        self.tableView_space.setSelectionBehavior(self.tableView_space.SelectRows)
        self.tableView_space.setSortingEnabled(True)

        ############# connect gui
        self.btn_use.clicked.connect(self._get_space_model().reset)
        
        self.config_ui_token( token_model)
        
        self.tableView_space.pressed.connect(self.cb_table_row_selected)
        

    def _get_proxy_model(self):
        return self.tableView_space.model()
    def _get_space_model(self):
        return self.tableView_space.model().sourceModel()
    def _get_current_index(self):
        index =  self.tableView_space.currentIndex()
        return self._get_proxy_model().mapToSource(index)
    ##### CALLBACK
    def cb_table_row_selected(self, index):
        # pending token -> gui
        self.comboBox_token.setCurrentIndex(self.used_token_idx)
        self.ui_valid_input()

    def cb_display_spaces(self, obj, *a, **kw):
        # this function can be put into dialog
        self.ui_valid_token()
        self.insert_new_valid_token()
        conn_info = SpaceConnectionInfo(self.conn_info)
        lst_id = self.ui_display_spaces(obj)
        if lst_id is not None:
            for space_id in lst_id:
                conn_info = SpaceConnectionInfo(conn_info)
                conn_info.set_(space_id=space_id)
                self.signal_space_count.emit( make_qt_args(conn_info))
    def cb_display_space_count(self, conn_info, obj):
        token, space_id = conn_info.get_xyz_space()
        if token != self.get_input_token(): return
        if obj["type"] == "StatisticsResponse":
            cnt = str(obj["count"]["value"])
        else:
            cnt = str(obj["count"])

        index = self._get_current_index()
        self._get_space_model().set_feat_count(space_id, cnt)
        self.tableView_space.setCurrentIndex(index)

    ###### UI function
    def ui_display_spaces(self, obj):
        return self._get_space_model().set_obj(obj)

    def ui_valid_input(self, flag=None):
        ok = self.ui_valid_token(flag) and self._get_current_index().isValid()
        self.ui_enable_ok_button(ok)
        return ok
    def ui_enable_ok_button(self, flag):
        self.buttonBox.button(self.buttonBox.Ok).setEnabled(flag)
        self.buttonBox.button(self.buttonBox.Ok).clearFocus()

class ConnectSpaceDialog(SpaceDialog):
    """ Dialog that contains table view of spaces + Token UX + Param input + Connect UX
    """
    title="Create a new XYZ Hub Connection"
    signal_space_connect = pyqtSignal(object)
    signal_space_bbox = pyqtSignal(object)
    def __init__(self, *a):
        SpaceDialog.__init__(self, *a)
        self.btn_bbox.setVisible(False)
    def config(self, *a):
        super().config(*a)

        self.buttonBox.button(self.buttonBox.Ok).setText("Connect")
        self.accepted.connect(self.start_connect)
        self.btn_bbox.clicked.connect(self.start_bbox)

        self._set_mask_number(self.lineEdit_limit)
        self._set_mask_number(self.lineEdit_max_feat)
        self._set_mask_tags(self.lineEdit_tags)

        self.lineEdit_limit.setText("100")
        self.lineEdit_max_feat.setText("1000000")
    def get_params(self):
        key = ["tags","limit","max_feat"]
        val = [
            self.lineEdit_tags.text().strip(),
            self.lineEdit_limit.text().strip(),
            self.lineEdit_max_feat.text().strip()
        ]
        fn = [str, int, int]
        return dict( 
            (k, f(v)) for k,v,f in zip(key,val,fn) if len(v) > 0
            )
    def _set_mask_number(self, lineEdit):
        lineEdit.setValidator(QRegExpValidator(QRegExp("[0-9]*")))
    def _set_mask_tags(self, lineEdit):
        lineEdit.setValidator(QRegExpValidator(QRegExp("^\\b.*\\b$")))
        
    def start_connect(self):
        index = self._get_current_index()
        meta = self._get_space_model().get_(dict, index)
        self.conn_info.set_(**meta, token=self.get_input_token())
        self.signal_space_connect.emit( make_qt_args(self.conn_info, meta, **self.get_params() ))

    def start_bbox(self):
        index = self._get_current_index()
        meta = self._get_space_model().get_(dict, index)
        self.conn_info.set_(**meta, token=self.get_input_token())
        self.signal_space_bbox.emit( make_qt_args(self.conn_info, meta, **self.get_params() ))
        # self.done(1)
        self.close()

class ConnectManageSpaceDialog(ConnectSpaceDialog):
    """ Dialog that contains table view of spaces + Token UX + Param input + Connect UX
    + Manage (New, Edit, Delete)
    """
    signal_new_space = pyqtSignal(object)
    signal_edit_space = pyqtSignal(object)
    signal_del_space = pyqtSignal(object)
    def config(self, *a):
        super().config(*a)

        self.btn_new.clicked.connect(self.ui_new_space)
        self.btn_edit.clicked.connect(self.ui_edit_space)
        self.btn_delete.clicked.connect(self.ui_del_space)

        self.groupBox_manage.setEnabled(False)
        self.checkBox_manage.stateChanged.connect(self.ui_enable_manage)
    def ui_valid_token(self, *a):
        flag = super().ui_valid_token()
        self.btn_new.setEnabled(flag)
        return flag

    def ui_enable_manage(self, check_state):
        self.groupBox_manage.setEnabled(check_state > 0)
    def ui_enable_ok_button(self, flag):
        super().ui_enable_ok_button(flag)
        self.btn_edit.setEnabled(flag)
        self.btn_delete.setEnabled(flag)
        
        self.btn_edit.clearFocus()
        self.btn_delete.clearFocus()
        
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
        
        self.conn_info.set_(token=token,space_id=space_id)
        
        dialog = ConfirmDialog("Do you want to Delete space ?")
        ret = dialog.exec_()
        if ret != dialog.Ok: return

        self.signal_del_space.emit(make_qt_args(self.conn_info))

class ConnectManageUploadSpaceDialog(ConnectManageSpaceDialog):
    title="XYZ Hub Connection"
    signal_upload_space = pyqtSignal(object)
    def config(self, *a):
        super().config(*a)
        self.vlayer = None
        
        self.btn_upload.clicked.connect(self.start_upload)
    def set_layer(self,vlayer):
        self.vlayer = vlayer
    def start_upload(self):
        index = self._get_current_index()
        meta = self._get_space_model().get_(dict, index)
        self.conn_info.set_(**meta, token=self.get_input_token())

        tags = self.lineEdit_tags.text().strip()
        kw = dict(tags=tags) if len(tags) else dict()

        dialog = ConfirmDialog("\n".join([
            "From Layer:\t%s",
            "To Space:\t%s",
            "Tags:\t\t%s",
            ]) % (self.vlayer.name(), meta["title"], tags),
            title="Confirm Upload"
        )
        ret = dialog.exec_()
        if ret != dialog.Ok: return

        self.signal_upload_space.emit(make_qt_args(self.conn_info, self.vlayer, **kw))
        self.close()
    def ui_enable_ok_button(self, flag):
        super().ui_enable_ok_button(flag)
        flag = flag and self.vlayer is not None
        self.btn_upload.setEnabled(flag)
        self.btn_upload.clearFocus()


# unused
class ManageSpaceDialog(SpaceDialog):
    title="Manage XYZ Space"

    
    signal_edit_space = pyqtSignal(object, object)
    signal_del_space = pyqtSignal(object)
    def __init__(self, *a):
        SpaceDialog.__init__(self, *a)
        self.mMapLayerComboBox.setEnabled(False)
    def config(self, *a):
        SpaceDialog.config(self, *a)
        
        self.btn_edit.clicked.connect(self.ui_edit_space)
        self.btn_delete.clicked.connect(self.ui_del_space)
        self.buttonBox.setVisible(False)
        
    def ui_enable_ok_button(self, flag):
        self.btn_edit.setEnabled(flag)
        self.btn_delete.setEnabled(flag)
        self.btn_edit.clearFocus()
        self.btn_delete.clearFocus()

    def ui_edit_space(self):
        token = self.get_input_token()
        index = self._get_current_index()
        space_id = self._get_space_model().get_("id",index)
        space_info = self._get_space_model().get_(dict,index)

        self.conn_info.set_(token=token,space_id=space_id)
        dialog = EditSpaceDialog(self)
        dialog.set_space_info(space_info)
        
        dialog.accepted.connect(lambda: self.signal_edit_space.emit(self.conn_info, dialog.get_space_info()))
        dialog.exec_()
    def ui_del_space(self):
        token = self.get_input_token()
        index = self._get_current_index()
        space_id = self._get_space_model().get_("id",index)
        
        self.conn_info.set_(token=token,space_id=space_id)

        dialog = ConfirmDialog("Do you want to Delete space ?")
        ret = dialog.exec_()
        if ret == dialog.Ok:
            self.signal_del_space.emit(self.conn_info)
        