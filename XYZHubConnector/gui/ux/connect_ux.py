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
from qgis.PyQt.QtGui import QRegExpValidator

from ...modules.controller import make_qt_args
from .space_ux import SpaceUX
from .ux import process_tags


class ConnectUX(SpaceUX):
    """ Dialog that contains table view of spaces + Token UX + Param input + Connect UX
    """
    title="Create a new XYZ Hub Connection"
    signal_space_connect = pyqtSignal(object)
    signal_space_bbox = pyqtSignal(object)
    def __init__(self, *a):
        # these are like abstract variables
        self.btn_bbox = None
        self.btn_load = None
        self.lineEdit_limit = None
        self.lineEdit_max_feat = None
        self.lineEdit_tags = None
        self.lineEdit_limit = None
    def config(self, *a):
        # super().config(*a)
        self.btn_bbox.setVisible(False)

        self.btn_load.clicked.connect(self.start_connect)
        self.btn_bbox.clicked.connect(self.start_bbox)

        self._set_mask_number(self.lineEdit_limit)
        self._set_mask_number(self.lineEdit_max_feat)
        self._set_mask_tags(self.lineEdit_tags)

        self.lineEdit_limit.setText("100")
        self.lineEdit_max_feat.setText("1000000")
    def get_params(self):
        key = ["tags","limit","max_feat"]
        val = [
            process_tags(self.lineEdit_tags.text().strip()),
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
        
    def ui_enable_ok_button(self, flag):
        for btn in [self.btn_load]:
            btn.setEnabled(flag)
            btn.clearFocus()
    
    def start_connect(self):
        index = self._get_current_index()
        meta = self._get_space_model().get_(dict, index)
        self.conn_info.set_(**meta, token=self.get_input_token())
        self.signal_space_connect.emit( make_qt_args(self.conn_info, meta, **self.get_params() ))
        # self.close()

    def start_bbox(self):
        index = self._get_current_index()
        meta = self._get_space_model().get_(dict, index)
        self.conn_info.set_(**meta, token=self.get_input_token())
        self.signal_space_bbox.emit( make_qt_args(self.conn_info, meta, **self.get_params() ))
        # self.close()
