# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from threading import Lock

from qgis.PyQt.QtCore import QMutex, QMutexLocker, QObject, Qt, pyqtSignal

from ..controller import BasicSignal
from .layer_loader import (InitUploadLayerController, ReloadLayerController,
                           UploadLayerController)
from .space_loader import (CreateSpaceController, DeleteSpaceController,
                           EditSpaceController, LoadSpaceController,
                           StatSpaceController)

from ..common.signal import close_print_qgis, make_print_qgis
print_qgis = make_print_qgis("controller_manager",debug=True)

class CanvasSignal(QObject):
    canvas_zoom = pyqtSignal()
    canvas_span = pyqtSignal()
    scale = pyqtSignal("double")
    extent = pyqtSignal()

    

class LoaderPool(object):
    def __init__(self):
        self.signal = BasicSignal()
        self._n_active = 0
        self._n_background = 0
        # self.mutex = QMutex()
        self.lock = Lock()
    def count_active(self):
        return self._n_active
    def start_dispatch_bg(self, progress):
        self._n_background += 1
        self.start_dispatch(progress)
    def try_finish_bg(self):
        self._n_background -= 1
        self.try_finish()
    def start_dispatch(self, progress):
        # if progress > 0: return

        self._dispatch()
        self.signal.progress.emit( self.count_active())

        print_qgis("dispatch", progress, self.count_active() )
    def try_finish(self):
        self._release()
        
        if self.count_active() == 0:
            self.signal.finished.emit()
        
        print_qgis("try_finish", self.count_active())
        
    def _dispatch(self):
        # locker = QMutexLocker(self.mutex)
        with self.lock:
            self._n_active += 1
    def _release(self):
        with self.lock:
            self._n_active = max(0, self._n_active - 1)
    def reset(self):
        self._n_active = self._n_background
        if self.count_active() == 0:
            self.signal.finished.emit()

class ControllerManager(object):
    """ simply store a list of Controller object inside
    """
    def __init__(self):
        self.signal = CanvasSignal()
        self._ptr = 0
        self._lst = dict()
        self._layer_ptr = dict()
        self.ld_pool = LoaderPool()
    def finish_fast(self):
        self.ld_pool.reset()
    def add_background(self, con, show_progress=True):
        """ background controller will not get affected when finish_fast()
        """
        callbacks = [self.ld_pool.start_dispatch_bg, self.ld_pool.try_finish_bg] if show_progress else None
        return self._add_cb(con, callbacks)
    def add(self, con, show_progress=True):
        """ controller will be forced to finish from the pool when finish_fast()
        """
        callbacks = [self.ld_pool.start_dispatch, self.ld_pool.try_finish] if show_progress else None
        return self._add_cb(con, callbacks)
    def _add_cb(self, con, callbacks):
        # ptr = 0
        ptr = self._add(con)
        con.signal.finished.connect( self.make_deregister_cb(ptr))
        con.signal.error.connect( self.make_deregister_cb(ptr))
        if callbacks is None: 
            return ptr
        start_dispatch, try_finish = callbacks
        con.signal.progress.connect(start_dispatch, Qt.QueuedConnection)
        con.signal.finished.connect( try_finish)
        con.signal.error.connect(lambda e: try_finish())
        
        return ptr
    def _add(self, con):
        ptr = self._ptr
        self._lst[ptr] = con
        self._ptr += 1
        return ptr
        
    def make_deregister_cb(self, ptr):
        def _deregister(*a):
            self._lst.pop(ptr, None)
        return _deregister
    
    def remove(self, layer_ids):
        idx = list()
        for i in layer_ids:
            for ptr in self._layer_ptr.get(i,list()):
                self._lst.pop(ptr, None)



class LoaderManager(ControllerManager):
    def config(self, network):
        super().__init__()
        self.network = network
        self._map_fun_con = {
            "list": LoadSpaceController(network),
            "stat": StatSpaceController(network),
            "delete": DeleteSpaceController(network),
            "edit": EditSpaceController(network),
            "create": CreateSpaceController(network)
        }
        
        self._map_layer_con_cls = {
            "load":ReloadLayerController, 
            "feat":InitUploadLayerController, 
            "upload":UploadLayerController
        }
        self._map_layer_con = dict()
    def get_con(self,key):
        return self._map_fun_con[key]

    def new_layer_con(self, key, layer):
        C = self._map_layer_con_cls[key]
        con = C(self.network)
        self._map_layer_con[(key, layer)] = con
        self.add_background(con)
        return con
