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
PLUGIN_NAME = __package__
USER_DIR = os.path.abspath(QgsApplication.qgisSettingsDirPath())
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_DIR = os.path.join(USER_DIR, PLUGIN_NAME, "tmp")
LOG_FILE = os.path.join(USER_DIR, PLUGIN_NAME, "qgis.log")

os.makedirs(TMP_DIR,exist_ok=True)
