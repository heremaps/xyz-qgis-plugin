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
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import QDialog

from . import get_ui_class
from .token_ux import TokenUX

from ..models import SpaceConnectionInfo
from ..modules.controller import make_qt_args

# EditSpaceLayerDialogUI and EditSpaceDialogUI: most of the components are same
EditSpaceDialogUI = get_ui_class("edit_space_dialog.ui")
# EditSpaceLayerDialogUI = get_ui_class("edit_space_layer_dialog.ui")
def copyright_from_txt(txt):
    return [dict(label=txt)] if len(txt) > 0 else None

def txt_from_copyright(obj):
    return obj[0].get("label") if isinstance(obj,list) and len(obj) > 0 else ""

class BaseSpaceInfoDialog(QDialog):
    title = "XYZ"

    def __init__(self, parent=None):
        """init window"""
        QDialog.__init__(self, parent)
        
        self.setWindowTitle(self.title)

    def get_space_info(self):
        d = {
            "title": self.lineEdit_title.text(),
            "id": self.lineEdit_id.text(),
            "description": self.plainTextEdit_description.toPlainText(),
            "shared": self.checkBox_shared.isChecked(),
            "license": self.comboBox_license.currentText() or None,
            "copyright": copyright_from_txt(self.lineEdit_copyright.text()),
            }
        return d

    def set_space_info(self, space_info):
        key_fun={
            "title": self.lineEdit_title.setText,
            "id": self.lineEdit_id.setText,
            "description": self.plainTextEdit_description.setPlainText,
            "shared": self.checkBox_shared.setChecked,
            "license": self.comboBox_license.setCurrentText,
            "copyright": lambda obj: self.lineEdit_copyright.setText( txt_from_copyright(obj)),
            }
        for k, fun in key_fun.items():
            if k in space_info:
                fun(space_info[k])
class SpaceInfoDialog(BaseSpaceInfoDialog, EditSpaceDialogUI):
    def __init__(self, *a):
        BaseSpaceInfoDialog.__init__(self,*a)
        EditSpaceDialogUI.setupUi(self,self)
        
        self.comboBox_license.addItems(
            sorted([
                "", "afl-3.0", "apache-2.0", "artistic-2.0",
                "bs1-1.0", "bsd-2-clause", "bsd-3-clause",
                "bsd-3-clause-clear", "cc", "cc0-1.0",
                "cc-by-4.0", "cc-by-sa-4.0", "wtfpl",
                "ecl-2.0", "epl-1.0", "eupl-1.1",
                "agpl-3.0", "gpl", "gpl-2.0", "gpl-3.0",
                "lgpl", "lgpl-2.1", "lgpl-3.0", "isc",
                "lppl-1.3c", "ms-pl", "mit", "mpl-2.0",
                "osl-3.0", "postgresql", "ofl-1.1",
                "ncsa", "unlicense", "zlib"
            ])
        )
class UploadNewSpaceDialog(SpaceInfoDialog, TokenUX):
    # ui = UP_CLASS()
    title = "Upload to new XYZ Geospace"
    signal_upload_new_space = pyqtSignal(object)

    def __init__(self, *a):
        SpaceInfoDialog.__init__(self,*a)
        
        self.groupBox_token.setEnabled(True)
        # self.used_token_idx = 0
        
        self.setWindowTitle(self.title)

    def config(self, token_model, network, vlayer):
        self.network = network
        self.vlayer = vlayer
        self.conn_info = SpaceConnectionInfo()

        self.config_ui_token(token_model)
        
        self.lineEdit_title.textChanged.connect(self.ui_valid_input)
        self.plainTextEdit_description.textChanged.connect(self.ui_valid_input)

        self.buttonBox.button(self.buttonBox.Ok).setText("Create and Upload")
        self.accepted.connect(self.start_upload)

    ########## COMBOBOX Config + Function

    def config_ui_token(self, token_model):
        TokenUX.config(self, token_model)

    def cb_set_valid_token(self, *a):
        self.insert_new_valid_token()
        self.ui_valid_input()

    def ui_enable_ok_button(self, flag):
        self.buttonBox.button(self.buttonBox.Ok).setEnabled(flag)
        self.buttonBox.button(self.buttonBox.Ok).clearFocus()

    # Check lineEdit as well
    def ui_valid_input(self, flag=None):
        ok = (
            self.ui_valid_token(flag) and 
            len(self.lineEdit_title.text()) and 
            len(self.plainTextEdit_description.toPlainText())
        )
            
        self.ui_enable_ok_button( ok)
        
    def start_upload(self):
        self.conn_info.set_(token=self.get_input_token())
        
        token = self.get_input_token()

        tags = self.lineEdit_tags.text().strip()
        kw = dict(tags=tags) if len(tags) else dict()

        self.signal_upload_new_space.emit(make_qt_args(self.conn_info, self.get_space_info(), self.vlayer, **kw))
        # self.network.add_space(token, self.get_space_info())

class EditSpaceDialog(SpaceInfoDialog):
    title = "Edit XYZ Geospace"

    def __init__(self, parent=None):
        SpaceInfoDialog.__init__(self, parent)
        
        self.groupBox_token.setVisible(False) # no groupBox_token
        self.groupBox_tags.setVisible(False) # no groupBox_tags

        self.setWindowTitle(self.title)
