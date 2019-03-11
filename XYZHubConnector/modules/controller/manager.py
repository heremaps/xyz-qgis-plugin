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
from qgis.PyQt.QtCore import Qt, QMutex, QMutexLocker
from threading import Lock
from ..controller import BasicSignal

from ..common.signal import make_print_qgis, close_print_qgis
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
        super().__init__()
        print("init",self)
        self.signal = CanvasSignal()
        self._ptr = 0
        self._lst = dict()
        self._reload_ptr = list()
        self.ld_pool = LoaderPool()
    def finish_fast(self):
        self.ld_pool.reset()
    def add_background(self, con):
        callbacks = [self.ld_pool.start_dispatch_bg, self.ld_pool.try_finish_bg]
        return self._add_cb(con, callbacks)
    def add(self, con):
        callbacks = [self.ld_pool.start_dispatch, self.ld_pool.try_finish]
        return self._add_cb(con, callbacks)
    def _add_cb(self, con, callbacks):
        start_dispatch, try_finish = callbacks
        con.signal.progress.connect(start_dispatch, Qt.QueuedConnection)

        ptr = self._add(con)
        con.signal.finished.connect( self.make_deregister_cb(ptr))

        con.signal.finished.connect( try_finish)
        con.signal.error.connect(lambda e: try_finish())
        
        return ptr
    def _add(self, con):
        ptr = self._ptr
        self._lst[ptr] = con
        self._ptr += 1
        return ptr
    def add_reload(self, con):
        ptr = self._add(con)
        self._reload_ptr.append(ptr)
        return ptr
    def make_deregister_cb(self, ptr):
        def _deregister():
            self._lst.pop(ptr, None)
        return _deregister
    
    def remove(self, layer_ids):
        idx = list()
        for i, ptr in enumerate(self._reload_ptr):
            c = self._lst[ptr]
            if c.layer is None: continue
            if not c.layer.get_layer().id() in layer_ids: continue
            self._lst.pop(ptr, None)
            idx.append(i)
        ptr = [p for i,p in enumerate(self._reload_ptr) if i not in idx]
        self._reload_ptr = ptr


    def disconnect_ux(self, iface):
        canvas = iface.mapCanvas()
        canvas.scaleChanged.disconnect( self._canvas_scale)
        canvas.extentsChanged.disconnect( self._canvas_extent)
    def connect_ux(self, iface):
        self._scaled = False
        canvas = iface.mapCanvas()
        canvas.scaleChanged.connect( self._canvas_scale)
        canvas.extentsChanged.connect( self._canvas_extent)
    def _canvas_scale(self,*a):
        self._scaled = True
    def _canvas_extent(self,*a):
        print("canvas_extent",self)
        self.signal.canvas_span.emit() # simple

        # if self._scaled:
        #     self.signal.canvas_zoom.emit()
        #     self._scaled = False
        # else:
        #     self.signal.canvas_span.emit()
    def reload_canvas(self, *a, **kw):
        for ptr in self._reload_ptr:
            self._lst[ptr].reload( *a, **kw)