# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


from qgis.PyQt.QtCore import QAbstractTableModel, Qt, QVariant
from .connection import parse_copyright


class QJsonTableModel(QAbstractTableModel):
    _header = list()

    def __init__(self, parent):
        super().__init__(parent)
        self.obj = list()
        self.header = self._header
        self.selected_index = None

    def rowCount(self, parent_idx):
        return len(self.obj)

    def columnCount(self, parent_idx):
        return len(self.header)

    def data(self, index, role):
        if role != Qt.DisplayRole:
            return QVariant()
        k = self.header[index.column()]
        row = self.obj[index.row()]
        v = row.get(k, "")
        if k == "copyright" and isinstance(v, list):
            v = "\n".join(parse_copyright(v))
        return QVariant(self._parse_string_or_number(v))

    def headerData(self, section, orientation, role):
        if role != Qt.DisplayRole:
            return QVariant()
        if orientation == Qt.Horizontal:
            return QVariant(self.header[section])
        else:
            return QVariant()

    # CUSTOM func

    def reset(self):
        self.set_obj(list())

    def set_obj(self, obj):
        self.beginResetModel()
        if len(obj) > 0:
            self.header = self._header + ([k for k in obj[0].keys() if k not in self._header])
        self.obj = obj
        self.endResetModel()

    def get_obj(self):
        return self.obj

    # Set/Get space selection (not needed anymore)
    def set_selected_index(self, index):
        self.selected_index = index

    def get_(self, key, index):
        if index is None or index.row() < 0:
            return dict() if key is dict else None
        row = self.obj[index.row()]
        return dict(row) if key is dict else row.get(key)

    def get_selected_space_info(self):
        return self.get_(dict, self.get_selected_index()) or dict()

    def get_selected_field(self, key):
        return self.get_(key, self.get_selected_index())

    def get_selected_index(self):
        return self.selected_index

    def _parse_string_or_number(self, v):
        v = str(v)
        try:
            v = int(v)
        except Exception as e:
            pass
        return v


class XYZSpaceModel(QJsonTableModel):
    HEADER_CNT = "feat_cnt"
    HEADER_RIGHT = "rights"
    HEADER_PROJECT = "project"
    HEADER_PROJECT_HRN = "project_hrn"
    HEADER_PROJECT_ITEM = "project_item"
    FIXED_HEADER_DATAHUB = [
        "id",
        "title",
        "description",
        HEADER_CNT,
        "license",
        "copyright",
        HEADER_RIGHT,
        "owner",
    ]
    FIXED_HEADER_PLATFORM = [
        "catalog",
        "id",
        "name",
        "description",
        "summary",
        HEADER_CNT,
        HEADER_PROJECT,
        HEADER_PROJECT_HRN,
        HEADER_PROJECT_ITEM,
    ]
    _header = FIXED_HEADER_DATAHUB

    def __init__(self, parent):
        super().__init__(parent)
        self.row_map = dict()  # space_id <-> row index
        self.row_reverse_map = dict()  # row index <-> space_id
        self.conn_info_map = dict()  # space_id <-> conn_info
        self.token = ""

    def get_(self, key, index):
        out = super().get_(key, index)
        if key is dict:
            out.pop(self.HEADER_CNT, None)
        return out

    def save_conn_info(self, conn_info, feat_cnt: int = None, project_hrn: str = None):
        idx = self._space_idx(conn_info.to_dict())
        if idx not in self.row_map:
            return
        irow = self.row_map[idx]
        self.conn_info_map[idx] = conn_info
        # update qt table
        if feat_cnt is not None:
            self.obj[irow][self.HEADER_CNT] = str(feat_cnt)
        project_hrn = project_hrn or conn_info.get_("project_hrn")
        if project_hrn:
            self.obj[irow][self.HEADER_PROJECT] = project_hrn.split("/")[-1]
            self.obj[irow][self.HEADER_PROJECT_HRN] = project_hrn
            self.obj[irow][self.HEADER_PROJECT_ITEM] = conn_info.get_("project_item")

    def refresh(self):
        self.beginResetModel()
        self.endResetModel()

    def get_conn_info(self, index):
        irow = index.row()
        idx = self.row_reverse_map.get(irow)
        if not idx:
            return
        return self.conn_info_map.get(idx)

    def _space_idx(self, obj):
        space_id = obj.get("id") or obj.get("space_id")
        return (
            space_id,
            obj.get("catalog_hrn"),
        )

    def set_obj(self, obj):
        super().set_obj(obj)
        self.row_map.clear()
        self.row_reverse_map.clear()
        self.conn_info_map.clear()
        for irow, s in enumerate(obj):
            idx = self._space_idx(s)
            self.row_map[idx] = irow
            self.row_reverse_map[irow] = idx

    def set_token(self, token):
        self.token = token

    def get_token(self):
        return self.token

    def set_fixed_header(self, headers):
        self._header = list(headers)
