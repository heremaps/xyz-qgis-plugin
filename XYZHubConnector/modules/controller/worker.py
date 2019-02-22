# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

# from PyQt5.QtGui import *
import time

from qgis.PyQt.QtCore import QRunnable, QThread

from . import make_exception_obj
from . import BasicSignal, output_to_qt_args

# https://martinfitzpatrick.name/article/multithreading-pyqt-applications-with-qthreadpool/

class Worker(QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and 
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function [a,kw]

    '''

    def __init__(self, fn, *a, **kw):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.a = a
        self.kw = kw
        self.signal = BasicSignal()
        self.setAutoDelete(True) # default is True # False lead to early crash

        self._finished=False
        self._cache = dict()
        # Add the callback to our kwargs
        # self.kwargs['progress_callback'] = self.signals.progress
    def is_finished(self):
        return self._finished
    # def get_cache(self):
    #     return self._cache
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''
        
        # Retrieve args/kwargs here; and fire processing using them
        try:
            # debug_signal.emit("worker thread: %d"% int(QThread.currentThreadId()))
            output = self.fn( *self.a, **self.kw)
            output = output_to_qt_args(output)
        except Exception as e:
            obj = make_exception_obj(e)
            self.signal.error.emit( obj) #worker2
            # self._cache["error"] = obj
        else:
            self._finished=True
            self.signal.finished.emit()  # Done
            self.signal.results.emit(output) #worker2 # Return the result of the processing
            # self._cache["results"] = output
            