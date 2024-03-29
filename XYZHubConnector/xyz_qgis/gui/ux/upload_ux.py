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
from qgis.core import QgsMapLayerProxyModel

from .space_ux import SpaceUX
from .ux import strip_list_string
from ..util_dialog import ConfirmDialog
from ...controller import make_qt_args


class UploadUX(SpaceUX):
    title = "XYZ Hub Connection"
    signal_upload_space = pyqtSignal(object)

    def __init__(self, *a):
        SpaceUX.__init__(self, *a)
        # these are like abstract variables
        self.btn_upload = None
        self.lineEdit_tags_upload = None
        self.mMapLayerComboBox = None
        self.vlayer = None

    def config(self, *a):
        # super().config(*a)
        self.vlayer = None
        self.btn_upload.clicked.connect(self.start_upload)
        self._set_mask_tags(self.lineEdit_tags_upload)

        # https://qgis.org/api/classQgsMapLayerProxyModel.html
        filters = QgsMapLayerProxyModel.VectorLayer  # use &, |, ~ to set/unset flag, enum
        self.mMapLayerComboBox.setFilters(filters)
        self.mMapLayerComboBox.layerChanged.connect(self._set_layer)

    def set_layer(self, vlayer):
        self.mMapLayerComboBox.setLayer(vlayer)
        self._set_layer(vlayer)

    def _set_layer(self, vlayer):
        self.vlayer = vlayer

    def _set_mask_tags(self, lineEdit):
        lineEdit.setValidator(QRegExpValidator(QRegExp("^\\b.*\\b$")))

    def start_upload(self):
        conn_info = self._get_input_conn_info(with_meta=True)

        tags = strip_list_string(self.lineEdit_tags_upload.text().strip())
        kw = dict(tags=tags) if len(tags) else dict()
        space_name = conn_info.get_name()
        dialog = ConfirmDialog(
            "\n".join(
                [
                    "Attribute and geometry type are adjusted after data is loaded into QGIS.",
                    "Uploaded data might have different geojson format than expected !\n",
                    "From Layer:\t%s",
                    "To Space:  \t%s",
                    "Tags:      \t%s",
                ]
            )
            % (self.vlayer.name(), space_name, tags),
            title="Confirm Upload",
        )
        ret = dialog.exec_()
        if ret != dialog.Ok:
            return
        self.signal_upload_space.emit(make_qt_args(conn_info, self.vlayer, **kw))
        # self.close()

    def ui_enable_ok_button(self, flag):
        # super().ui_enable_ok_button(flag)
        flag = flag and self.vlayer is not None
        self.btn_upload.setEnabled(flag)
        self.btn_upload.clearFocus()
