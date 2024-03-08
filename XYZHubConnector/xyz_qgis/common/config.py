# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os
from typing import Iterable

from ... import __version__ as version


class Config:
    TAG_PLUGIN = __package__
    PLUGIN_NAME = __package__.split(".")[-1]
    PLUGIN_FULL_NAME = PLUGIN_NAME
    PLUGIN_VERSION = version
    PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
    USER_DIR = os.path.join(os.path.expanduser("~"), ".{name}".format(name=PLUGIN_NAME))
    USER_PLUGIN_DIR = os.path.join(USER_DIR, PLUGIN_NAME)
    TMP_DIR = os.path.join(USER_DIR, PLUGIN_NAME, "tmp")
    LOG_FILE = os.path.join(USER_DIR, PLUGIN_NAME, "qgis.log")
    EXTERNAL_LIB_DIR = os.path.join(PLUGIN_DIR, "external")
    PYTHON_LOG_FILE = os.path.join(USER_DIR, PLUGIN_NAME, "python.log")

    def __init__(self):
        self._is_here_system = None

    def set_config(self, config):
        for k, v in config.items():
            setattr(self, k, v)

    def get_external_os_lib(self):
        txt = self.get_plugin_setting("ext_lib") or os.environ.get("HERE_QGIS_EXT_LIB")
        lib_path = os.path.abspath(txt) if txt else self.EXTERNAL_LIB_DIR

        return lib_path

    def get_plugin_setting(self, key):
        from qgis.PyQt.QtCore import QSettings

        key_prefix = "xyz_qgis/settings"
        key_ = f"{key_prefix}/{key}"
        return QSettings().value(key_)

    def _check_here_system(self):
        import socket
        from .crypter import decrypt_text

        socket.setdefaulttimeout(1)

        def _check_host(host: str) -> bool:
            is_host_reachable = False
            try:
                ip = socket.gethostbyname(host)
                is_host_reachable = len(ip.split(".")) == 4
            except:
                pass
            return is_host_reachable

        def _check_fqdn(hosts: Iterable[str]) -> bool:
            fqdn = socket.getfqdn()
            return any(host in fqdn for host in hosts)

        host1 = decrypt_text("Vi5tWQcgFl88Wzg=")
        host2 = decrypt_text("XiRtWQcgFl88Wzg=")

        is_here_domain = _check_host(host1) or _check_host(host2) or _check_fqdn([host1, host2])
        return is_here_domain

    def is_here_system(self):
        if self._is_here_system is None:
            try:
                self._is_here_system = self._check_here_system()
            except Exception as e:
                print(e)
        return self._is_here_system
