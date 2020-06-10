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

from ...xyz_qgis.controller import make_qt_args
from .ux import UXDecorator

class BasemapUX(UXDecorator):
    signal_add_basemap = pyqtSignal(object)
    
    def __init__(self, *a):
        # these are like abstract variables
        self.comboBox_basemap = None
        self.lineEdit_app_id = None
        self.lineEdit_app_code = None
        self.btn_basemap = None

    def config_basemap(self, map_basemap_meta, auth):
        
        ############# connect gui
        self.lineEdit_app_id.textChanged.connect(self._basemap_ui_valid_input)
        self.lineEdit_app_code.textChanged.connect(self._basemap_ui_valid_input)
        self.btn_basemap.clicked.connect(self.add_basemap)
        
        ############# import basemap
        for k,v in map_basemap_meta.items():
            self.comboBox_basemap.addItem(k,v)
        self.lineEdit_app_id.setText( auth.get("app_id",""))
        self.lineEdit_app_code.setText( auth.get("app_code",""))

    def _get_basemap_meta(self):
        return self.comboBox_basemap.currentData()
    def add_basemap(self):
        meta=self._get_basemap_meta()
        app_id = self.lineEdit_app_id.text()
        app_code = self.lineEdit_app_code.text()
        self.signal_add_basemap.emit( make_qt_args(meta, app_id, app_code))
    ###### UI function
    def _basemap_ui_valid_input(self, flag=None):
        ok = len(self.lineEdit_app_id.text()) > 0 and len(self.lineEdit_app_code.text()) > 0 
        self._basemap_ui_enable_ok_button(ok)
        return ok
    def _basemap_ui_enable_ok_button(self, flag):
        self.btn_basemap.setEnabled(flag)
        self.btn_basemap.clearFocus()
