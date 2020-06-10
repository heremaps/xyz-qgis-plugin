# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


from qgis.testing import start_app, unittest 
from test.utils import (BaseTestAsync, BaseTestWorkerAsync, 
    add_test_fn_params, get_token_space, 
    get_conn_info, AllErrorsDuringTest)
from test.test_layer_loader import TestReLoader, TestLoader
from XYZHubConnector.xyz_qgis.network import NetManager
from XYZHubConnector.xyz_qgis.loader import TileLayerLoader, EmptyXYZSpaceError
from XYZHubConnector.xyz_qgis.layer import bbox_utils, tile_utils, layer_utils

from qgis.core import QgsProject
from qgis.PyQt.QtCore import QTimer

app = start_app()
network = NetManager(app)


class TestTileLoader(TestLoader):
    flag_canvas = False
    def _test_load_small_layer(self, n_parallel, **kw_start):
        conn_info = get_conn_info("water")
        meta = dict(id="unittest",title="unittest",description="unittest")
        feat_cnt = 527
        kw = dict(kw_start)

        schema = "here"
        # level, rect = 1, (-165.7,-71.4 , 160.8,93.7) # fail
        # level, rect = 1, (-180,-90,181,91) # fail
        # level, rect = 1, (-180,-90,180,90) # ok
        # level, rect = 7, (4.7,47.4 , 16.3,55.2)
        level, rect = 1, (4.7,47.4 , 16.3,55.2) # test interrupt

        kw.update(dict(  
            rect=rect,
            level=level,
            tile_schema=schema
            ))
        self.subtest_load_layer(conn_info, meta, feat_cnt, n_parallel, **kw)
        
    def subtest_load_layer(self, conn_info, meta, feat_cnt, n_parallel, **kw_start):
        limit = kw_start.get("limit", 30000)
        layer = None
        with self.subTest(conn_info=conn_info.get_xyz_space(), #meta=meta, 
        feat_cnt=feat_cnt,n_parallel=n_parallel,**kw_start):
            loader = self._make_load_controller(n_parallel)

            layer = self._load_layer(loader, conn_info, meta, **kw_start)
            self._assert_layer(layer, feat_cnt, limit)

        if self.flag_canvas: self._wait_async()
        return layer
     
    def _assert_layer(self, layer, feat_cnt, limit):
        feat_cnt_layer = layer.get_feat_cnt()
        self._log_debug("Feature count", feat_cnt_layer)
        if feat_cnt is None: return
        with self.subTest(actual_cnt=feat_cnt_layer):
            self.assertGreaterEqual(feat_cnt_layer, limit, "check feat_cnt lower bound")  
            self.assertLessEqual(feat_cnt_layer, feat_cnt, "check feat_cnt upper bound")
            self.assertEqual(feat_cnt_layer, feat_cnt, "check exact feat_cnt")
    def _make_load_controller(self, n_parallel):
        loader = TileLayerLoader(network, n_parallel=n_parallel)
        
        for f in loader.get_lst_fun():
            pass
            # self._log_debug("lst_fun", f)
            # f.signal.results.connect(self._log_debug)
            # f.signal.results.connect( self._add_output)

        loader.signal.finished.connect( self._stop_async)
        loader.signal.error.connect( self._handle_error)
        loader.signal.error.connect( self._add_output)
        return loader
    def _split_rect(self, rect_all, n_x=5, n_y=5):
        step_x = (rect_all[2] - rect_all[0]) / n_x
        step_y = (rect_all[3] - rect_all[1]) / n_y

        lst_x0 = [rect_all[0] + i*step_x for i in range(n_x)]
        lst_x1 = lst_x0[1:] + [rect_all[2]]
        lst_y0 = [rect_all[1] + i*step_y for i in range(n_y)]
        lst_y1 = lst_y0[1:] + [rect_all[3]]
        lst_rect = [(x0,y0,x1,y1) 
        for x0,x1 in zip(lst_x0, lst_x1)
        for y0,y1 in zip(lst_y0, lst_y1)
        ]
        return lst_rect
    def _load_layer(self, loader, conn_info, meta, **kw_start):
        self.canvas = self.canvas_init()

        rect,level,tile_schema = [kw_start[k] for k in ["rect","level","tile_schema"]]

        # for i, rect in enumerate(self._split_rect(rect,2,2)):
        
        for i,limit in enumerate([10,20,30,40]):
            self._log_debug(rect)
            kw_start["tile_ids"] = tile_utils.bboxToListColRow(*rect,level,tile_schema)
            kw_start["limit"] = limit
            if not i:
                loader.start(conn_info, meta, **kw_start)
            else:
                loader.restart(conn_info, meta, **kw_start)

            # self._process_async()
            # import time 
            # time.sleep(1)
            # self._process_async()

            # QTimer.singleShot(100, self._stop_async) # early interrupt
            self._wait_async()
            
            lst_layer = list(loader.layer.iter_layer())
            if not lst_layer: continue

            if self.flag_canvas:
                self.canvas.setLayers(lst_layer)
                self.canvas_zoom_to_layer(self.canvas, lst_layer[0])
        return loader.layer

    def _wait_async(self):
        try: 
            super()._wait_async()
        except AllErrorsDuringTest as e:
            lst_err = e.args[0]
            for err in lst_err:
                if not isinstance(err, EmptyXYZSpaceError):
                    raise e

    def canvas_init(self):
        from test import mock_iface
        iface = mock_iface.make_iface_canvas(self)
        canvas = iface.mapCanvas()
        canvas.closed.connect(self._stop_async)
        if self.flag_canvas: canvas.show()
        return canvas

    def canvas_zoom_to_layer(self, canvas, vlayer):
        vlayer.triggerRepaint(False)
        extent = vlayer.extent()
        extent.scale(1.05)
        canvas.setExtent(extent)
        canvas.refresh()
        canvas.waitWhileRendering()

for n_parallel in [1,2,4,8]:
    add_test_fn_params(TestTileLoader,"_test_load_small_layer",n_parallel=n_parallel)
    add_test_fn_params(TestTileLoader,"_test_load_large_layer",n_parallel=n_parallel)
    for limit in [100,250,1000,100000]:
        add_test_fn_params(TestTileLoader,"_test_load_small_layer",n_parallel=n_parallel, limit=limit)
        add_test_fn_params(TestTileLoader,"_test_load_large_layer",n_parallel=n_parallel, limit=limit)



if __name__ == "__main__":
    import sys
    if "--canvas" in sys.argv:
        TestTileLoader.flag_canvas = True
        sys.argv.remove("--canvas")

    
    # unittest.main()
    tests = [
        "TestTileLoader.test_load_small_layer_n_parallel_2_limit_100",
        "TestTileLoader.test_load_small_layer_n_parallel_2_limit_250",

        # "TestTileLoader.test_load_small_layer_n_parallel_2_limit_100000",
        # "TestTileLoader.test_load_large_layer_n_parallel_2_limit_1000",

        # "TestTileLoader.test_load_large_layer_n_parallel_2_limit_100",
        # "TestTileLoader.test_load_small_layer_n_parallel_4_limit_100000", # large limit: test retry
        # "TestTileLoader.test_load_small_layer_n_parallel_4_limit_100",
        # "TestTileLoader.test_load_small_layer_n_parallel_2",
        # "TestTileLoader.test_load_small_layer_n_parallel_4",
        # "TestTileLoader.test_load_small_layer_n_parallel_8",
    ]
    # unittest.main(defaultTest = tests, failfast=True) # will not run all subtest
    unittest.main(defaultTest = tests)
    