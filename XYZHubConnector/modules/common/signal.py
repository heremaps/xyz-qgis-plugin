# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.PyQt.QtCore import pyqtSignal, QObject
from qgis.core import Qgis
from typing import Tuple, Callable

QtArgs = Tuple[tuple, dict]

def make_qt_args(*a,**kw) -> QtArgs:
    return a, kw
def parse_qt_args(args: QtArgs) -> Tuple[tuple, dict]:
    a, kw = args
    return a, kw
def make_fun_args(fun: Callable) -> Callable[[QtArgs], Callable]:
    def _fun_args(args):
        a, kw = parse_qt_args(args)
        return fun(*a,**kw)
    return _fun_args
def validate_qt_args(output):
    if not ( isinstance(output, (list,tuple)) and len(output) == 2):
        return False
    a, kw = output
    return isinstance(a, tuple) and isinstance(kw, dict)
def output_to_qt_args(output) -> QtArgs:
    if validate_qt_args(output):
        return output
    elif isinstance(output, tuple):
        return make_qt_args(*output)
    else:
        return make_qt_args(output)

from qgis.core import QgsMessageLog, Qgis
from qgis.PyQt.QtCore import Qt

from ... import config
import time

level = ["Info", "Warning", "Critical", "Success", "None"]
qgis_level = dict(zip(map(lambda k: getattr(Qgis,k), level), level))
time_fmt = '%Y-%m-%dT%H:%M:%S%z'

def make_print_qgis(tag="debug",debug=False):
    def _print_qgis(*a):    
        msg =  " ".join([str(i) for i in a])
        QgsMessageLog.logMessage(
            "{tag:10} {msg}".format(
                tag="[{}]".format(tag),
                msg=msg),
            config.TAG_PLUGIN, Qgis.Info)
    return _print_qgis if debug else lambda *a: None
    
def cb_log_qgis(msg, tag, level):
    if tag != config.TAG_PLUGIN: return

    # careful for recursive loop logMessage()
    # QgsMessageLog.logMessage( msg, tag, Qgis.Info)
    with open( config.LOG_FILE, "a") as f:
        f.write("{time} {level:10} {msg}\n".format(
            time=time.strftime(time_fmt,time.localtime()),
            level="/{}".format(qgis_level.get(level,"Unknown")), 
            msg=msg
        ))

# dont need extra signal
# class LoggingSignal(QObject):
#     logging = pyqtSignal(object)
# QOBJ_LOG = LoggingSignal()
# QOBJ_LOG.logging.connect(lambda a: cb_log_qgis(*a), Qt.QueuedConnection)

# def log_qgis(*a):
#     QOBJ_LOG.logging.emit(a)
# def close_file_logger():
#     try:QOBJ_LOG.logging.disconnect()
#     except: pass

class BasicSignal(QObject):
    """
    Defines the signals available .

    Supported signals are:

    finished
        No data

    error
        `tuple` (exctype, value, traceback.format_exc() )

    result
        `object` data returned from processing, anything

    progress
        `int` indicating % progress
    """
    finished = pyqtSignal()
    results = pyqtSignal(object)
    error = pyqtSignal(object)
    progress = pyqtSignal(object)