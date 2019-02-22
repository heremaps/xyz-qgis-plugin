# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.PyQt.uic import loadUiType
from . import config
import os
import time

def disconnect_silent(signal):
    ok = True
    try: signal.disconnect()
    except TypeError: ok = False
    return ok
def get_ui_class(ui_file):
    """return class object of a uifile"""
    ui_file_full = os.path.join(
        config.PLUGIN_DIR, "gui", "ui", ui_file
        )
    return loadUiType(ui_file_full)[0]

def make_unique_full_path(ext="json"):
    return os.path.join(config.TMP_DIR, "%s.%s"%(time.time(),ext))
    # return os.path.join(config.TMP_DIR, "%s.%s"%("test",ext))
def clear_cache():
    files = [os.path.join(config.TMP_DIR, f) for f in os.listdir(config.TMP_DIR)]
    for f in files:
        try: os.remove(f)
        except OSError: pass # files in used