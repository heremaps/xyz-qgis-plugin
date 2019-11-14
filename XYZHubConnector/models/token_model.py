# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem
from qgis.PyQt.QtCore import QIdentityProxyModel, Qt, QVariant

class UsedToken():
    def __init__(self):
        self.set_invalid_token_idx(0)
    def set_invalid_token_idx(self, invalid_idx):
        self.invalid_idx = invalid_idx
        self.reset_used_token_idx()
    def get_invalid_token_idx(self):
        return self.invalid_idx
    def set_used_token_idx(self, idx):
        self.used_token_idx = idx
    def get_used_token_idx(self):
        return self.used_token_idx
    def reset_used_token_idx(self):
        self.used_token_idx = self.invalid_idx

class TokenModel(QStandardItemModel, UsedToken):
    """ Simple version of token model, in sync with a simple line config file
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        UsedToken.__init__(self)
        self.ini = ""
        self._config_callback() # persistant_cange (Experimental)
    def load_ini(self, ini):
        self._load_ini(ini)
        self.ini = ini # must be after loaded
        self._refresh_token()
        
    def get_ini(self):
        return self.ini
    
    def _refresh_token(self):
        pass

    def _load_ini(self, ini):
        it = self.invisibleRootItem()
        it.appendRow(QStandardItem())
        with open(ini) as f:
            it.appendRows([
                QStandardItem(line.strip()) for line in f.readlines()
                if len(line.strip()) > 0
                ])
    def _config_callback(self):
        try: self.rowsInserted.disconnect()
        except TypeError: pass
        try: self.rowsAboutToBeRemoved.disconnect()
        except TypeError: pass

        self.rowsInserted.connect(self._cb_append_token_to_file)

        # persistent remove (uncomment next line)
        self.rowsAboutToBeRemoved.connect(self._cb_remove_token_from_file)
    def _cb_remove_token_from_file(self, root, i0, i1):
        if self.ini == ""  or not self._is_valid_single_selection(i0, i1): return # do not write multiple added items appendRows
        token = self.item(i0).text()
        with open(self.ini,"r+") as f:
            new_lines = [line for line in f.readlines() if not token == line.strip() and len(line.strip()) > 0] # remove blackline as well
            f.seek(0)
            f.writelines(new_lines)
            f.truncate()
    def _cb_append_token_to_file(self, root, i0, i1):
        if self.ini == ""  or not self._is_valid_single_selection(i0, i1): return # do not write multiple added items appendRows
        token = self.item(i0).text()
        with open(self.ini,"a") as f:
            f.write("\n")
            f.write(token)
    def _is_valid_single_selection(self, i0, i1):
        """ check for valid single selection, assume index 0 is not valid (text input)
        """
        return i0 > 0 and i0 == i1

from .connection import SpaceConnectionInfo
import configparser

class GroupTokenModel(TokenModel):
    """ Server-group token model, in sync with a ini config file (with sections)
    """
    SERVERS = [SpaceConnectionInfo.PRD, SpaceConnectionInfo.CIT, SpaceConnectionInfo.SIT]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.server = SpaceConnectionInfo.PRD
        
    def set_server(self, server):
        self.server = server
        self._refresh_token()

    def _refresh_token(self):
        tokens = self.token_groups.options(self.server)
        self.clear()
        it = self.invisibleRootItem()
        # it.appendRow(QStandardItem())
        it.appendRows([
            QStandardItem(t) for t in tokens
            if len(t) > 0
            ])

    def _write_to_file(self):
        if self.ini == "": return
        with open(self.ini, "w") as f:
            self.token_groups.write(f)

    def _load_ini(self, ini):
        token_groups = configparser.ConfigParser(allow_no_value=True)
        token_groups.optionxform = str
        for s in self.SERVERS:
            if not token_groups.has_section(s):
                token_groups.add_section(s)
        with open(ini,"a+") as f:
            f.seek(0)
            token_groups.read_file(f)
        
        self.token_groups = token_groups

    def _cb_remove_token_from_file(self, root, i0, i1):
        if not self._is_valid_single_selection(i0, i1): return # do not write multiple added items appendRows
        token = self.item(i0).text().strip()
        if self.token_groups.has_option(self.server, token):
            self.token_groups.remove_option(self.server, token)
            self._write_to_file()
        
    def _cb_append_token_to_file(self, root, i0, i1):
        if not self._is_valid_single_selection(i0, i1): return # do not write multiple added items appendRows
        token = self.item(i0).text()
        if not self.token_groups.has_option(self.server, token):
            self.token_groups.set(self.server, token)
            self._write_to_file()

class GroupTokenInfoModel(GroupTokenModel):
    INFO_KEYS = ["name","token"]
    SERIALIZE_KEYS = ["token","name"]
    DELIM = ","
    
    def _refresh_token(self):
        tokens = self.token_groups.options(self.server)
        self.clear()
        
        self.setHorizontalHeaderLabels(self.INFO_KEYS)
        it = self.invisibleRootItem()
        # it.appendRow(QStandardItem())
        
        for line in tokens:
            if not line: continue
            token_info = self.deserialize_line(line)
            if not token_info.get("token"): continue
            it.appendRow([QStandardItem(t)  
                for t in self.items_from_token_info(
                    token_info
                )
            ])

    def get_text(self, row, col):
        it = self.item(row, col)
        return it.text().strip() if it else None

    def get_token_info(self, row):
        return dict(
            [k, self.get_text(row, col)]
            for col, k in enumerate(self.INFO_KEYS)
        )

    def items_from_token_info(self, token_info: dict):
        return [token_info.get(k,"") for k in self.INFO_KEYS]

    def deserialize_line(self, line):
        infos = line.split(self.DELIM,maxsplit=1)
        return dict(zip(self.SERIALIZE_KEYS, infos))

    def serialize_token_info(self, row):
        token_info = self.get_token_info(row)
        lst_txt = [token_info.get(k,"") for k in self.SERIALIZE_KEYS]
        return self.DELIM.join(lst_txt)

    def _cb_remove_token_from_file(self, root, i0, i1):
        if not self._is_valid_single_selection(i0, i1): return # do not write multiple added items appendRows
        token = self.serialize_token_info(i0)
        if self.token_groups.has_option(self.server, token):
            self.token_groups.remove_option(self.server, token)
            self._write_to_file()
        
    def _cb_append_token_to_file(self, root, i0, i1):
        if not self._is_valid_single_selection(i0, i1): return # do not write multiple added items appendRows
        token = self.serialize_token_info(i0)
        if not self.token_groups.has_option(self.server, token):
            self.token_groups.set(self.server, token)
            self._write_to_file()
    def cb_write_token(self):
        pass

class EditableGroupTokenInfoModel(GroupTokenInfoModel):
    
    def cb_refresh_token(self):
        self._refresh_token()

    def _refresh_token(self):
        self.cache_tokens = list()
        super()._refresh_token()

    def _config_callback(self):
        super()._config_callback()
        try: self.itemChanged.disconnect()
        except TypeError: pass
        # self.rowsMoved.connect(print)
        self.dataChanged.connect(self._cb_changed_token_to_file)

    def cb_write_token(self):
        self.token_groups.remove_section(self.server)
        self.token_groups.add_section(self.server)
        tokens = self.token_groups.options(self.server)
        for token in self.cache_tokens:
            self.token_groups.set(self.server, token)
        tokens = self.token_groups.options(self.server)

        self._write_to_file()

    def _cb_remove_token_from_file(self, root, i0, i1):
        if not self._is_valid_single_selection(i0, i1): return
        token = self.cache_tokens.pop(i0)

    def _cb_append_token_to_file(self, root, i0, i1):
        if not self._is_valid_single_selection(i0, i1): return
        token = self.serialize_token_info(i0)
        self.cache_tokens.insert(i0,token)

    def _cb_changed_token_to_file(self, idx_top_left, idx_bot_right):
        i0 = idx_top_left.row()
        i1 = idx_bot_right.row()
        if not self._is_valid_single_selection(i0, i1): return
        token = self.serialize_token_info(i0)
        self.cache_tokens[i0] = token

    def _is_valid_single_selection(self, i0, i1):
        """ check for valid single selection (no text input)
        """
        return i0 == i1

class ComboBoxProxyModel(QIdentityProxyModel):
    def set_keys(self, keys):
        """ set header keys
        """
        self.keys = keys
        self.col_name = self.get_key_index("name")
        self.col_token = self.get_key_index("token")
    def get_key_index(self, key):
        return self.keys.index(key)
    def get_value(self, row, col, role):
        return self.sourceModel().item(row, col).data(role)
    def get_text(self, row, col):
        return self.sourceModel().item(row, col).text().strip()
    def get_token(self, row):
        it = self.sourceModel().item(row, self.col_token)
        return it.text().strip() if it else ""
    def data(self, index, role):
        val = super().data(index, role)
        if role == Qt.DisplayRole:
            name = self.get_text(index.row(), self.col_name)
            token = self.get_text(index.row(), self.col_token)
            if token:
                msg = name if name else "<noname token> %s"%token
                return QVariant(msg)
        return val
