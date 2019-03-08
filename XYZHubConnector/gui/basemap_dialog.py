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
from qgis.PyQt.QtWidgets import QDialog

from . import get_ui_class
from ..modules import basemap
from ..modules.controller import make_qt_args

BaseMapDialogUI = get_ui_class('basemap_dialog.ui')
class BaseMapDialog(QDialog, BaseMapDialogUI):
    signal_add_basemap = pyqtSignal(object)

    def __init__(self, parent=None):
        """init window"""
        QDialog.__init__(self, parent)
        BaseMapDialogUI.setupUi(self, self)

    def config(self, map_basemap_meta, auth):
        for k,v in map_basemap_meta.items():
            self.comboBox_basemap.addItem(k,v)
        self.lineEdit_app_id.setText( auth.get("app_id",""))
        self.lineEdit_app_code.setText( auth.get("app_code",""))
        
        ############# connect gui
        self.lineEdit_app_id.textChanged.connect(self.ui_valid_input)
        self.lineEdit_app_code.textChanged.connect(self.ui_valid_input)
        self.accepted.connect(self.add_basemap)
        
        self.ui_valid_input()
    def _get_basemap_meta(self):
        return self.comboBox_basemap.currentData()
    def add_basemap(self):
        meta=self._get_basemap_meta()
        app_id = self.lineEdit_app_id.text()
        app_code = self.lineEdit_app_code.text()
        self.signal_add_basemap.emit( make_qt_args(meta, app_id, app_code))
    ###### UI function
    def ui_valid_input(self, flag=None):
        ok = len(self.lineEdit_app_id.text()) > 0 and len(self.lineEdit_app_code.text()) > 0 
        self.ui_enable_ok_button(ok)
        return ok
    def ui_enable_ok_button(self, flag):
        self.buttonBox.button(self.buttonBox.Ok).setEnabled(flag)
        self.buttonBox.button(self.buttonBox.Ok).clearFocus()
