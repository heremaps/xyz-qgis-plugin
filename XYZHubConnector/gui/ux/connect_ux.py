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
from qgis.PyQt.QtGui import QRegExpValidator, QIntValidator

from ...xyz_qgis.controller import make_qt_args
from ...xyz_qgis.models import LOADING_MODES
from ...xyz_qgis.models.filter_model import FilterModel
from ..filter_dialog import FilterDialog
from .space_ux import SpaceUX, SpaceConnectionInfo
from .ux import strip_list_string


class ConnectUX(SpaceUX):
    """ Dialog that contains table view of spaces + Token UX + Param input + Connect UX
    """
    title="XYZ Hub Connection"
    signal_space_connect = pyqtSignal(object)
    signal_space_bbox = pyqtSignal(object) # deprecate
    signal_space_tile = pyqtSignal(object)
    def __init__(self, *a):
        # these are like abstract variables
        self.radioButton_loading_live = None
        self.radioButton_loading_tile = None
        self.radioButton_loading_single = None
        self.btn_load = None
        self.btn_filter = None
        self.lineEdit_filter = None
        self.lineEdit_selection = None
        self.lineEdit_limit = None
        self.lineEdit_max_feat = None
        self.lineEdit_tags = None
        self.comboBox_similarity_threshold = None
    def config(self, *a):
        # super().config(*a)

        self.ui_enable_tile_mode(False)

        self.btn_load.clicked.connect(self.start_connect)
        self.radioButton_loading_single.toggled.connect(self.ui_enable_tile_mode)

        self.filter_dialog = FilterDialog(self)
        self.filter_dialog.config(FilterModel())
        self.btn_filter.clicked.connect(self.open_filter_dialog)
        
        self._set_mask_number(self.lineEdit_limit,0,100000)
        self._set_mask_number(self.lineEdit_max_feat)
        self._set_mask_tags(self.lineEdit_tags)

        self.radioButton_loading_tile.setChecked(True)
        self.lineEdit_limit.setText("100")
        self.lineEdit_max_feat.setText("1000000")

        for text, data in [
            ("single", 0),
            ("maximal", 100),
            ("balanced", 80),
        ]:
            self.comboBox_similarity_threshold.addItem(text,data)
        self.comboBox_similarity_threshold.setCurrentIndex(2)
        self.comboBox_similarity_threshold.setToolTip("\n".join([
            "Features with similar set of properties are merged into the same layer",
            " + balanced: features with similar properties are merged, balanced layers",
            " + maximal: no feature is merged, as many layers",
            " + single: all features are merged into 1 layer",
        ]))

        for btn, msg in zip([
            self.radioButton_loading_live, 
            self.radioButton_loading_tile, 
            self.radioButton_loading_single
        ],[
            "\n".join([
                "Live loading: Interactively refresh features in the current canvas. ",
                "Useful for visualizing and editing dynamic dataset"
            ]),
            "\n".join([
                "Incremental loading: Interactively refresh and cache features in the current canvas. ",
                "Useful for visualizing and exploring large dataset"
            ]),
            "\n".join([
                "Static loading: Load and cache all features in space. ",
                "Useful for importing and analysis of static dataset"
            ]),
        ]):
            btn.setToolTip(msg)
        self.lineEdit_max_feat.setToolTip("Maximum limit of features to be loaded")
        self.lineEdit_limit.setToolTip("Number of features loaded per request")
        self.lineEdit_selection.setToolTip("Load only the selected properties of features")
        self.btn_filter.setToolTip("Query features by property")
            
    def _get_loading_mode(self) -> str:
        for mode, box in zip(LOADING_MODES, [
            self.radioButton_loading_live, 
            self.radioButton_loading_tile, 
            self.radioButton_loading_single
        ]):
            if box.isChecked(): return mode
        return LOADING_MODES[0]

    def _get_filters(self):
        filters = self.filter_dialog.get_filters()
        for p in filters:
            p["values"] = strip_list_string(p["values"])
        return filters or None

    def get_params(self):
        key = ["tags","limit","max_feat","similarity_threshold","similarity_mode","loading_mode","selection","filters"]
        val = [
            strip_list_string(self.lineEdit_tags.text().strip()),
            self.lineEdit_limit.text().strip(),
            self.lineEdit_max_feat.text().strip(),
            self.comboBox_similarity_threshold.currentData(),
            self.comboBox_similarity_threshold.currentText(),
            self._get_loading_mode(),
            strip_list_string(self.lineEdit_selection.text().strip()),
            self._get_filters()
        ]
        fn = [str, int, int, int, str, str, str, list]
        return dict( 
            (k, f(v)) for k,v,f in zip(key,val,fn) if v is not None and len(str(v)) > 0
            )
    def _set_mask_number(self, lineEdit, lo:int=0, hi:int=None):
        validator = QIntValidator()
        validator.setBottom(lo)
        if hi: validator.setTop(hi)
        lineEdit.setValidator(validator)
    def _set_mask_tags(self, lineEdit):
        lineEdit.setValidator(QRegExpValidator(QRegExp("^\\b.*\\b$")))
        
    def ui_enable_ok_button(self, flag):
        for btn in [self.btn_load]:
            btn.setEnabled(flag)
            btn.clearFocus()
    def ui_enable_tile_mode(self, flag):
        self.lineEdit_max_feat.setEnabled( flag)

    def start_connect(self):
        index = self._get_current_index()
        meta = self._get_space_model().get_(dict, index)
        self.conn_info.set_(**meta, token=self.get_input_token(), server=self.get_input_server())
        conn_info = SpaceConnectionInfo(self.conn_info)
        self.signal_space_connect.emit( make_qt_args(conn_info, meta, **self.get_params() ))


        # if self.radioButton_loading_live.isChecked():
        #     self.signal_space_tile.emit( make_qt_args(conn_info, meta, **self.get_params() ))
        # else:
        #     self.signal_space_connect.emit( make_qt_args(conn_info, meta, **self.get_params() ))

        # self.close()

    def open_filter_dialog(self):
        ret = self.filter_dialog.exec_()
        if ret == self.filter_dialog.Accepted:
            self.lineEdit_filter.setText(self.filter_dialog.get_display_str())
        return ret
