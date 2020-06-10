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

from test.utils import (BaseTestAsync, TestFolder, format_long_args,
                        len_of_struct, len_of_struct_sorted, flatten,
                        format_map_fields)

from qgis.core import QgsFields, QgsVectorLayer
from qgis.testing import unittest
from XYZHubConnector.xyz_qgis.layer import parser


# import unittest
# class TestParser(BaseTestAsync, unittest.TestCase):
class TestParser(BaseTestAsync):
    def __init__(self,*a,**kw):
        super().__init__(*a,**kw)
        self.similarity_threshold=80
    ######## Parse xyz geojson -> QgsFeature 
    def test_parse_xyzjson(self):
        folder = "xyzjson-small"
        fnames = [
            "airport-xyz.geojson",
            "water-xyz.geojson"
            ]
        for fname in fnames:
            self.subtest_parse_xyzjson(folder,fname)
    def subtest_parse_xyzjson(self,folder,fname):
        with self.subTest(folder=folder,fname=fname):
            resource = TestFolder(folder)
            
            txt = resource.load(fname)
            obj = json.loads(txt)
            obj_feat = obj["features"]
            fields = QgsFields()
            feat = [parser.xyz_json_to_feat(ft, fields) for ft in obj_feat]

            self._assert_parsed_fields(obj_feat, feat, fields)
            self._assert_parsed_geom(obj_feat, feat, fields)
    def _assert_parsed_fields_unorder(self, obj_feat, feat, fields):
        # self._log_debug(fields.names())
        # self._log_debug("debug id, json vs. QgsFeature")
        # self._log_debug([o["id"] for o in obj_feat])
        # self._log_debug([ft.attribute(parser.QGS_XYZ_ID) for ft in feat])

        names = fields.names()
        self.assertTrue(parser.QGS_XYZ_ID in names, 
            "%s %s" % (len(names), names))
        self.assertEqual( len(obj_feat), len(feat))

    def _assert_parsed_fields(self, obj_feat, feat, fields):
        self._assert_parsed_fields_unorder(obj_feat, feat, fields)

        def msg_fields(obj):
            return (
                "{sep}{0}{sep}{1}"
                "{sep}fields-props {2}"
                "{sep}props-fields {3}"
                "{sep}json {4}"
                .format(*tuple(map(
                    lambda x: "%s %s" % (len(x), x), [
                    obj_props, 
                    fields.names(),
                    set(fields.names()).difference(obj_props),
                    set(obj_props).difference(fields.names())
                    ])),
                    format_long_args(json.dumps(obj)),
                    sep="\n>> ")
                )
            
        for o in obj_feat:
            obj_props = list(o["properties"].keys())
            self.assertLessEqual( len(obj_props), fields.size(), msg_fields(o))
            self.assertTrue( set(obj_props) < set(fields.names()), msg_fields(o))
            # self.assertEqual( obj_props, fields.names(), msg_fields(o)) # strict assert
            
    def _assert_parsed_geom_unorder(self, obj_feat, feat, fields, geom_str):
        for ft in feat:
            geom = json.loads(ft.geometry().asJson()) # limited to 13 or 14 precison (ogr.CreateGeometryFromJson)
            self.assertEqual(geom["type"], geom_str)

    def _assert_parsed_geom(self, obj_feat, feat, fields):

        # both crs is WGS84
        for o, ft in zip(obj_feat, feat):
            geom = json.loads(ft.geometry().asJson()) # limited to 13 or 14 precison (ogr.CreateGeometryFromJson)
            obj_geom = o["geometry"]

            self.assertEqual(geom["type"], obj_geom["type"])

            id_ = ft.attribute(parser.QGS_XYZ_ID)
            obj_id_ = o["id"]
            self.assertEqual(id_, obj_id_)

            # self._log_debug(geom)
            # self._log_debug(obj_geom)

            # coords = obj_geom["coordinates"]
            # obj_geom["coordinates"] = [round(c, 13) for c in coords]
            # obj_geom["coordinates"] = [float("%.13f"%c) for c in coords]
            # self.assertDictEqual(geom, obj_geom) # precision
            # for c1, c2 in zip(geom["coordinates"], obj_geom["coordinates"]):
                # self.assertAlmostEqual(c1, c2, places=13)
            
            c1 = np.array(obj_geom["coordinates"])
            c2 = np.array(geom["coordinates"])
            if c1.shape != c2.shape:
                self._log_debug(
                    "\nWARNING: Geometry has mismatch shape",
                    c1.shape, c2.shape,
                    "\nOriginal geom has problem. Testing parsed geom..")
                self.assertEqual(c2.shape[-1], 2, 
                    "parsed geom has wrong shape of coord")
                continue
            else:
                self.assertLess( np.max(np.abs(c1 - c2)), 1e-13,
                    "parsed geometry error > 1e-13")
    # @unittest.skip("large")
    def test_parse_xyzjson_large(self):
        folder = "xyzjson-large"
        fnames = [
            "cmcs-osm-dev-building-xyz.geojson",
            "cmcs-osm-dev-building-xyz-30000.geojson",
        ]
        for fname in fnames:
            self.subtest_parse_xyzjson(folder,fname)
    
    ######## Parse xyz geojson -> struct of geom: [fields], [[QgsFeature]]
    def test_parse_xyzjson_map(self):
        folder = "xyzjson-small"
        fnames = [
            "mixed-xyz.geojson",
        ]
        for fname in fnames:
            self.subtest_parse_xyzjson_map(folder,fname)
        
        mix_fnames = [
            "airport-xyz.geojson",
            "water-xyz.geojson",
        ]
        self.subtest_parse_xyzjson_mix(folder,mix_fnames)
    def test_parse_xyzjson_map_similarity_0(self):
        s = self.similarity_threshold
        self.similarity_threshold = 0
        try:
            folder = "xyzjson-small"
            fnames = [
                "mixed-xyz.geojson",
            ]
            
            for fname in fnames:
                with self.subTest(folder=folder,fname=fname,
                similarity_threshold=self.similarity_threshold):
                    map_fields = self._parse_xyzjson_map_simple(folder,fname)
                    self._assert_map_fields_similarity_0(map_fields)

        finally:
            self.similarity_threshold = s

    
    def test_parse_xyzjson_map_dupe_case(self):
        folder = "xyzjson-small"
        fnames = [
            "airport-xyz.geojson",
            "water-xyz.geojson",
        ]
        for fname in fnames:
            self.subtest_parse_xyzjson_map_dupe_case(folder,fname)
    
    def _parse_xyzjson_map_simple(self,folder,fname):
        resource = TestFolder(folder)
        txt = resource.load(fname)
        obj = json.loads(txt)
        return self.subtest_parse_xyzjson_map_chunk(obj)


    def subtest_parse_xyzjson_map_dupe_case(self,folder,fname):
        with self.subTest(folder=folder,fname=fname):
            import random
            mix_case = lambda txt, idx: "".join([
                (s.lower() if s.isupper() else s.upper()) 
                if i == idx else s
                for i, s in enumerate(txt)])
            new_feat = lambda ft, props: dict(ft, properties=dict(props))
            n_new_ft = 2
            with self.subTest(folder=folder,fname=fname):
                resource = TestFolder(folder)
                txt = resource.load(fname)
                obj = json.loads(txt)
                features = obj["features"]
                features[0]["properties"].update(fid=1) # test fid
                lst_k = list()
                lst_new_k = list()
                props_ = dict(obj["features"][0]["properties"])
                props_ = sorted(props_.keys())
                debug_msg = ""
                for k in props_:
                    lst_k.append(k)
                    for i in range(n_new_ft):
                        ft = dict(features[0])
                        props = dict(ft["properties"])
                        new_k = k
                        while new_k == k:
                            idx = random.randint(0,len(k)-1)
                            if k == "fid": idx = i
                            new_k = mix_case(k, idx)
                        if new_k not in lst_new_k: lst_new_k.append(new_k)
                        debug_msg += format_long_args("\n", "mix_case", k, new_k, props[k], idx)
                        props[new_k] = props.pop(k) or ""
                        new_ft = new_feat(ft, props)
                        features.append(new_ft)
                map_fields = self.subtest_parse_xyzjson_map_chunk(obj,chunk_size=1)

                # assert that parser handle dupe of case insensitive prop name, e.g. name vs Name
                self.assertEqual(len(map_fields),1, "not single geom")
                lst_fields = list(map_fields.values())[0]
                for k in lst_k:
                    self.assertIn(k, lst_fields[0].names())

                # debug
                debug_msg += format_long_args("\n", lst_fields[0].names())
                for k, fields in zip(lst_new_k, lst_fields[1:]):
                    if k.lower() in {parser.QGS_ID, parser.QGS_XYZ_ID}:
                        k = "{}_{}".format(k, 
                        "".join(str(i) for i, s in enumerate(k) if s.isupper()))
                    debug_msg += format_long_args("\n", k in fields.names(), k, fields.names())

                # self.assertEqual(len(lst_fields), len(lst_new_k) + 1)
                for k, fields in zip(lst_new_k, lst_fields[1:]):
                    if k.lower() in {parser.QGS_ID, parser.QGS_XYZ_ID}:
                        k = "{}_{}".format(k, 
                        "".join(str(i) for i, s in enumerate(k) if s.isupper()))
                    self.assertIn(k, fields.names(), 
                    "len lst_fields vs. len keys: %s != %s" %
                    (len(lst_fields), len(lst_new_k) + 1) +
                    debug_msg
                    )

    def subtest_parse_xyzjson_map(self,folder,fname):
        with self.subTest(folder=folder,fname=fname):
            resource = TestFolder(folder)
            txt = resource.load(fname)
            obj = json.loads(txt)
            self.subtest_parse_xyzjson_map_shuffle(obj)
            self.subtest_parse_xyzjson_map_multi_chunk(obj)
            
    def subtest_parse_xyzjson_mix(self,folder,fnames):
        if len(fnames) < 2: return
        with self.subTest(folder=folder, fname="mix:"+",".join(fnames)):
            resource = TestFolder(folder)
            lst_obj = [
                json.loads(resource.load(fname))
                for fname in fnames
            ]
            obj = lst_obj[0]
            for o in lst_obj[1:]:
                obj["features"].extend(o["features"])
            random.seed(0.1)
            random.shuffle(obj["features"])
            self.subtest_parse_xyzjson_map_shuffle(obj)
            self.subtest_parse_xyzjson_map_multi_chunk(obj)

    def subtest_parse_xyzjson_map_multi_chunk(self, obj, lst_chunk_size=None):
        if not lst_chunk_size:
            p10 = 1+len(str(len(obj["features"])))
            lst_chunk_size = [10**i for i in range(p10)]
        with self.subTest(lst_chunk_size=lst_chunk_size):
            ref_map_feat, ref_map_fields = self.do_test_parse_xyzjson_map(obj)
            lst_map_fields = list()
            for chunk_size in lst_chunk_size:
                map_fields = self.subtest_parse_xyzjson_map_chunk(obj, chunk_size)
                if map_fields is None: continue
                lst_map_fields.append(map_fields)
                
            for map_fields, chunk_size in zip(lst_map_fields, lst_chunk_size):
                with self.subTest(chunk_size=chunk_size):
                    self._assert_len_map_fields(
                        map_fields, ref_map_fields)
    
    def subtest_parse_xyzjson_map_shuffle(self, obj, n_shuffle=5, chunk_size=10):
        with self.subTest(n_shuffle=n_shuffle):
            o = dict(obj)
            ref_map_feat, ref_map_fields = self.do_test_parse_xyzjson_map(o)
            lst_map_fields = list()
            random.seed(0.5)
            for i in range(n_shuffle):
                random.shuffle(o["features"])
                map_fields = self.subtest_parse_xyzjson_map_chunk(o, chunk_size)
                if map_fields is None: continue
                lst_map_fields.append(map_fields)
                
                # self._log_debug("parsed fields shuffle", len_of_struct(map_fields))

            for i, map_fields in enumerate(lst_map_fields):
                with self.subTest(shuffle=i):
                    self._assert_len_map_fields(
                        map_fields, ref_map_fields)

    def subtest_parse_xyzjson_map_chunk(self, obj, chunk_size=100):
        similarity_threshold = self.similarity_threshold
        with self.subTest(chunk_size=chunk_size, similarity_threshold=similarity_threshold):
            o = dict(obj)
            obj_feat = obj["features"]
            lst_map_feat = list()
            map_fields = dict()
            for i0 in range(0,len(obj_feat), chunk_size):
                chunk = obj_feat[i0:i0+chunk_size]
                o["features"] = chunk
                map_feat, _ = parser.xyz_json_to_feature_map(o, map_fields, similarity_threshold)
                self._assert_parsed_map(chunk, map_feat, map_fields)
                lst_map_feat.append(map_feat)

                # self._log_debug("len feat", len(chunk))
                # self._log_debug("parsed feat", len_of_struct(map_feat))
                # self._log_debug("parsed fields", len_of_struct(map_fields))

            lst_feat = flatten([x.values() for x in lst_map_feat])
            self.assertEqual(len(lst_feat), len(obj["features"]))
            return map_fields
    
    def do_test_parse_xyzjson_map(self, obj, similarity_threshold=None):
        obj_feat = obj["features"]
        # map_fields=dict()
        if similarity_threshold is None: 
            similarity_threshold = self.similarity_threshold
        map_feat, map_fields = parser.xyz_json_to_feature_map(obj, similarity_threshold=similarity_threshold)

        self._log_debug("len feat", len(obj_feat))
        self._log_debug("parsed feat", len_of_struct(map_feat))
        self._log_debug("parsed fields", len_of_struct(map_fields))

        self._assert_parsed_map(obj_feat, map_feat, map_fields)
        return map_feat, map_fields

    def _assert_len_map_fields(self, map_fields, ref, strict=False):
        len_ = len_of_struct if strict else len_of_struct_sorted
        self.assertEqual(
            len_(map_fields), len_(ref), "\n".join([
                "map_fields, ref_map_fields",
                format_map_fields(map_fields),
                format_map_fields(ref),
                ])
            )
        
    def _assert_parsed_map(self, obj_feat, map_feat, map_fields):
        self._assert_len_map_feat_fields(map_feat, map_fields)
        self.assertEqual(len(obj_feat), 
            sum(len(lst) 
            for lst_lst in map_feat.values() 
            for lst in lst_lst),
            "total len of parsed feat incorrect")

        # NOTE: obj_feat order does not corresponds to that of map_feat
        # -> use unorder assert
        for geom_str in map_feat:
            for feat, fields in zip(map_feat[geom_str], map_fields[geom_str]):
                o = obj_feat[:len(feat)]
                self._assert_parsed_fields_unorder(o, feat, fields)
                self._assert_parsed_geom_unorder(o, feat, fields, geom_str)
                obj_feat = obj_feat[len(feat):]

    def _assert_len_map_feat_fields(self, map_feat, map_fields):
        self.assertEqual(map_feat.keys(), map_fields.keys())
        for geom_str in map_feat:
            self.assertEqual(len(map_feat[geom_str]), len(map_fields[geom_str]),
            "len mismatch: map_feat, map_fields" +
            "\n %s \n %s" % (len_of_struct(map_feat), len_of_struct(map_fields))
            )
    
    def _assert_map_fields_similarity_0(self, map_fields):
        fields_cnt = {k:len(lst_fields) for k, lst_fields in map_fields.items()}
        ref = {k:1 for k in map_fields}
        self.assertEqual(fields_cnt, ref, 
        "given similarity_threshold=0, " + 
        "map_fields should have exact 1 layer/fields per geom")

    def test_parse_xyzjson_map_large(self):
        folder = "xyzjson-large"
        fnames = [
            "cmcs-osm-dev-building-xyz.geojson",
            "cmcs-osm-dev-road-xyz.geojson",
        ]
        for fname in fnames:
            self.subtest_parse_xyzjson_map(folder,fname)

    ######## Parse QgsFeature -> json 
    def test_parse_qgsfeature(self):
        self.subtest_parse_qgsfeature("geojson-small","airport-qgis.geojson") # no xyz_id

    def subtest_parse_qgsfeature(self,folder,fname):
        # qgs layer load geojson -> qgs feature
        # parse feature to xyz geojson
        # compare geojson and xyzgeojson
        with self.subTest(folder=folder,fname=fname):
        
            resource = TestFolder(folder) 
            path = resource.fullpath(fname)
            txt = resource.load(fname)
            obj = json.loads(txt)

            vlayer = QgsVectorLayer(path, "test", "ogr")
            feat = parser.feature_to_xyz_json(list(vlayer.getFeatures()),is_new=True) # remove QGS_XYZ_ID if exist
            self._log_debug(feat)

            self.assertListEqual(obj["features"],feat)
            self.assertEqual(len(obj["features"]),len(feat))

    def test_parse_qgsfeature_large(self):
        pass
        
if __name__ == "__main__":
    # unittest.main()

    tests = [
        # "TestParser.test_parse_xyzjson",
        "TestParser.test_parse_xyzjson_map_similarity_0",
        # "TestParser.test_parse_xyzjson_map",
        # "TestParser.test_parse_xyzjson_map_dupe_case",
        # "TestParser.test_parse_xyzjson_large",
        # "TestParser.test_parse_xyzjson_map_large",
        
    ]
    # unittest.main(defaultTest = tests, failfast=True) # will not run all subtest
    unittest.main(defaultTest = tests)
