# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


import configparser
from typing import Any, List, Mapping

from qgis.PyQt.QtCore import QIdentityProxyModel, Qt, QVariant
from qgis.PyQt.QtGui import QStandardItem, QStandardItemModel

GroupedData = Mapping[str, List[Mapping]]

class UsedToken():
    def __init__(self):
        self.invalid_idx = -1
        self.used_token_idx = self.invalid_idx
        self._is_used_token_changed = False
    def set_invalid_token_idx(self, invalid_idx):
        self.invalid_idx = invalid_idx
        self.reset_used_token_idx()
    def get_invalid_token_idx(self):
        return self.invalid_idx
    def set_used_token_idx(self, idx):
        self.used_token_idx = idx
        self._is_used_token_changed = False
    def get_used_token_idx(self):
        return self.used_token_idx
    def reset_used_token_idx(self):
        self.used_token_idx = self.invalid_idx
        self._is_used_token_changed = True
    def is_used_token_idx(self, idx):
        return (
            idx != self.get_invalid_token_idx()
            and idx == self.get_used_token_idx()
        )
    def modify_token_idx(self, idx):
        flag = idx == self.get_used_token_idx()
        self._is_used_token_changed = self._is_used_token_changed or flag
    def is_used_token_modified(self):
        return self._is_used_token_changed

def make_config_parser():
    """ ConfigParser for managing token/server
    """
    parser = configparser.ConfigParser(allow_no_value=True, delimiters=("*",))
    parser.optionxform = str
    return parser

class EditableItemModel(QStandardItemModel):
    INFO_KEYS = []
    TOKEN_KEY = ""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cached_data = list()
        self.cfg = list()
        self._config_callback()

    def get_text(self, row, col):
        it = self.item(row, col)
        return it.text().strip() if it else "None"

    def get_data(self, row):
        return dict(
            [k, self.get_text(row, col)]
            for col, k in enumerate(self.INFO_KEYS)
        )

    def get_submitted_data(self):
        return list(self.cfg)

    def items_from_data(self, data: dict):
        return [data.get(k,"") for k in self.INFO_KEYS]

    def refresh_model(self):
        self._refresh_model()

    def submit_cache(self):
        self._submit_cache()

    def _config_callback(self):
        try: self.rowsInserted.disconnect()
        except TypeError: pass
        try: self.rowsAboutToBeRemoved.disconnect()
        except TypeError: pass

        self.rowsInserted.connect(self._cb_item_inserted)

        # persistent remove (uncomment next line)
        self.rowsAboutToBeRemoved.connect(self._cb_item_removed)

        try: self.itemChanged.disconnect()
        except TypeError: pass
        self.dataChanged.connect(self._cb_item_changed)

    def _submit_cache(self):
        self.cfg = list(filter(self._validate_data, self.cached_data))

    def _refresh_model(self):
        self.cached_data = list()
        self.clear()
        
        self.setHorizontalHeaderLabels(self.INFO_KEYS)
        it = self.invisibleRootItem()
        # it.appendRow(QStandardItem())
        
        for data in self._iter_data():
            it.appendRow([QStandardItem(t) for t in self.items_from_data(data)])

    def _cb_item_removed(self, root, i0, i1):
        if not self._is_valid_single_selection(i0, i1): return
        data = self.cached_data.pop(i0)

    def _cb_item_inserted(self, root, i0, i1):
        if not self._is_valid_single_selection(i0, i1): return
        data = self.get_data(i0)
        self.cached_data.insert(i0, data)

    def _cb_item_changed(self, idx_top_left, idx_bot_right):
        i0 = idx_top_left.row()
        i1 = idx_bot_right.row()
        if not self._is_valid_single_selection(i0, i1): return
        data = self.get_data(i0)
        self.cached_data[i0] = data

    def _is_valid_single_selection(self, i0, i1):
        """ check for valid single selection (no text input)
        """
        return i0 == i1
        
    # helper
    def _iter_data(self):
        for data in self.cfg:
            if not self._validate_data(data): continue
            yield data
    
    def _validate_data(self, data):
        return data and data.get(self.TOKEN_KEY)

