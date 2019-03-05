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

class TokenModel(QStandardItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ini = ""
        self._config_callback() # persistant_cange (Experimental)
    def load_ini(self, ini):
        self._load_ini(ini)
        self.ini = ini # must be after loaded
    def get_ini(self):
        return self.ini
    
    def cb_set_server(self, server):
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
            print(new_lines)
            f.writelines(new_lines)
            f.truncate()
    def _cb_append_token_to_file(self, root, i0, i1):
        if self.ini == ""  or not self._is_valid_single_selection(i0, i1): return # do not write multiple added items appendRows
        token = self.item(i0).text()
        with open(self.ini,"a") as f:
            f.write("\n")
            print(token,i0,i1)
            f.write(token)
    def _is_valid_single_selection(self, i0, i1):
        return i0 > 0 and i0 == i1

from .connection import SpaceConnectionInfo
import configparser

class GroupTokenModel(TokenModel):
    SERVERS = [SpaceConnectionInfo.PRD, SpaceConnectionInfo.CIT, SpaceConnectionInfo.SIT]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.server = SpaceConnectionInfo.PRD
        
    def cb_set_server(self, server):
        self.server = server

        tokens = self.token_groups.options(server)

        self.clear()
        it = self.invisibleRootItem()
        it.appendRow(QStandardItem())
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