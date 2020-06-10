# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.PyQt.QtCore import QTimer

from ..controller import (AsyncFun, LoopController, make_exception_obj,
                          make_qt_args, parse_qt_args, QtArgs)
from typing import Sequence, Iterable
from threading import Lock


from ..common.signal import make_print_qgis
print_qgis = make_print_qgis("loop_loader")

########################
# Base Load
########################

class ParallelWrapper():
    def __init__(self, n_parallel=1):
        # super().__init__()
        self.n_parallel = n_parallel # deprecate
        self._n_active = 0
        self.lock = Lock()
        
    def count_active(self):
        with self.lock:
            n_active = self._n_active
        return n_active
    def _reserve(self):
        with self.lock:
            self._n_active = self._n_active + 1
            n_active = self._n_active
            print_qgis("reserve", n_active)
        return n_active
    def _release(self):
        with self.lock:
            self._n_active = max(0, self._n_active - 1)
            n_active = self._n_active
        return n_active
    def _try_finish(self):
        n_active = self._release()
        print_qgis("try_finish con", n_active)
        if n_active == 0:
            print_qgis("try_finish con emit")
            self._emit_finish()
    def dispatch_parallel(self, delay=0.1, delay_offset=0.001, n_parallel=1):
        for i in range(n_parallel): 
            d = delay*i  + delay_offset
            QTimer.singleShot(d, self._dispatch)
    def _dispatch(self):
        self._run_single()
    def _emit_progress_start(self):
        raise NotImplementedError()
    def _emit_finish(self):
        raise NotImplementedError()
    def _run_single(self):
        raise NotImplementedError()

class ParallelLoop(LoopController,ParallelWrapper):
    def __init__(self):
        LoopController.__init__(self)
        ParallelWrapper.__init__(self)
    def _run_single(self):
        self._run_loop()
    def _emit_progress_start(self):
        self.signal.progress.emit( 0)
    def _emit_finish(self):
        self.signal.finished.emit()
    def dispatch_parallel(self, delay=0.1, delay_offset=0.001, n_parallel=1):
        for i in range(n_parallel): 
            if not self.count_active() < self.n_parallel: return
            n_active = self._reserve()
            print_qgis("dispatch con", n_active)
            if n_active == 1:
                print_qgis("dispatch con emit")
                self._emit_progress_start()
            d = delay*i  + delay_offset
            QTimer.singleShot(d, self._dispatch)

class ParallelFun(AsyncFun,ParallelWrapper):
    def __init__(self, fun):
        AsyncFun.__init__(self, fun)
        ParallelWrapper.__init__(self)
        self.results=dict()
        self.iter_args: Iterable = None
    def call(self, args: QtArgs):
        a, kw = parse_qt_args( args)
        self.dispatch_parallel(*a)
        
    def _emit_finish(self):
            self.signal.results.emit(make_qt_args(self.results))
            self.signal.finished.emit()

    def _try_finish(self):
        n_active = self._release()
        if n_active == 0:
            self._emit_finish()

    def _dispatch(self):
        args = next(self.iter_args, None)
        if args is None: return # hotfix
        k = args[0]
        try:
            output = self.fun( *args)
        except Exception as e:
            obj = make_exception_obj(e)
            self.signal.error.emit(obj)
        else:
            self.results[k] = output
            self._try_finish()
    def dispatch_parallel(self, lst_args: Sequence, **kw):
        self.signal.progress.emit( 0)
        
        n_parallel = len(lst_args)
        self._n_active = n_parallel

        if n_parallel == 0:
            self._emit_finish()
            return

        self.iter_args = iter(lst_args)
        kw.update(n_parallel=n_parallel)

        ParallelWrapper.dispatch_parallel(self, **kw)

class BaseLoop(ParallelLoop):
    LOADING = "loading"
    FINISHED = "finished"
    STOPPED = "stopped"
    
    def __init__(self):
        super().__init__()
        self.status = self.LOADING
    def _check_valid(self):
        return True
    def _check_status(self):
        return self.status != self.STOPPED
    def _run(self):
        """
        internal default single run
        """
        LoopController.start(self)
    def _run_loop(self):
        """
        internal default run loop logic
        """
        if not self._check_valid():
            return
        if not self._check_status():
            return
        self._run()
    def _emit_finish(self):
        self.status = self.FINISHED
        self.signal.finished.emit()
    def stop_loop(self):
        """
        stop loop externally
        """
        self.status = self.STOPPED
    def reset(self, **kw):
        """
        reset is invoked when BaseLoop first started (no active thread)
        """
        self.status = self.LOADING
    def start(self, *a, **kw):
        """
        explicit invoke to start dispatching task (_run_loop) in parallel. Do not override !
        """
        # if not self._check_valid():
        #     return
        # if self.count_active() == 0:
        ## parallel dispatch might fail
        self.reset( **kw)
        self.dispatch_parallel(n_parallel=self.n_parallel)

class BaseLoader(BaseLoop):
    ALL_FEAT = "all_feature"
    MAX_FEAT = "max_feat"
