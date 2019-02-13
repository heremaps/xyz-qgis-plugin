# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
#
###############################################################################

from qgis.PyQt.QtCore import QTimer
from .controller import LoopController

########################
# Base Load
########################

class ParallelLoop(LoopController):
    def __init__(self, n_parallel=1):
        super().__init__()
        self.n_parallel = n_parallel
        self._n_active = 0
    def count_active(self):
        return self._n_active
    def _release(self):
        self._n_active -= 1
    def _try_finish(self):
        self._release()
        if self.count_active() == 0:
            self.signal.finished.emit()
    def dispatch_parallel(self, delay=0.1, delay_offset=0.001, n_parallel=1):
        for i in range(n_parallel): 
            d = delay*i  + delay_offset
            QTimer.singleShot(d, self._dispatch)
    def _dispatch(self):
        if self.count_active() == 0:
            self.signal.progress.emit( 0)
        
        self._n_active += 1
        self._run_loop()
    def reset(self, **kw):
        self._n_active = 0


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
    def _try_finish(self):
        self._release()
        if self.count_active() == 0:
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
