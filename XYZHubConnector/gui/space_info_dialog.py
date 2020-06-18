# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import json

# from qgis.core import QgsSettings
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import QDialog, QInputDialog

from . import get_ui_class
# from .token_ux import TokenUX

from ..xyz_qgis.models import SpaceConnectionInfo
from ..xyz_qgis.controller import make_qt_args

SUPPORTED_SPACE_LICENSES = [
    "afl-3.0", "apache-2.0", "artistic-2.0",
    "bs1-1.0", "bsd-2-clause", "bsd-3-clause",
    "bsd-3-clause-clear", "cc", "cc0-1.0",
    "cc-by-4.0", "cc-by-sa-4.0", "wtfpl",
    "ecl-2.0", "epl-1.0", "eupl-1.1",
    "agpl-3.0", "gpl", "gpl-2.0", "gpl-3.0",
    "lgpl", "lgpl-2.1", "lgpl-3.0", "isc",
    "lppl-1.3c", "ms-pl", "mit", "mpl-2.0",
    "osl-3.0", "postgresql", "ofl-1.1",
    "ncsa", "unlicense", "zlib"
]

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
        self._space_info = dict()
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
        return d if not self._space_info else self._space_info

    def set_space_info(self, space_info):
        self._space_info = dict(space_info)
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

class SpaceInfoTokenDialog(BaseSpaceInfoDialog, EditSpaceDialogUI):
    def __init__(self, *a):
        BaseSpaceInfoDialog.__init__(self,*a)
        EditSpaceDialogUI.setupUi(self,self)
        
        self.comboBox_license.addItems([""] + list(sorted(SUPPORTED_SPACE_LICENSES)))
        self.lineEdit_title.textChanged.connect(self.ui_enable_btn)
        self.plainTextEdit_description.textChanged.connect(self.ui_enable_btn)
        self.ui_enable_btn()
    def ui_enable_btn(self):
        flag = all([
            self.lineEdit_title.text().strip(),
            self.plainTextEdit_description.toPlainText()
            ])
        self.buttonBox.button(self.buttonBox.Ok).setEnabled(flag)
        self.buttonBox.button(self.buttonBox.Ok).clearFocus()

        
class SpaceInfoDialog(SpaceInfoTokenDialog):
    def __init__(self, parent=None):
        SpaceInfoTokenDialog.__init__(self, parent)
        
        self.groupBox_token.setVisible(False) # no groupBox_token
        self.groupBox_tags.setVisible(False) # no groupBox_tags

        self.btn_advanced.clicked.connect(self.update_space_info_json)
        self.setWindowTitle(self.title)
        
    def update_space_info_json(self):
        # dialog = PlainTextDialog("")
        space_info = self.get_space_info()
        txt = json.dumps(space_info,indent=4)
        txt, ok = QInputDialog.getMultiLineText(None, "Edit Space JSON", "Only change this if you know what you're doing", txt)
        if ok:
            space_info = json.loads(txt)
            self.set_space_info(space_info)
        
class NewSpaceDialog(SpaceInfoDialog):
    title = "Create New XYZ Hub Space"
class EditSpaceDialog(SpaceInfoDialog):
    title = "Edit XYZ Hub Space"
