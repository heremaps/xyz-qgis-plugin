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
import time
import shutil
import gzip

from qgis.PyQt.uic import loadUiType
from . import config

def get_current_millis_time():
    return int(round(time.time() * 1000))

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
def make_fixed_full_path(name="temp", ext="json"):
    return os.path.join(config.TMP_DIR, "%s.%s"%(name,ext))
def clear_cache():
    files = [os.path.join(config.TMP_DIR, f) for f in os.listdir(config.TMP_DIR)]
    files.append(config.LOG_FILE)
    for f in files:
        try: os.remove(f)
        except OSError: pass # files in used

def archive_log_file():
    if not os.path.exists(config.LOG_FILE): return
    threshold = 5*1024*1024
    if os.path.getsize(config.LOG_FILE) < threshold: return
    base,_ = os.path.split(config.LOG_FILE)
    idx = len([s for s in os.listdir(base) if s.endswith(".gz")])
    archive_path = os.path.join(base, "qgis.%s.log.gz"%idx)
    with open(config.LOG_FILE, 'rb') as f_in:
        with gzip.open(archive_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    with open(config.LOG_FILE, 'w') as f_in:
        pass

archive_log_file()
