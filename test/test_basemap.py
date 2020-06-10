# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from test import mock_iface
from test.utils import (BaseTestAsync, BaseTestWorkerAsync, add_test_fn_params,
                        get_env)

from qgis.testing import start_app, unittest

from qgis.core import QgsRasterLayer, QgsProject
from XYZHubConnector.xyz_qgis import basemap

import os

APP_ID=os.environ["APP_ID"]
APP_CODE=os.environ["APP_CODE"]

app = start_app()

class TestBasemap(BaseTestWorkerAsync):
    def test_basemap(self):
        iface = mock_iface.make_iface_canvas(self)
        
        d = os.path.dirname(basemap.__file__)
        t = basemap.load_xml(os.path.join(d,"basemap.xml"))
        lst = list(t.values())

        for k,v in t.items():
            canvas = mock_iface.show_canvas(iface)
            canvas.setWindowTitle(k)

            basemap.add_auth(v,app_id=APP_ID, app_code=APP_CODE)
            u = basemap.parse_uri(v)
            self._log_debug(k,u)
            layer = QgsRasterLayer( u, k, "wms")

            # QgsProject.instance().addMapLayer(layer)
            canvas.setLayers([layer])
            mock_iface.canvas_zoom_to_layer(canvas, layer)
        
            self._wait_async()
if __name__ == "__main__":
    
    # unittest.main()
    tests = [
        "TestBasemap.test_basemap"
    ]
    unittest.main(defaultTest = tests)
