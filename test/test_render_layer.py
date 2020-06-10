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
                        len_of_struct, len_of_struct_sorted, flatten,
                        format_map_fields)
from test import test_parser
from qgis.testing import unittest
from qgis.core import QgsWkbTypes, QgsProject

from XYZHubConnector.xyz_qgis.layer import XYZLayer, parser, render

# import unittest
# class TestParser(BaseTestAsync, unittest.TestCase):
class TestRenderLayer(BaseTestAsync):
    _assert_len_map_fields = test_parser.TestParser._assert_len_map_fields
    def __init__(self,*a,**kw):
        super().__init__(*a,**kw)
        test_parser.TestParser._id = lambda x: self._id()
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
            ref_map_feat, ref_map_fields = self._test_render_mixed_json_to_layer(obj)
            
            ref = dict()
            ref_len_fields = {'MultiPoint': [6, 18], 'MultiPolygon': [27]}
            ref["len_fields"] = ref_len_fields
            with self.subTest():
                self._assert_len_fields(ref_map_fields, ref_len_fields)
                ref["map_fields"] = ref_map_fields
            obj = json.loads(txt)
            self.subtest_render_mixed_json_to_layer_shuffle(obj, ref)
            obj = json.loads(txt)
            self.subtest_render_mixed_json_to_layer_multi_chunk(obj, ref)
            obj = json.loads(txt)
            self.subtest_render_mixed_json_to_layer_empty_chunk(obj, ref)

    def subtest_render_mixed_json_to_layer_multi_chunk(self, obj, ref, lst_chunk_size=None):
        if not lst_chunk_size:
            p10 = 1+len(str(len(obj["features"])))
            lst_chunk_size = [10**i for i in range(p10)]
        with self.subTest(lst_chunk_size=lst_chunk_size):
            lst_map_fields = list()
            for chunk_size in lst_chunk_size:
                map_fields = self.subtest_render_mixed_json_to_layer_chunk(obj, chunk_size)
                if map_fields is None: continue
                lst_map_fields.append(map_fields)

            for map_fields, chunk_size in zip(lst_map_fields, lst_chunk_size):
                with self.subTest(chunk_size=chunk_size):
                    self._assert_len_ref_fields(
                        map_fields, ref)
    def subtest_render_mixed_json_to_layer_shuffle(self, obj, ref, n_shuffle=5, chunk_size=10):
        with self.subTest(n_shuffle=n_shuffle):
            o = dict(obj)
            lst_map_fields = list()
            random.seed(0.5)
            for i in range(n_shuffle):
                random.shuffle(o["features"])
                map_fields = self.subtest_render_mixed_json_to_layer_chunk(o, chunk_size)
                if map_fields is None: continue
                lst_map_fields.append(map_fields)
                
            for i, map_fields in enumerate(lst_map_fields):
                with self.subTest(shuffle=i):
                    self._assert_len_ref_fields(
                        map_fields, ref)
    def subtest_render_mixed_json_to_layer_empty_chunk(self, obj, ref, chunk_size=10,empty_chunk=10):
        with self.subTest(empty_chunk=empty_chunk):
            map_fields = self.subtest_render_mixed_json_to_layer_chunk(obj, chunk_size, empty_chunk=empty_chunk)
            self.assertIsNotNone(map_fields)
            self._assert_len_ref_fields(
                map_fields, ref)

    def subtest_render_mixed_json_to_layer_chunk(self, obj, chunk_size=100, empty_chunk=None):
        with self.subTest(chunk_size=chunk_size):
            layer = self.new_layer()
            o = dict(obj)
            obj_feat = obj["features"]
            lst_map_feat = list()
            map_fields = dict()
            lst_chunk: list = [obj_feat[i0:i0+chunk_size]
            for i0 in range(0,len(obj_feat), chunk_size)]
            if empty_chunk:
                step = max(2,len(lst_chunk)//empty_chunk)
                for i in reversed(range(0, len(lst_chunk), step)):
                    lst_chunk.insert(i, list())
            for chunk in lst_chunk:
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

            self.remove_layer(layer)
            return map_fields
            
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
        map_feat, map_fields = test_parser.TestParser().do_test_parse_xyzjson_map(obj)
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

    def _assert_len_ref_fields(self, map_fields, ref, strict=False):
        if "len_fields" in ref:
            self._assert_len_fields(map_fields, ref["len_fields"], strict)
        if "map_fields" in ref:
            self._assert_len_map_fields(map_fields, ref["map_fields"], strict)

    def _assert_len_fields(self, map_fields, ref, strict=False):
        len_ = len_of_struct if strict else len_of_struct_sorted
        self.assertEqual(
            len_(map_fields), ref, "\n".join([
                "len of map_fields is not correct (vs. ref). "+
                "Please revised parser, similarity threshold.",
                format_map_fields(map_fields),
                ])
            )
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

        cnt = layer.get_feat_cnt()
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
    def remove_layer(self,layer:XYZLayer):
        for vlayer in layer.iter_layer():
            QgsProject.instance().removeMapLayer(vlayer)
    def new_layer(self):
        conn_info = dict(tags=["tags"])
        meta = dict(title="title", id="id")
        layer = XYZLayer(conn_info, meta)
        return layer
    

if __name__ == "__main__":
    unittest.main()
    