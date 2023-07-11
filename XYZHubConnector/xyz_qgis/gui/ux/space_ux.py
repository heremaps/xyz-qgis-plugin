# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.PyQt.QtCore import QSortFilterProxyModel, pyqtSignal, Qt

from .token_server_ux import TokenWithServerUX
from ...models import SpaceConnectionInfo, XYZSpaceModel, API_TYPES
from ...controller import make_qt_args


class SpaceUX(TokenWithServerUX):
    """Base dialog that contains table view of spaces + Token UX"""

    signal_space_count = pyqtSignal(object)

    def __init__(self):
        # these are like abstract variables
        self.tableView_space = None

    def config(self, token_model, server_model):

        space_model = XYZSpaceModel(self)

        proxy_model = QSortFilterProxyModel()
        proxy_model.setSourceModel(space_model)
        proxy_model.setFilterKeyColumn(-1)
        self.tableView_space.setModel(proxy_model)
        self.tableView_space.setSelectionMode(self.tableView_space.SingleSelection)
        self.tableView_space.setSelectionBehavior(self.tableView_space.SelectRows)
        self.tableView_space.setSortingEnabled(True)

        # connect gui

        self.tableView_space.model().layoutAboutToBeChanged.connect(
            self.cb_refresh_model
        )  # cb for sort column
        self.tableView_space.selectionModel().currentChanged.connect(
            self.cb_table_row_selected, Qt.QueuedConnection
        )
        self.lineEdit_space_filter.valueChanged.connect(self.cb_space_filter_changed)
        self.checkBox_case_sensitive.toggled.connect(self.cb_case_sensitive_toggled)
        self.checkBox_case_sensitive.setChecked(False)
        self.cb_case_sensitive_toggled(False)

        TokenWithServerUX.config(self, token_model, server_model)

    def _get_proxy_model(self):
        return self.tableView_space.model()

    def _get_space_model(self):
        return self.tableView_space.model().sourceModel()

    def _get_source_index(self):
        index = self.tableView_space.currentIndex()
        return self._get_proxy_model().mapToSource(index)

    def _get_input_conn_info(self, with_meta=False, use_prior=False):
        index = self._get_source_index()
        conn_info = self._get_space_model().get_conn_info(index)
        if not conn_info:
            space_id = self._get_space_model().get_("id", index)
            catalog_hrn = self._get_space_model().get_("catalog_hrn", index)
            conn_info = (
                self._get_input_conn_info_without_id()
                if not use_prior
                else SpaceConnectionInfo(self.conn_info)
            )
            conn_info.set_(
                space_id=space_id,
                catalog_hrn=catalog_hrn,
            )
        if with_meta:
            meta = self._get_space_model().get_(dict, index)
            if meta:
                conn_info.set_(**meta)
        return conn_info

    def open_token_dialog(self):
        is_used_token_modified = super().open_token_dialog()
        if not is_used_token_modified:
            return

        self._get_space_model().reset()
        self.ui_valid_input()

    def open_server_dialog(self):
        is_used_token_modified = super().open_server_dialog()
        if not is_used_token_modified:
            return

        self._get_space_model().reset()
        self.ui_valid_input()

    # CALLBACK

    def cb_token_used(self, *a):
        self._get_space_model().reset()
        self.ui_valid_input()
        super().cb_token_used(*a)

    def cb_table_row_selected(self, idx, *a):
        # pending token -> gui
        # do not refresh model, otherwise make selected index invalid
        self.comboBox_token.setCurrentIndex(self.token_model.get_used_token_idx())
        self.ui_valid_input()

    def cb_refresh_model(self, *a):
        self._get_space_model().refresh()

    def cb_display_spaces(self, conn_info, obj, *a, **kw):
        # this function can be put into dialog
        # self.ui_valid_token()
        self.conn_info = SpaceConnectionInfo(conn_info)
        self.ui_display_spaces(obj)
        if obj is None:
            return
        lst_conn_info = list()
        for meta in obj:
            conn_info = SpaceConnectionInfo(self.conn_info)
            conn_info.set_(**meta)
            self._get_space_model().save_conn_info(conn_info)
            lst_conn_info.append(conn_info)
        self.cb_refresh_model()
        for conn_info in lst_conn_info:
            self.signal_space_count.emit(make_qt_args(conn_info))

    def cb_display_space_count(self, conn_info: SpaceConnectionInfo, obj):
        token, space_id = conn_info.get_xyz_space()
        here_credentials = conn_info.get_("here_credentials")
        server = conn_info.get_("server")
        user_login = conn_info.get_user_email()
        realm = conn_info.get_realm()
        if not (
            (server and server == self.get_input_server())
            and (
                (token and token == self.get_input_token())
                or (here_credentials and here_credentials == self.get_input_here_credentials())
                or (
                    user_login
                    and user_login == self.get_input_user_login()
                    and realm == self.get_input_realm()
                )
            )
        ):
            return
        if obj["type"] == "StatisticsResponse":
            cnt = obj["count"]["value"]
        else:
            cnt = obj["count"]

        self._get_space_model().save_conn_info(conn_info, feat_cnt=cnt)
        # self.cb_refresh_model() # disable for smoother ux
        index = self.tableView_space.currentIndex()
        if index.row() > -1:
            self.tableView_space.selectRow(index.row())

    def cb_comboBox_server_selected(self, index):
        super().cb_comboBox_server_selected(index)
        api_type = self.token_model.get_api_type()
        space_model = self._get_space_model()
        if api_type == API_TYPES.PLATFORM:
            header = space_model.FIXED_HEADER_PLATFORM
        else:
            header = space_model.FIXED_HEADER_DATAHUB
        space_model.set_fixed_header(header)
        space_model.reset()

    def cb_space_filter_changed(self, value):
        self._get_proxy_model().setFilterFixedString(value)
        self.tableView_space.selectionModel().clear()

    def cb_case_sensitive_toggled(self, flag):
        self._get_proxy_model().setFilterCaseSensitivity(flag)
        self.tableView_space.selectionModel().clear()

    # UI function
    def ui_display_spaces(self, obj):
        self._get_space_model().set_obj(obj)

    def ui_valid_input(self, *a):
        """Returns true when token is succesfully connected and a space is selected
        also enables button if condition above is met.
        """
        ok = self.ui_valid_token() and self._get_source_index().isValid()
        self.ui_enable_ok_button(ok)
        return ok

    def ui_enable_ok_button(self, flag):
        raise NotImplementedError()
