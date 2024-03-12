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

from .. import get_ui_class
from ...iml.network.network import IMLNetworkManager

LAYER_TYPES = [
    "interactivemap",
]

EditSpaceDialogUI = get_ui_class("edit_iml_space_dialog.ui")


class IMLSpaceInfoDialog(QDialog, EditSpaceDialogUI):
    title = "Dialog"
    _required_properties = ["id", "name", "summary", "description", "layerType", "catalog_hrn"]

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self._config_ui()
        self._space_info = dict()

    def _config_ui(self):
        EditSpaceDialogUI.setupUi(self, self)
        self.setWindowTitle(self.title)
        self.comboBox_layer_type.addItems(LAYER_TYPES)

        self.comboBox_layer_type.currentIndexChanged[int].connect(self.ui_enable_btn)
        self.lineEdit_catalog_hrn.textChanged.connect(self.ui_enable_btn)
        self.lineEdit_id.textChanged.connect(self.ui_enable_btn)
        self.lineEdit_title.textChanged.connect(self.ui_enable_btn)
        self.lineEdit_tags.textChanged.connect(self.ui_enable_btn)
        self.lineEdit_billing_tags.textChanged.connect(self.ui_enable_btn)
        self.plainTextEdit_description.textChanged.connect(self.ui_enable_btn)
        self.plainTextEdit_summary.textChanged.connect(self.ui_enable_btn)
        self.btn_advanced.clicked.connect(self.update_space_info_json)
        self.ui_enable_btn()

    def get_space_info(self):
        d = {k: v for k, v in self._get_space_info().items() if v is not None}
        d = dict(self._space_info, **d)
        d = IMLNetworkManager.trim_payload(d, "edit_layer")
        return d

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

    def ui_enable_btn(self, *a):
        flag = self._is_valid_input()
        self.buttonBox.button(self.buttonBox.Ok).setEnabled(flag)
        self.buttonBox.button(self.buttonBox.Ok).clearFocus()

    def _is_valid_input(self):
        d = self._get_space_info()
        return all(d.get(k) for k in self._required_properties)

    def _txt_to_list(self, txt: str, delim=","):
        if not txt.strip():
            return None
        return [s.strip() for s in txt.strip().split(delim)]

    def _list_to_txt(self, lst: list, delim=","):
        return delim.join(str(s) for s in lst)

    def _get_space_info(self):
        return {
            "layerType": self.comboBox_layer_type.currentText(),
            "catalog_hrn": self.lineEdit_catalog_hrn.text().strip(),
            "name": self.lineEdit_title.text().strip(),
            "id": self.lineEdit_id.text().strip(),
            "summary": self.plainTextEdit_summary.toPlainText().strip(),
            "description": self.plainTextEdit_description.toPlainText().strip(),
            "tags": self._txt_to_list(self.lineEdit_tags.text()),
            "billingTags": self._txt_to_list(self.lineEdit_billing_tags.text()),
        }

    def _get_space_info_fn_mapping(self):
        return {
            "layerType": self.comboBox_layer_type.setCurrentText,
            "catalog_hrn": self.lineEdit_catalog_hrn.setText,
            "name": self.lineEdit_title.setText,
            "id": self.lineEdit_id.setText,
            "summary": self.plainTextEdit_summary.setPlainText,
            "description": self.plainTextEdit_description.setPlainText,
            "tags": lambda obj: self.lineEdit_tags.setText(self._list_to_txt(obj)),
            "billingTags": lambda obj: self.lineEdit_billing_tags.setText(self._list_to_txt(obj)),
        }

    def get_updated_conn_info(self, conn_info):
        conn_info.set_(catalog_hrn=self._get_space_info().get("catalog_hrn"))
        return conn_info


class IMLNewSpaceDialog(IMLSpaceInfoDialog):
    title = "Create New HERE Layer"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lineEdit_catalog_hrn.setEnabled(True)
        self.lineEdit_id.setEnabled(True)


class IMLEditSpaceDialog(IMLSpaceInfoDialog):
    title = "Edit HERE Layer"
