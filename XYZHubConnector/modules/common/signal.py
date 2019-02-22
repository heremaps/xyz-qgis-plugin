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

def make_qt_args(*a,**kw):
    return [a,kw]
def parse_qt_args(args):
    a, kw = args
    return a, kw
def make_fun_args(fun):
    def _fun_args(args):
        a, kw = parse_qt_args(args)
        return fun(*a,**kw)
    return _fun_args
def validate_qt_args(output):
    if not ( isinstance(output, (list,tuple)) and len(output) == 2):
        return False
    a, kw = output
    return isinstance(a, tuple) and isinstance(kw, dict)
def output_to_qt_args(output):
    if validate_qt_args(output):
        return output
    elif isinstance(output, tuple):
        return make_qt_args(*output)
    else:
        return make_qt_args(output)
        
class LoggingSignal(QObject):
    logging = pyqtSignal(str, object)

from qgis.core import QgsMessageLog, Qgis
from qgis.PyQt.QtCore import Qt

QOBJ_LOG = LoggingSignal()
QOBJ_LOG.logging.connect(lambda tag, a: log_qgis(*a,tag=tag), Qt.QueuedConnection)

from ... import config
def log_qgis(*a,tag=""):
    msg =  " ".join([str(i) for i in a])
    # careful for recursive loop logMessage()
    # QgsMessageLog.logMessage( msg, tag, Qgis.Info)
    with open( config.LOG_FILE, "a") as f:
        f.write("%s: %s\n"%(tag,msg))
        
        
def make_print_qgis(tag="debug",debug=False):
    def _print_qgis(*a):
        QOBJ_LOG.logging.emit(tag,a)
    return _print_qgis if debug else lambda *a: None
def close_print_qgis():
    QOBJ_LOG.logging.disconnect()

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