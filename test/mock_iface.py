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
def make_iface_canvas():
    my_iface = mock.Mock(spec=QgisInterface)

    my_iface.mainWindow.return_value = QMainWindow()

    # canvas = QgsMapCanvas(my_iface.mainWindow())
    canvas = MyCanvas()
    canvas.setDestinationCrs(QgsCoordinateReferenceSystem(4326))
    canvas.setFrameStyle(0)
    canvas.resize(400, 400)
    my_iface.mapCanvas.return_value = canvas
    return my_iface
