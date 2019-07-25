# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
#
###############################################################################

import json
import random
import numpy as np
import pprint

from test.utils import (BaseTestAsync, TestFolder, format_long_args,
                        len_of_struct, len_of_struct_unorder, flatten,
                        format_map_fields)
from test import test_parser
from qgis.testing import unittest
from qgis.core import QgsWkbTypes

from XYZHubConnector.modules.layer import XYZLayer, parser, render



# import unittest
# class TestParser(BaseTestAsync, unittest.TestCase):
class TestRenderLayer(BaseTestAsync):
    def test_render_mixed_json_to_layer_chunk(self):
        folder="xyzjson-small"
        fnames=[
            "mixed-xyz.geojson",
        ]
        for fname in fnames:
            self.subtest_render_mixed_json_to_layer(folder, fname)

    def subtest_render_mixed_json_to_layer(self,folder,fname):
        with self.subTest(folder=folder,fname=fname):
            resource = TestFolder(folder)
            txt = resource.load(fname)
            obj = json.loads(txt)
            self.subtest_render_mixed_json_to_layer_shuffle(obj)
            self.subtest_render_mixed_json_to_layer_multi_chunk(obj)

    def subtest_render_mixed_json_to_layer_multi_chunk(self, obj, lst_chunk_size=None):
        if not lst_chunk_size:
            p10 = 1+len(str(len(obj["features"])))
            lst_chunk_size = [10**i for i in range(p10)]
        with self.subTest(lst_chunk_size=lst_chunk_size):
            ref_map_feat, ref_map_fields = self._test_render_mixed_json_to_layer(obj)
            lst_map_fields = list()
            for chunk_size in lst_chunk_size:
                map_fields = self.subtest_render_mixed_json_to_layer_chunk(obj, chunk_size)
                if map_fields is None: continue
                lst_map_fields.append(map_fields)

            for map_fields, chunk_size in zip(lst_map_fields, lst_chunk_size):
                with self.subTest(chunk_size=chunk_size):
                    self._assert_len_map_fields(
                        ref_map_fields, map_fields)
    def subtest_render_mixed_json_to_layer_shuffle(self, obj, n_shuffle=5, chunk_size=10):
        with self.subTest(n_shuffle=n_shuffle):
            o = dict(obj)
            ref_map_feat, ref_map_fields = self._test_render_mixed_json_to_layer(obj)
            lst_map_fields = list()
            random.seed(0.5)
            for i in range(n_shuffle):
                random.shuffle(o["features"])
                map_fields = self.subtest_render_mixed_json_to_layer_chunk(obj, chunk_size)
                if map_fields is None: continue
                lst_map_fields.append(map_fields)
                
            for i, map_fields in enumerate(lst_map_fields):
                with self.subTest(shuffle=i):
                    self._assert_len_map_fields(
                        ref_map_fields, map_fields)

    def subtest_render_mixed_json_to_layer_chunk(self, obj, chunk_size=100):
        with self.subTest(chunk_size=chunk_size):
            layer = self.new_layer()
            o = dict(obj)
            obj_feat = obj["features"]

            lst_map_feat = list()
            map_fields = dict()
            for i0 in range(0,len(obj_feat), chunk_size):
                chunk = obj_feat[i0:i0+chunk_size]
                o["features"] = chunk
                map_feat, _ = parser.xyz_json_to_feature_map(o, map_fields)
                test_parser.TestParser()._assert_parsed_map(chunk, map_feat, map_fields)
                lst_map_feat.append(map_feat)
                self._render_layer(layer, map_feat, map_fields)

                # self._log_debug("len feat", len(chunk))
                # self._log_debug("parsed feat", len_of_struct(map_feat))
                # self._log_debug("parsed fields", len_of_struct(map_fields))

            lst_feat = flatten([x.values() for x in lst_map_feat])
            self.assertEqual(len(lst_feat), len(obj["features"]))

            self.assert_layer(layer, obj, map_fields)
            return map_fields
            
    def _assert_len_map_fields(self, ref, map_fields, strict=False):
        len_ = len_of_struct if strict else len_of_struct_unorder
        self.assertEqual(
            len_(map_fields), len_(ref),
            format_map_fields(map_fields)+"\n"+
            format_map_fields(ref))

    def _assert_rendered_fields(self, vlayer, fields):
        name_vlayer_fields = vlayer.fields().names()
        name_fields = fields.names()

        self.assertEqual(name_vlayer_fields, name_fields, 
            "layer fields and parsed fields mismatch. len: %s and %s" %
            (len(name_vlayer_fields), len(name_fields))
        )

    def _test_render_mixed_json_to_layer(self, obj):
        layer = self.new_layer()
        # map_feat, map_fields = parser.xyz_json_to_feature_map(obj)
        map_feat, map_fields = test_parser.TestParser()._test_parse_xyzjson_map(obj)
        self._render_layer(layer, map_feat, map_fields)
        self.assert_layer(layer, obj, map_fields)
        return map_feat, map_fields
        
    def _render_layer(self, layer, map_feat, map_fields):
        for geom_str in map_feat:
            for idx,(feat, fields) in enumerate(zip(
                map_feat[geom_str], map_fields[geom_str])):
                vlayer = (
                    layer.get_layer(geom_str, idx) 
                    if layer.has_layer(geom_str, idx)
                    else layer.add_ext_layer(geom_str, idx))
                ok, out_feat = render.add_feature_render(vlayer, feat, fields)
                if not ok:
                    self._log_debug(ok, len(feat), len(out_feat), vlayer.id())
                    # self._log_info("\n\n".join(
                    #     [str(ft["properties"].keys()) for ft in obj["features"]]))

                self._assert_rendered_fields(vlayer, fields)

    def assert_layer(self, layer, obj, map_fields):
        lst_vlayer = list(layer.iter_layer())
        map_vlayer = layer.map_vlayer

        len_fields = len_of_struct(map_fields) # field cnt
        len_vlayer = len_of_struct(map_vlayer) # feat cnt
        len_vlayer_fields = dict(
            (geom_str, [len(x.fields()) for x in lst])
            for geom_str, lst in map_vlayer.items()
            )
        
        # self._log_debug("feat layer", len_vlayer)
        # self._log_debug("fields layer", len_vlayer_fields)

        self.assertGreater(len(lst_vlayer), 0)

        cnt = sum(x.featureCount() for x in lst_vlayer)
        self.assertEqual(cnt, len(obj["features"]), len_vlayer)

        
        name_vlayer_fields = dict(
            (geom_str,
            [x.fields().names() for x in lst])
            for geom_str, lst in map_vlayer.items()
            )

        name_map_fields = dict(
            (geom_str,
            [x.names() for x in lst])
            for geom_str, lst in map_fields.items()
            )
        self.assertEqual(len_vlayer_fields, len_fields, "\n".join([
            "layer fields and map_fields mismatch",
            pprint.pformat(name_vlayer_fields, compact=True),
            pprint.pformat(name_map_fields, compact=True)
            ])
        )
        self.assertEqual(name_vlayer_fields, name_map_fields)
                    
        # lst_feat = list(vlayer.getFeatures())
        # self._log_debug(lst_feat)
    def new_layer(self):
        conn_info = dict(tags=["tags"])
        meta = dict(title="title", id="id")
        layer = XYZLayer(conn_info, meta)
        return layer
    
if __name__ == "__main__":
    unittest.main()
    