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
from .controller import LoopController
from .controller import AsyncFun, parse_qt_args, make_qt_args,output_to_qt_args, make_exception_obj

########################
# Base Load
########################

class ParallelWrapper():
    def __init__(self, n_parallel=1):
        # super().__init__()
        self.n_parallel = n_parallel # deprecate
        self._n_active = 0
        
    def count_active(self):
        return self._n_active
    def _release(self):
        self._n_active -= 1
    def _try_finish(self):
        self._release()
        if self.count_active() == 0:
            self._emit_finish()
    def dispatch_parallel(self, delay=0.1, delay_offset=0.001, n_parallel=1):
        for i in range(n_parallel): 
            d = delay*i  + delay_offset
            QTimer.singleShot(d, self._dispatch)
    def _dispatch(self):
        if self.count_active() == 0:
            self._emit_progress_start()
        self._n_active += 1
        self._run_single()
    def reset(self, **kw):
        self._n_active = 0

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

class ParallelFun(AsyncFun,ParallelWrapper):
    def __init__(self, fun):
        AsyncFun.__init__(self, fun)
        ParallelWrapper.__init__(self)
        self.results=dict()
    def call(self, args):
        a, kw = parse_qt_args( args)
        self.dispatch_parallel(*a)
        
    def _try_finish(self):
        self._release()
        if self.count_active() == 0:
            self.signal.finished.emit()
            self.signal.results.emit(make_qt_args(self.results))
            
    def _dispatch(self):
        args = next(self.iter_args)
        k = args[0]
        try:
            output = self.fun( *args)
        except Exception as e:
            obj = make_exception_obj(e)
            self.signal.error.emit(obj)
        else:
            self.results[k] = output
            self._try_finish()
    def dispatch_parallel(self, lst_args, **kw):
        self.signal.progress.emit( 0)
        
        n_parallel = len(lst_args)
        self._n_active = n_parallel

        if n_parallel == 0:
            self.signal.finished.emit()
            return

        self.iter_args = iter(lst_args)
        kw.update(n_parallel=n_parallel)

        ParallelWrapper.dispatch_parallel(self, **kw)

class BaseLoader(ParallelLoop):
    LOADING = "loading"
    ALL_FEAT = "all_feature"
    MAX_FEAT = "max_feat"
    FINISHED = "finished"
    STOPPED = "stopped"
    
    def __init__(self):
        super().__init__()
        self.status = self.LOADING
    def _check_valid(self):
        return True
    def _check_status(self):
        return True
    def _run(self):
        LoopController.start(self)
    def _run_loop(self):
        if not self._check_valid():
            return
        if not self._check_status():
            return
        self._run()
    def _emit_finish(self):
        self.status = self.FINISHED
        self.signal.finished.emit()
    def stop_loop(self):
        self.status = self.STOPPED
    def reset(self, **kw):
        super(BaseLoader, self).reset(**kw)
        self.status = self.LOADING
        
    def start(self, **kw):
        if not self._check_valid():
            return
        if self.count_active() == 0:
            self.reset( **kw)
        self.dispatch_parallel(n_parallel=self.n_parallel)
