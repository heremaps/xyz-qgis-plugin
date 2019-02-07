# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
#
###############################################################################

from qgis.PyQt.QtCore import Qt

from .. import make_exception_obj
from .. import BasicSignal, make_qt_args
from .async_fun import AsyncFun, InvalidArgsException

# __package__ = __package__.rpartition(".")[0]
# print(__package__)

class Controller(object):
    """ Contains all main features of the plugin: Load data, Upload data, Manage space 
    Control threading, worker for async function (single of parallel). Acts as the central in message exchanging between workers.
    Chain async function
    """
    def __init__(self):
        self.signal = BasicSignal()
        self.lst_fun = list()
        self._cnt = 0
    # def __del__(self):
    #     del self.signal
    #     print("del",self)
    # DEPRECATED
    def split_input(self):
        pass
    def merge_output(self):
        pass
    def next_fun(self, args):
        pass
    #
    def config_fun(self, lst_fun):
        pass
    def get_lst_fun(self):
        return self.lst_fun
    def start_args(self, args):
        self.lst_fun[0].call(args)
    def start(self, *a, **kw):
        # use start_args define in base class
        Controller.start_args( self, make_qt_args(*a,**kw))
        
        
class ChainInterrupt(Exception):
    pass
class ChainController(Controller):
    """ Chain async function
    """
    def config_fun(self, lst_fun):
        """
        Args:
            lst_fun: list of AsyncFun
        """
        
        for f in lst_fun:
            assert(isinstance(f, AsyncFun))
        self.lst_fun = list(lst_fun)
        for idx, (fun, fun2) in enumerate(zip(self.lst_fun, self.lst_fun[1:])):
            fun.signal.results.connect(fun2.call, Qt.QueuedConnection)
            # fun.signal.results.connect(fun2)

            fun.signal.error.connect(self._make_error_handler(idx))
        fun = self.lst_fun[-1]
        fun.signal.results.connect(self.signal.results.emit)
        fun.signal.finished.connect(self.signal.finished.emit)
        fun.signal.error.connect(self._make_error_handler(len(self.lst_fun)-1 ) )
        
    def _make_error_handler(self, idx):
        idx_str = "%s/%s in chain"%(idx + 1, len(self.lst_fun))
        def _chain_interrupt(e):
            self._handle_error(
                make_exception_obj( ChainInterrupt(e, idx, idx_str, self))
            )
        return _chain_interrupt
    def _handle_error(self, e):
        self.signal.error.emit(e)
        
    def start_args(self, args):
        # increase the count of function calls
        self.signal.progress.emit(self._cnt)
        self._cnt += 1
        Controller.start_args( self, args)
    def start(self, *a, **kw):
        # use start_args define in current class
        ChainController.start_args( self, make_qt_args(*a,**kw))
class LoopController(ChainController):
    """ Loop of Chain async function
    """
    def config_fun(self, lst_fun):
        """
        Args:
            lst_fun: list of AsyncFun
        """
        for f in lst_fun:
            assert(isinstance(f, AsyncFun))
        self.lst_fun = list(lst_fun)
        for idx, (fun, fun2) in enumerate(zip(self.lst_fun, self.lst_fun[1:])):
            fun.signal.results.connect(fun2.call, Qt.QueuedConnection)
            # fun.signal.results.connect(fun2)

            fun.signal.error.connect(self._make_error_handler(idx))
        idx = len(self.lst_fun)-1
        fun = self.lst_fun[idx]
        fun.signal.finished.connect(self._run_loop, Qt.QueuedConnection)
        fun.signal.error.connect(self._make_error_handler( idx) )
        
    def _handle_error(self, e):
        raise NotImplementedError("handle_error")
    def _run_loop(self):
        raise NotImplementedError("run_loop")
    def stop_loop(self):
        raise NotImplementedError("stop_loop")
        
    def start(self, *a, **kw):
        # use start_args define in base class
        Controller.start_args( self, make_qt_args(*a,**kw))