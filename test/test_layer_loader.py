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
from XYZHubConnector.xyz_qgis.network import NetManager
from XYZHubConnector.xyz_qgis.loader import LoadLayerController, ManualInterrupt

from qgis.core import QgsProject
from qgis.PyQt.QtCore import QTimer

app = start_app()
network = NetManager(app)


class TestLoader(BaseTestWorkerAsync):
    """ test layer loader (chain of network, handler, parser, render, then repeat (after parser))
    """
    def test_load_small_layer(self):
        self._test_load_small_layer(n_parallel=1)
    def _test_load_small_layer(self, n_parallel, **kw_start):
        conn_info = get_conn_info("water")
        meta = dict(id="unittest",title="unittest",description="unittest")
        feat_cnt = 527
        kw = dict(kw_start)
        kw.update(dict(  
            max_feat=600
            ))
        self.subtest_load_layer(conn_info, meta, feat_cnt, n_parallel, **kw)

        # conn_info = get_conn_info("playground-pa")
        # meta = dict(id="unittest",title="unittest",description="unittest")
        # feat_cnt = 461
        # kw = dict(kw_start)
        # self.subtest_load_layer(conn_info, meta, feat_cnt, n_parallel,  **kw)
    def subtest_load_layer(self, conn_info, meta, feat_cnt, n_parallel, **kw_start):
        if feat_cnt is not None:
            feat_cnt = min(feat_cnt, max(
                kw_start.get("max_feat", feat_cnt), 
                kw_start.get("limit", 30000)
                ))
        with self.subTest(conn_info=conn_info.get_xyz_space(), #meta=meta, 
        feat_cnt=feat_cnt,n_parallel=n_parallel,**kw_start):
            loader = self._make_load_controller(n_parallel)
            layer = self._load_layer(loader, conn_info, meta, **kw_start)
            self._assert_layer(layer, feat_cnt)
            return layer
    def _load_layer(self, loader, conn_info, meta, **kw_start):
        loader.start(conn_info, meta, **kw_start)
        self._wait_async()
        return loader.layer
    def _assert_layer(self, layer, feat_cnt):
        feat_cnt_layer = layer.get_feat_cnt()
        self._log_debug("Feature count", feat_cnt_layer)
        if feat_cnt is None: return
        with self.subTest(actual_cnt=feat_cnt_layer):
            self.assertEqual(feat_cnt_layer, feat_cnt)
    def _make_load_controller(self, n_parallel):
        loader = LoadLayerController(network, n_parallel=n_parallel)
        
        for f in loader.get_lst_fun():
            pass
            # self._log_debug("lst_fun", f)
            # f.signal.results.connect(self._log_debug)
            # f.signal.results.connect( self._add_output)

        loader.signal.finished.connect( self._stop_async)
        loader.signal.error.connect( self._handle_error)
        loader.signal.error.connect( self._add_output)
        return loader


    def _test_load_large_layer(self, n_parallel, **kw_start):
        # load connection
        # conn_info_src = get_conn_info("playground-building")
        # meta = dict(id="unittest",title="unittest", description="playground-building")
        # feat_cnt = 137798
        # self._test_load_layer(conn_info_src, meta, feat_cnt, n_parallel, limit)


        conn_info_src = get_conn_info("uom_world_carto")
        meta = dict(id="unittest",title="unittest", description="uom_world_carto")
        feat_cnt = 50573442 
        kw = dict(kw_start)
        kw.update(dict( 
            max_feat=2000
            ))
        self.subtest_load_layer(conn_info_src, meta, feat_cnt, n_parallel, **kw)

        # # taking very long
        # conn_info_src = get_conn_info("uom_world_road")
        # meta = dict(id="unittest",title="unittest", description="uom_world_road")
        # feat_cnt = None
        # self._test_load_layer(conn_info_src, meta, feat_cnt, n_parallel, limit)


        conn_info_src = get_conn_info("uom_world_building")
        meta = dict(id="unittest",title="unittest", description="uom_world_building")
        feat_cnt = None
        kw = dict(kw_start)
        kw.update(dict( 
            max_feat=2000
            ))
        self.subtest_load_layer(conn_info_src, meta, feat_cnt, n_parallel, **kw)

    def test_load_multi_start(self):
        pass
    def test_load_multi_start_async(self):
        pass
        
    def setUp(self):
        QgsProject.instance().removeAllMapLayers()
        super().setUp()


