# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import mock
from qgis.gui import QgisInterface, QgsMapCanvas
from qgis.core import QgsCoordinateReferenceSystem
from qgis.PyQt.QtWidgets import QMainWindow
from qgis.PyQt.QtCore import pyqtSignal

class MyCanvas(QgsMapCanvas):
    closed = pyqtSignal()
    def closeEvent(self,event):
        super().closeEvent(event)
        print("closing")
        self.closed.emit()
# /python/testing/mocked.py
def make_iface_canvas(test_async):
    my_iface = mock.Mock(spec=QgisInterface)

    my_iface.mainWindow.return_value = QMainWindow()

    canvas = MyCanvas()
    canvas.setDestinationCrs(QgsCoordinateReferenceSystem(4326))
    canvas.setFrameStyle(0)
    canvas.resize(400, 400)
    canvas.closed.connect(test_async._stop_async)
    
    my_iface.mapCanvas.return_value = canvas
    return my_iface

def canvas_zoom_to_layer(canvas, layer):
    layer.setCrs(canvas.mapSettings().destinationCrs())
    extent = layer.extent()
    extent.scale(1.05)
    canvas.setExtent(extent)
    if canvas.isCachingEnabled():
        layer.triggerRepaint()  # if caching enabled
    else:
        canvas.refresh()
    # canvas.waitWhileRendering()
def show_canvas(iface):
    canvas = iface.mapCanvas()
    canvas.show()
    return canvas