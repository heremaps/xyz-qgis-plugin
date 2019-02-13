# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
#
###############################################################################


from qgis.PyQt.QtCore import QAbstractTableModel, Qt, QVariant
def parse_copyright(v):
    if not isinstance(v, list): return v
    lst = [
        ". ".join(el[j] for j in ["label","alt"] if j in el)
        for el in v
    ]
    return lst
        
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
            v = "\n".join( parse_copyright(v))
        return QVariant(str(v))
    def headerData(self, section, orientation, role):
        if role != Qt.DisplayRole:
            return QVariant()
        if orientation == Qt.Horizontal:
            return QVariant(self.header[section])
        else:
            return QVariant()

    #### CUSTOM func

    def reset(self):
        self.set_obj(list())
    def set_obj(self, obj):
        self.beginResetModel()
        if len(obj) > 0:
            self.header = self._header + ([k for k in obj[0].keys() if k not in self._header])
        self.obj = obj
        self.endResetModel()


    #### Set/Get space selection (not needed anymore)
    def set_selected_index(self, index):
        self.selected_index = index

    def get_(self, key, index):
        if index is None: return None
        row = self.obj[index.row()]
        if key is dict: return row
        else: return row.get(key)
    def get_selected_space_info(self):
        return self.get_(dict, self.get_selected_index()) or dict()
    def get_selected_field(self, key):
        return self.get_(key, self.get_selected_index())
    def get_selected_index(self):
        return self.selected_index

class XYZSpaceModel(QJsonTableModel):
    HEADER_CNT = "feat_cnt"
    HEADER_RIGHT = "rights"
    _header = ["id", "title","description",HEADER_CNT,"license","copyright", HEADER_RIGHT,"owner"]
    def __init__(self, parent):
        super().__init__(parent)
        self.space_map = dict() # space_id <-> index
        self.token = ""
    def set_feat_count (self, space_id, cnt):
        key = self.HEADER_CNT
        if space_id not in self.space_map: return
        irow = self.space_map[space_id]
        self.beginResetModel()
        self.obj[irow][key] = cnt
        self.endResetModel()
    def set_obj(self, obj):
        super().set_obj(obj)
        self.space_map = dict()
        for i, s in enumerate(obj):
            self.space_map[s["id"]] = i
        return self.space_map.keys()
        
    def set_token(self, token):
        self.token = token
    def get_token(self):
        # print("space_model.get_token()")
        return self.token