class TestReLoader(TestLoader):
    def _load_layer(self, loader, conn_info, meta, **kw_start):
        lst_layer = list()
        batch = 100 # kw_start.get("limit",30000)
        for i in range(6):
            timer = QTimer()
            timer.timeout.connect(lambda: self.check_loader(loader,batch))
            if not i:
                loader.start(conn_info, meta, **kw_start)
            else:
                loader.restart(conn_info, meta, **kw_start)

            timer.start(10)
            try:
                self._wait_async()
            except AllErrorsDuringTest as e:
                lst_err = e.args[0]
                self.assertIsInstance(lst_err[0], ManualInterrupt)
            finally:
                timer.stop()
                lst_layer.append(loader.layer)
                
            # with self.assertRaises(AllErrorsDuringTest, msg="stopping loader should emit error") as cm: 
            #     self._wait_async()
            # lst_err = cm.exception.args[0]
            # self.assertIsInstance(lst_err[0], ManualInterrupt)
        
        return lst_layer
    def _assert_layer(self, lst_layer, feat_cnt):
        batch = 100 # kw_start.get("limit",30000)
        cnt = min(batch, feat_cnt)
        for i, layer in enumerate(lst_layer):
            with self.subTest(layer=i):
                self.assertIs(layer,lst_layer[0])
                super()._assert_layer(layer, cnt)
    
    def check_loader(self,loader,feat_cnt):
        if not hasattr(loader,"layer"):
            return
        # self._log_debug("cnt",loader.get_feat_cnt())
        if loader.get_feat_cnt() >= feat_cnt:
            self._log_debug("\n\n\n\nstop loop",loader.get_feat_cnt())

            loader.stop_loop()


for n_parallel in [1,2,4,8]:
    add_test_fn_params(TestLoader,"_test_load_small_layer",n_parallel=n_parallel)
    add_test_fn_params(TestLoader,"_test_load_large_layer",n_parallel=n_parallel)
    for limit in [100,1000,100000]:
        add_test_fn_params(TestLoader,"_test_load_small_layer",n_parallel=n_parallel, limit=limit)
        add_test_fn_params(TestLoader,"_test_load_large_layer",n_parallel=n_parallel, limit=limit)

        add_test_fn_params(TestReLoader,"_test_load_small_layer",n_parallel=n_parallel, limit=limit)



if __name__ == "__main__":
    # unittest.main()
    tests = [
        # "TestReLoader.test_load_small_layer_n_parallel_1_limit_100",
        "TestReLoader.test_load_small_layer_n_parallel_2_limit_100",

        # "TestLoader.test_load_small_layer_n_parallel_2_limit_100",
        # "TestLoader.test_load_small_layer_n_parallel_2_limit_100000",
        # "TestLoader.test_load_large_layer_n_parallel_2_limit_1000",

        # "TestLoader.test_load_large_layer_n_parallel_2_limit_100",
        # "TestLoader.test_load_small_layer_n_parallel_4_limit_100000", # large limit: test retry
        # "TestLoader.test_load_small_layer_n_parallel_4_limit_100",
        # "TestLoader.test_load_small_layer_n_parallel_2",
        # "TestLoader.test_load_small_layer_n_parallel_4",
        # "TestLoader.test_load_small_layer_n_parallel_8",
    ]
    # unittest.main(defaultTest = tests, failfast=True) # will not run all subtest
    unittest.main(defaultTest = tests)
    