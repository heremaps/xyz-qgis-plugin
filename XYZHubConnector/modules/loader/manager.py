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
from .layer_loader import (InitUploadLayerController, LoadLayerController,
                           UploadLayerController)
from .space_loader import (CreateSpaceController, DeleteSpaceController,
                           EditSpaceController, LoadSpaceController,
                           StatSpaceController)

from ..common.signal import make_print_qgis
print_qgis = make_print_qgis("controller_manager")

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
        print_qgis("start_dispatch", self.count_active())
        # if progress > 0: return
        self._dispatch()
        self.signal.progress.emit( self.count_active())
    def try_finish(self):
        print_qgis("try_finish", self.count_active())
        self._release()
        if self.count_active() == 0:
            self.signal.finished.emit()
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
        self.ld_pool = LoaderPool()
    def finish_fast(self):
        self.ld_pool.reset()
    def add_on_demand_controller(self, con, show_progress=True):
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
        con.signal.finished.connect( try_finish, Qt.QueuedConnection)
        con.signal.error.connect(lambda e: try_finish(), Qt.QueuedConnection)
        
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

class LayerControllerManager(ControllerManager):
    def __init__(self):
        super().__init__()
        self._layer_ptr = dict()
        self._static_ptr = set()
    def reset(self):
        self.unload()
    def make_register_xyz_layer_cb(self, con, ptr):
        def _register_xyz_layer():
            # assert con.layer is not None 
            self._layer_ptr[con.layer.get_id()] = ptr
        return _register_xyz_layer
    def get_loader(self, xlayer_id):
        return self._lst.get(self._layer_ptr.get(xlayer_id))
    def get_interactive_loader(self, xlayer_id):
        if self._layer_ptr.get(xlayer_id) in self._static_ptr: return
        return self.get_loader(xlayer_id)
    def get_all_static_loader(self):
        return [self._lst.get(ptr) for ptr in self._static_ptr if ptr in self._lst]
    def add_static_loader(self, con, show_progress=True):
        ptr = self.add_persistent_loader(con, show_progress)
        self._static_ptr.add(ptr)
        return ptr
    def add_persistent_loader(self, con, show_progress=True):
        callbacks = [self.ld_pool.start_dispatch_bg, self.ld_pool.try_finish_bg] if show_progress else None
        
        ptr = self._add(con)
        # con.signal.finished.connect( self.make_deregister_cb(ptr))
        # con.signal.error.connect( self.make_deregister_cb(ptr))
        if callbacks is not None: 
            start_dispatch, try_finish = callbacks
            con.signal.progress.connect(start_dispatch, Qt.QueuedConnection)
            con.signal.finished.connect( try_finish, Qt.QueuedConnection)
            con.signal.error.connect(lambda e: try_finish(), Qt.QueuedConnection)
        
        cb_register_layer = self.make_register_xyz_layer_cb(con, ptr)
        if con.layer is None:
            con.signal.progress.connect(cb_register_layer,
                Qt.QueuedConnection)
        else: 
            cb_register_layer()

        return ptr

    def remove_persistent_loader(self, xlayer_id):
        self._static_ptr.discard(xlayer_id)
        ptr = self._layer_ptr.pop(xlayer_id, None)
        con = self._lst.pop(ptr, None)
        if con:
            con.destroy()
        
    def unload(self):
        for xid, ptr in self._layer_ptr.items():
            con = self._lst.pop(ptr, None)
            if con:
                con.destroy()

                
class LoaderManager(LayerControllerManager):
    def config(self, network):
        self.network = network
        self._map_fun_con = dict()
        self._map_fun_cls = {
            "list": LoadSpaceController,
            "stat": StatSpaceController,
            "delete": DeleteSpaceController,
            "edit": EditSpaceController,
            "create": CreateSpaceController
        }
    def get_con(self,key):
        return self._map_fun_con[key]
    def make_con(self,key):
        if key not in self._map_fun_cls: 
            raise Exception("Unknown key: %s (Available keys: %s)"%(key, ", ".join(self._map_fun_cls.keys())))
        C = self._map_fun_cls[key]
        con = C(self.network)
        self._map_fun_con[key] = con
        return con

