# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
#
###############################################################################

from qgis.PyQt.QtCore import pyqtSignal, QObject, Qt

class CanvasSignal(QObject):
    canvas_zoom = pyqtSignal()
    canvas_span = pyqtSignal()
    scale = pyqtSignal("double")
    extent = pyqtSignal()
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
    def __del__(self):
        # del self._lst
        # del self.signal
        print("del",self)
    def add(self, con):
        ptr = self._add(con)
        con.signal.finished.connect( self.make_deregister_cb(ptr))
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