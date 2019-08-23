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

from ...modules.controller import make_qt_args
from .space_ux import SpaceUX, SpaceConnectionInfo
from .ux import process_tags


class ConnectUX(SpaceUX):
    """ Dialog that contains table view of spaces + Token UX + Param input + Connect UX
    """
    title="Create a new XYZ Hub Connection"
    signal_space_connect = pyqtSignal(object)
    signal_space_bbox = pyqtSignal(object) # deprecate
    signal_space_tile = pyqtSignal(object)
    def __init__(self, *a):
        # these are like abstract variables
        self.checkBox_tile = None
        self.btn_load = None
        self.lineEdit_limit = None
        self.lineEdit_max_feat = None
        self.lineEdit_tags = None
        self.comboBox_similarity_threshold = None
    def config(self, *a):
        # super().config(*a)

        self.btn_load.clicked.connect(self.start_connect)
        self.checkBox_tile.toggled.connect(self.ui_enable_tile_mode)

        self._set_mask_number(self.lineEdit_limit,0,100000)
        self._set_mask_number(self.lineEdit_max_feat)
        self._set_mask_tags(self.lineEdit_tags)

        self.checkBox_tile.setChecked(True)
        self.lineEdit_limit.setText("100")
        self.lineEdit_max_feat.setText("1000000")

        for text, data in [
            ("single", 0),
            ("maximal", 100),
            ("balanced", 80),
        ]:
            self.comboBox_similarity_threshold.addItem(text,data)
        self.comboBox_similarity_threshold.setCurrentIndex(2)

    def get_params(self):
        key = ["tags","limit","max_feat","similarity_threshold"]
        val = [
            process_tags(self.lineEdit_tags.text().strip()),
            self.lineEdit_limit.text().strip(),
            self.lineEdit_max_feat.text().strip(),
            self.comboBox_similarity_threshold.currentData()
        ]
        fn = [str, int, int, int]
        return dict( 
            (k, f(v)) for k,v,f in zip(key,val,fn) if len(str(v)) > 0
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
        self.lineEdit_max_feat.setEnabled(not flag) # disable

    def start_connect(self):
        index = self._get_current_index()
        meta = self._get_space_model().get_(dict, index)
        self.conn_info.set_(**meta, token=self.get_input_token())
        conn_info = SpaceConnectionInfo(self.conn_info)
        if self.checkBox_tile.isChecked():
            self.signal_space_tile.emit( make_qt_args(conn_info, meta, **self.get_params() ))
        else:
            self.signal_space_connect.emit( make_qt_args(conn_info, meta, **self.get_params() ))
        # self.close()