class GroupEditableItemModel(EditableItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cfg: GroupedData = dict()
        self.group_key = ""
        
    def from_dict(self, data: GroupedData):
        self.cfg = {
            k: list(filter(self._validate_data, lst))
            for k, lst in data.items()
        }
        
        
    def to_dict(self) -> GroupedData:
        return dict(self.cfg)

    def get_submitted_data(self):
        return {self.group_key: list(self._iter_data())}

    def _submit_cache(self):
        self.cfg.pop(self.group_key, None)
        self.cfg[self.group_key] = list()
        for data in self.cached_data:
            if not self._validate_data(data): continue
            self.cfg[self.group_key].append(data)

    def _set_group(self, key):
        self.group_key = key

    # helper
    def _iter_data(self):
        for data in self.cfg.get(self.group_key, list()):
            if not self._validate_data(data): continue
            yield data

class ConfigParserMixin():
    SERIALIZE_KEYS = ("value","name")
    DELIM = ","
    def __init__(self, ini, cfg: configparser.ConfigParser, serialize_keys=("value","name"), delim=","):
        self.ini = ini
        self.cfg = cfg
        self.SERIALIZE_KEYS = serialize_keys
        self.DELIM = delim

    def set_ini(self, ini):
        self.ini = ini

    def get_ini(self):
        return self.ini

    def update_config(self, data: GroupedData):
        for section, options in data.items():
            if not section.strip(): continue
            self.cfg.remove_section(section)
            self.cfg.add_section(section)
            for option in options:
                self.cfg.set(section, self.serialize_data(option))

    def get_config(self) -> GroupedData:
        return {
            s: [self.deserialize(line) for line in self.cfg.options(s)]
            for s in self.cfg.sections()
        }

    def read_from_file(self):
        with open(self.ini, "a+") as f:
            f.seek(0)
            self.cfg.read_file(f)

    def write_to_file(self):
        # clean unwanted sections
        for s in self.cfg.sections():
            if not s.strip(): self.cfg.remove_section(s)
        with open(self.ini, "w") as f:
            self.cfg.write(f)

    def deserialize(self, line):
        infos = line.split(self.DELIM,maxsplit=1)
        return dict(zip(self.SERIALIZE_KEYS, map(str.strip, infos)))

    def serialize_data(self, token_info):
        lst_txt = [token_info.get(k,"").strip() for k in self.SERIALIZE_KEYS]
        return self.DELIM.join(lst_txt)

class WritableItemModel(GroupEditableItemModel):
    SERIALIZE_KEYS = ("value","name")

    # load_ini - load_from_file
    def __init__(self, ini, parser: configparser.ConfigParser = None, parent=None):
        super().__init__(parent)
        UsedToken.__init__(self)
        if not parser:
            parser = make_config_parser()
        self.parser = ConfigParserMixin(ini, parser, self.SERIALIZE_KEYS)

    def load_from_file(self):
        self.parser.read_from_file()
        self.from_dict(self.parser.get_config())
        self._refresh_model()

    def write_to_file(self):
        self._submit_cache()
        # print(self.get_submitted_data().keys())
        self.parser.update_config(self.get_submitted_data())
        self.parser.write_to_file()

    def submit_cache(self):
        self.write_to_file()

class TokenModel(WritableItemModel, UsedToken):
    """ Grouped Token Model, Cached changes and write to file at the end
    """
    INFO_KEYS = ["name","token"]
    SERIALIZE_KEYS = ["token","name"]
    TOKEN_KEY = "token"
    def __init__(self, ini, parser: configparser.ConfigParser = None, parent=None):
        super().__init__(ini, parser, parent)
        UsedToken.__init__(self)
        self._set_group("PRD")

    def set_default_servers(self, default_api_urls):
        self._migrate_server_aliases(default_api_urls)
        url = default_api_urls.get(self.group_key)
        if url: self._set_group(url)
        self._refresh_model()

    def set_server(self, server):
        """ Set server will submit the cache of the current group (server), then switch to the new server and refresh
        """
        # print("set_server", server)
        self.reset_used_token_idx()
        self.submit_cache()
        self._set_group(server)
        self._refresh_model()

    def get_server(self):
        return self.group_key

    def _migrate_server_aliases(self, default_api_urls):
        for env, url in default_api_urls.items():
            if env in self.cfg and url not in self.cfg:
                self.cfg[url] = self.cfg[env]


class ServerModel(WritableItemModel, UsedToken):
    INFO_KEYS = ["name","server"]
    SERIALIZE_KEYS = ["server","name"]
    TOKEN_KEY = "server"

    def __init__(self, ini, parser: configparser.ConfigParser = None, parent=None):
        super().__init__(ini, parser, parent)
        UsedToken.__init__(self)
        self._set_group("servers")
        
    def set_default_servers(self, default_api_urls):
        self._init_default_servers([
            dict(name="HERE Server", server=default_api_urls["PRD"])
        ])

    def _init_default_servers(self, server_infos: list):
        existing_server = dict()
        for idx, data in enumerate(self._iter_data()):
            existing_server.setdefault(data["server"], list()).append(idx)
        
        it = self.invisibleRootItem()
        
        # # remove existing default server
        # removed_idx = sorted(sum((
        #     existing_server.get(sv, list())
        #     for server_info in server_infos
        #     for sv in server_info.pop("old_servers", list()) + [server_info["server"]]
        #     ), list()), reverse=True)
        # for idx in removed_idx:
        #     it.removeRow(idx)

        # add default server
        for i, server_info in enumerate(server_infos):
            if server_info["server"] in existing_server: continue
            if not self._validate_data(server_info): continue
            it.insertRow(i, [
                QStandardItem(t) for t in self.items_from_data(server_info)
            ])
        self.submit_cache()


class ServerTokenConfig():
    def __init__(self, ini, parent=None):
        self.parent = parent
        self.ini = ini
        self.parser = make_config_parser()
        self.default_api_urls = dict()

    def get_server_model(self):
        model = ServerModel(self.ini, self.parser, self.parent)
        model.load_from_file()
        model.set_default_servers(self.default_api_urls)
        return model
        
    def get_token_model(self):
        model = TokenModel(self.ini, self.parser, self.parent)
        model.load_from_file()
        model.set_default_servers(self.default_api_urls)
        return model

    def set_default_servers(self, default_api_urls):
        self.default_api_urls = default_api_urls


class ComboBoxProxyModel(QIdentityProxyModel):
    def __init__(self, token_key="token", named_token="{name}", nonamed_token="<noname token> {token}"):
        super().__init__()
        self.token_key = token_key
        self.named_token = named_token
        self.nonamed_token = nonamed_token
    def set_keys(self, keys):
        """ set header keys
        """
        self.keys = keys
        self.col_name = self.get_key_index("name")
        self.col_token = self.get_key_index(self.token_key)
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
                msg = self.named_token.format(name=name, token=token) if name else self.nonamed_token.format(token=token)
                return QVariant(msg)
        return val
