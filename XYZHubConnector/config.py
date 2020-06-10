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

from qgis.core import QgsApplication

from . import __version__ as version
from .xyz_qgis.common import override_config

TAG_PLUGIN = "XYZ Hub Connector"
PLUGIN_FULL_NAME = "XYZ Hub Connector"
PLUGIN_NAME = __package__
PLUGIN_VERSION = version
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
USER_DIR = os.path.abspath(QgsApplication.qgisSettingsDirPath())
USER_PLUGIN_DIR = os.path.join(USER_DIR, PLUGIN_NAME)
TMP_DIR = os.path.join(USER_DIR, PLUGIN_NAME, "tmp")
LOG_FILE = os.path.join(USER_DIR, PLUGIN_NAME, "qgis.log")

os.makedirs(TMP_DIR,exist_ok=True)

override_config(dict(filter(lambda kv: kv[0].isupper(), locals().items())))
