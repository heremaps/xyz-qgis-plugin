# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from test.utils import BaseTestAsync, BaseTestWorkerAsync, add_test_fn_params, get_env
from qgis.testing import start_app, unittest 
from XYZHubConnector.modules import basemap

import os

APP_ID=os.environ["APP_ID"]
APP_CODE=os.environ["APP_CODE"]

app = start_app()

class TestBasemap(BaseTestWorkerAsync):
    def test_basemap(self):
        iface = self.make_iface()
        
        import os
        d = os.path.dirname(basemap.__file__)
        t = basemap.load_xml(os.path.join(d,"basemap.xml"))
        lst = list(t.values())

        from qgis.core import QgsRasterLayer, QgsProject, QgsVectorLayer
        for k,v in t.items():
            canvas = self.show_canvas(iface)
            canvas.setWindowTitle(k)

            basemap.add_auth(v,app_id=APP_ID, app_code=APP_CODE)
            u = basemap.parse_uri(v)
            self._log_debug(k,u)
            layer = QgsRasterLayer( u, k, "wms")

            # QgsProject.instance().addMapLayer(layer)
            canvas.setLayers([layer])
            self.canvas_zoom_to_layer(canvas, layer)
        
            self._wait_async()

    def make_iface(self):
        # from qgis.utils import iface # None
        from test import mock_iface
        iface = mock_iface.make_iface_canvas()
        return iface
    def canvas_zoom_to_layer(self, canvas, layer):
        layer.setCrs(canvas.mapSettings().destinationCrs())
        extent = layer.extent()
        extent.scale(1.05)
        canvas.setExtent(extent)
        if canvas.isCachingEnabled():
            layer.triggerRepaint()  # if caching enabled
        else:
            canvas.refresh()
        # canvas.waitWhileRendering()
    def show_canvas(self, iface):
        canvas = iface.mapCanvas()
        canvas.closed.connect(self._stop_async)
        canvas.show()
        return canvas
if __name__ == "__main__":
    
    # unittest.main()
    tests = [
        "TestBasemap.test_basemap"
    ]
    unittest.main(defaultTest = tests)