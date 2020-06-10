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

from ... import __version__ as version

class Config():
    TAG_PLUGIN = __package__
    PLUGIN_NAME = __package__.split(".")[-1]
    PLUGIN_FULL_NAME = PLUGIN_NAME
    PLUGIN_VERSION = version
    PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
    USER_DIR = os.path.join(os.path.expanduser("~"), ".{name}".format(name=PLUGIN_NAME))
    USER_PLUGIN_DIR = os.path.join(USER_DIR, PLUGIN_NAME)
    TMP_DIR = os.path.join(USER_DIR, PLUGIN_NAME, "tmp")
    LOG_FILE = os.path.join(USER_DIR, PLUGIN_NAME, "qgis.log")
    
    def set_config(self, config):
        for k, v in config.items():
            setattr(self, k, v)
