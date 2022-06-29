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

from qgis.PyQt.QtWidgets import QDialog, QInputDialog

from . import get_ui_class

SUPPORTED_SPACE_LICENSES = [
    "afl-3.0",
    "apache-2.0",
    "artistic-2.0",
    "bs1-1.0",
    "bsd-2-clause",
    "bsd-3-clause",
    "bsd-3-clause-clear",
    "cc",
    "cc0-1.0",
    "cc-by-4.0",
    "cc-by-sa-4.0",
    "wtfpl",
    "ecl-2.0",
    "epl-1.0",
    "eupl-1.1",
    "agpl-3.0",
    "gpl",
    "gpl-2.0",
    "gpl-3.0",
    "lgpl",
    "lgpl-2.1",
    "lgpl-3.0",
    "isc",
    "lppl-1.3c",
    "ms-pl",
    "mit",
    "mpl-2.0",
    "osl-3.0",
    "postgresql",
    "ofl-1.1",
    "ncsa",
    "unlicense",
    "zlib",
]

EditSpaceDialogUI = get_ui_class("edit_space_dialog.ui")


def copyright_from_txt(txt):
    return [dict(label=txt)] if len(txt) > 0 else None


def txt_from_copyright(obj):
    return obj[0].get("label") if isinstance(obj, list) and len(obj) > 0 else ""


class SpaceInfoDialog(QDialog, EditSpaceDialogUI):
    title = "Dialog"
    _required_properties = ["title", "description"]

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self._config_ui()
        self._space_info = dict()

    def _config_ui(self):
        EditSpaceDialogUI.setupUi(self, self)
        self.setWindowTitle(self.title)
        self.comboBox_license.addItems([""] + list(sorted(SUPPORTED_SPACE_LICENSES)))

        self.lineEdit_title.textChanged.connect(self.ui_enable_btn)
        self.plainTextEdit_description.textChanged.connect(self.ui_enable_btn)
        self.btn_advanced.clicked.connect(self.update_space_info_json)
        self.ui_enable_btn()

    def get_space_info(self):
        d = self._get_space_info()
        return dict(self._space_info, **d)

    def set_space_info(self, space_info):
        self._space_info = dict(space_info)
        fn_mapping = self._get_space_info_fn_mapping()
        for k, fn in fn_mapping.items():
            v = space_info.get(k)
            if v is None:
                continue
            fn(v)

    def update_space_info_json(self):
        space_info = self.get_space_info()
        txt = json.dumps(space_info, indent=4)
        txt, ok = QInputDialog.getMultiLineText(
            None, "Edit Space JSON", "Only change this if you know what you're doing", txt
        )
        if ok:
            space_info = json.loads(txt)
            self.set_space_info(space_info)

    def ui_enable_btn(self):
        flag = self._is_valid_input()
        self.buttonBox.button(self.buttonBox.Ok).setEnabled(flag)
        self.buttonBox.button(self.buttonBox.Ok).clearFocus()

    def _is_valid_input(self):
        d = self._get_space_info()
        return all(d.get(k) for k in self._required_properties)

    def _get_space_info(self):
        return {
            "title": self.lineEdit_title.text().strip(),
            "id": self.lineEdit_id.text().strip(),
            "description": self.plainTextEdit_description.toPlainText().strip(),
            "shared": self.checkBox_shared.isChecked(),
            "license": self.comboBox_license.currentText() or None,
            "copyright": copyright_from_txt(self.lineEdit_copyright.text().strip()),
        }

    def _get_space_info_fn_mapping(self):
        return {
            "title": self.lineEdit_title.setText,
            "id": self.lineEdit_id.setText,
            "description": self.plainTextEdit_description.setPlainText,
            "shared": self.checkBox_shared.setChecked,
            "license": self.comboBox_license.setCurrentText,
            "copyright": lambda obj: self.lineEdit_copyright.setText(txt_from_copyright(obj)),
        }


class NewSpaceDialog(SpaceInfoDialog):
    title = "Create New HERE Space"


class EditSpaceDialog(SpaceInfoDialog):
    title = "Edit HERE Space"
