# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.PyQt.QtNetwork import QNetworkReply
from qgis.PyQt.QtCore import Qt, QThreadPool
from qgis.core import QgsProject

from .. import make_exception_obj
from .. import BasicSignal, output_to_qt_args, parse_qt_args, QtArgs
from ..worker import Worker
from typing import Callable

class InvalidArgsException(Exception):
    pass
class AsyncFun(object):
    """Wrapper for async function (NetworkReply or Long-running task)

    reentrant call (older async task shall be ignored, aborted)
    -> by checking chain_id
    """

    def __init__(self, fun: Callable):
        self.signal = BasicSignal(QgsProject.instance())
        self.fun: Callable = fun
        self.cache = dict()
        self._finished=False
    def get_fn(self) -> Callable:
        return self.fun
    def call(self, args: QtArgs) -> None:
        """ Assume args is qt_args
        """
        a, kw = parse_qt_args( args)
        try:
            async_obj = self.fun( *a,**kw)
        except Exception as e:
            obj = make_exception_obj(e)
            self.signal.error.emit(obj)
        else:
            output = output_to_qt_args(async_obj)

            self.signal.finished.emit()
            self.signal.results.emit(output)
        
class WorkerFun(AsyncFun):
    """ wrapper for worker (without cache)
    """
    def __init__(self, fun: Callable, pool: QThreadPool):
        super().__init__(fun)
        self.pool = pool
        
    def call(self, args: QtArgs) -> None:
        a, kw = parse_qt_args( args)
        worker = Worker(self.fun, *a, **kw)
        
        worker.signal.error.connect( self.signal.error.emit)
        worker.signal.results.connect( self.signal.results.emit)
        worker.signal.finished.connect( self.signal.finished.emit)
        self.pool.start(worker)

        
class NetworkFun(AsyncFun):
    def _emit(self, output: QtArgs):
        self.signal.finished.emit()
        self.signal.results.emit(output)
    def _emitter(self, output: QtArgs) -> Callable:
        def _fn():
            self._emit(output)
        return _fn
    def call(self, args: QtArgs) -> None:
        a, kw = parse_qt_args( args)
        try:
            reply = self.fun( *a,**kw)
            self.reply = reply
        except Exception as e:
            obj = make_exception_obj(e)
            self.signal.error.emit(obj)
        else:
            output: QtArgs = output_to_qt_args(reply)
            if reply.isFinished():
                self._emit(output)
            else:
                # reply.finished.connect(lambda: self._emit(output) )
                reply.finished.connect( self._emitter(output))
