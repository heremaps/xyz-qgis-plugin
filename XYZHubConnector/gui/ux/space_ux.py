# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


from qgis.PyQt.QtCore import QSortFilterProxyModel, pyqtSignal

from ...xyz_qgis.models import SpaceConnectionInfo, XYZSpaceModel
from ...xyz_qgis.controller import make_qt_args
from .token_ux import TokenUX

class SpaceUX(TokenUX):
    """ Base dialog that contains table view of spaces + Token UX
    """
    signal_space_count = pyqtSignal(object)
    
    def __init__(self):
        # these are like abstract variables
        self.tableView_space = None
        
    def config(self, token_model):
        
        space_model = XYZSpaceModel(self)

        proxy_model = QSortFilterProxyModel()
        proxy_model.setSourceModel(space_model)
        self.tableView_space.setModel( proxy_model)
        self.tableView_space.setSelectionMode(self.tableView_space.SingleSelection)
        self.tableView_space.setSelectionBehavior(self.tableView_space.SelectRows)
        self.tableView_space.setSortingEnabled(True)

        ############# connect gui
        self.tableView_space.pressed.connect(self.cb_table_row_selected)
        
        self.btn_use.clicked.connect(self._get_space_model().reset)
        TokenUX.config(self,token_model)

    def _get_proxy_model(self):
        return self.tableView_space.model()
    def _get_space_model(self):
        return self.tableView_space.model().sourceModel()
    def _get_current_index(self):
        index =  self.tableView_space.currentIndex()
        return self._get_proxy_model().mapToSource(index)
        
    def open_token_dialog(self):
        is_used_token_changed = super().open_token_dialog()
        if not is_used_token_changed: return

        self._get_space_model().reset()
        self.token_model.reset_used_token_idx()
        self.ui_valid_input()

    ##### CALLBACK
    def cb_table_row_selected(self, index):
        # pending token -> gui
        self.comboBox_token.setCurrentIndex(self.token_model.get_used_token_idx())
        self.ui_valid_input()

    def cb_display_spaces(self, obj, *a, **kw):
        # this function can be put into dialog
        # self.ui_valid_token()
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

    def ui_valid_input(self, *a):
        """ Returns true when token is succesfully connected and a space is selected
        also enables button if condition above is met.
        """
        ok = self.ui_valid_token() and self._get_current_index().isValid()
        self.ui_enable_ok_button(ok)
        return ok
    def ui_enable_ok_button(self, flag):
        raise NotImplementedError()
