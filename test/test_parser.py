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

from test.utils import (
    BaseTestAsync,
    TestFolder,
    format_long_args,
    len_of_struct,
    len_of_struct_sorted,
    flatten,
    format_map_fields,
)

from qgis.core import QgsFields, QgsVectorLayer, QgsWkbTypes
from qgis.testing import unittest
from XYZHubConnector.xyz_qgis.layer import parser


# import unittest
# class TestParser(BaseTestAsync, unittest.TestCase):
class TestParser(BaseTestAsync):
    def __init__(self, *a, test_parser_kw=None, **kw):
        super().__init__(*a, **kw)
        test_parser_kw = test_parser_kw or dict()
        self.similarity_threshold = test_parser_kw.get("similarity_threshold", 80)
        self.mixed_case_duplicate = test_parser_kw.get("mixed_case_duplicate", False)
        self.has_many_fields = test_parser_kw.get("has_many_fields", False)

    # util for debug
    def assertEqual(self, first, second, msg=None):
        if first != second:
            msg = self._log_error(msg)
        super().assertEqual(first, second, msg)

    def assertTrue(self, expr, msg=None):
        if not expr:
            msg = self._log_error(msg)
        super().assertTrue(expr, msg)

    def fail(self, msg):
        msg = self._log_error(msg)
        return super().fail(msg)

    # ######## Parse xyz geojson -> QgsFeature
    def test_parse_xyzjson(self):
        folder = "xyzjson-small"
        fnames = ["airport-xyz.geojson", "water-xyz.geojson"]
        for fname in fnames:
            self.subtest_parse_xyzjson(folder, fname)

    def subtest_parse_xyzjson(self, folder, fname):
        feat = list()
        with self.subTest(folder=folder, fname=fname):
            resource = TestFolder(folder)

            txt = resource.load(fname)
            obj = json.loads(txt)
            obj_feat = obj["features"]
            fields = QgsFields()
            feat = [parser.xyz_json_to_feature(ft, fields) for ft in obj_feat]
            o1 = obj_feat[0] if len(obj_feat) else None
            geom_str = o1 and o1["geometry"] and o1["geometry"]["type"]

            self._assert_parsed_feat(obj_feat, feat)
            self._assert_parsed_fields_unorder(obj_feat, feat, fields)
            self._assert_parsed_fields(obj_feat, feat, fields)
            self._assert_parsed_geom_unorder(obj_feat, feat, fields, geom_str)
            self._assert_parsed_geom(obj_feat, feat, fields, geom_str)
        return feat

    def _assert_parsed_feat(self, obj_feat, feat):
        self.assertEqual(len(obj_feat), len(feat))
        for o, ft in zip(obj_feat, feat):
            id_ = ft.attribute(parser.QGS_XYZ_ID)
            obj_id_ = o["id"]
            self.assertEqual(id_, obj_id_)

    def _assert_parsed_fields_unorder(self, obj_feat, feat, fields):
        # self._log_debug(fields.names())
        # self._log_debug("debug id, json vs. QgsFeature")
        # self._log_debug([o["id"] for o in obj_feat])
        # self._log_debug([ft.attribute(parser.QGS_XYZ_ID) for ft in feat])

        names = fields.names()
        self.assertTrue(parser.QGS_XYZ_ID in names, "%s %s" % (len(names), names))

    def _assert_parsed_fields(self, obj_feat, feat, fields):
        def msg_fields(obj):
            return (
                "{sep}props {0}"
                "{sep}fields {1}"
                "{sep}props-fields {2} (should be 0)"
                "{sep}fields-props {3}"
                "{sep}json {4}".format(
                    *tuple(
                        map(
                            lambda x: "%s %s" % (len(x), x),
                            [
                                obj_props,
                                fields.names(),
                                set(obj_props).difference(fields.names()),
                                set(fields.names()).difference(obj_props),
                            ],
                        )
                    ),
                    format_long_args(json.dumps(obj)),
                    sep="\n>> "
                )
            )

        for o in obj_feat:
            obj_props = list(o["properties"].keys())
            obj_props_non_null = [k for k, v in o["properties"].items() if v is not None]
            self.assertLessEqual(len(obj_props), fields.size(), msg_fields(o))
            # self._log_debug(msg_fields(o).replace(">>", "++"))

            obj_props_is_subset_of_fields = any(
                [
                    set(obj_props) < set(fields.names()),
                    set(obj_props_non_null) < set(fields.names()),
                ]
            )
            self.assertTrue(obj_props_is_subset_of_fields, msg_fields(o))
            # self.assertEqual( obj_props, fields.names(), msg_fields(o)) # strict assert

    def wkb_type_to_wkt_str(self, typ):
        return QgsWkbTypes.displayString(typ)

    def wkb_type_to_geom_str(self, typ):
        return QgsWkbTypes.displayString(typ % 1000) if typ else None

    def wkb_type_to_geom_display_str(self, typ):
        return (
            QgsWkbTypes.geometryDisplayString(QgsWkbTypes.geometryType(typ))
            if typ
            else "No geometry"
        )

    def _assert_parsed_geom_unorder(self, obj_feat, feat, fields, geom_str):
        wkt_ref = self.wkb_type_to_wkt_str(QgsWkbTypes.parseType(geom_str))
        for ft in feat:
            geom = json.loads(
                ft.geometry().asJson()
            )  # limited to 13 or 14 precison (ogr.CreateGeometryFromJson)
            self.assertEqual(geom and geom["type"], geom_str)

            geom_str_ft = self.wkb_type_to_geom_str(ft.geometry().wkbType())
            wkt_ft = self.wkb_type_to_wkt_str(ft.geometry().wkbType())
            msg = "wkt string {} != {}".format(wkt_ft, wkt_ref)
            self.assertEqual(geom_str_ft, geom_str, msg)

    def _assert_parsed_geom(self, obj_feat, feat, fields, geom_str):
        # both crs is WGS84
        for o, ft in zip(obj_feat, feat):
            geom = json.loads(
                ft.geometry().asJson()
            )  # limited to 13 or 14 precison (ogr.CreateGeometryFromJson)
            obj_geom = o["geometry"]

            self.assertEqual(geom and geom["type"], obj_geom and obj_geom["type"])
            if not geom or not obj_geom:
                continue

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
            c1_flatten = np.array(flatten(obj_geom["coordinates"]))
            c2_flatten = np.array(flatten(geom["coordinates"]))
            if c1.shape != c2.shape:
                self._log_debug(
                    "\nWARNING: Geometry has mismatch shape",
                    c1.shape,
                    c2.shape,
                    "\nOriginal geom has problem. Testing parsed geom..",
                )
                msg = (
                    "parsed geom has wrong shape of coord for geom {geom}. {} != {}".format(
                        c1.shape, c2.shape, geom=geom["type"]
                    ),
                )
                self.assertEqual(c2.shape[-1], 2, msg)
                continue
            else:
                self.assertLess(
                    np.max(np.abs(c1_flatten - c2_flatten)), 1e-13, "parsed geometry error > 1e-13"
                )

    # @unittest.skip("large")
    def test_parse_xyzjson_large(self):
        folder = "xyzjson-large"
        fnames = [
            "cmcs-osm-dev-building-xyz.geojson",
            "cmcs-osm-dev-building-xyz-30000.geojson",
        ]
        for fname in fnames:
            self.subtest_parse_xyzjson(folder, fname)

    # ######## Parse xyz geojson -> struct of geom: [fields], [[QgsFeature]]
    def test_parse_xyzjson_map(self):
        folder = "xyzjson-small"
        fnames = [
            "mixed-xyz.geojson",
        ]
        for fname in fnames:
            self.subtest_parse_xyzjson_map(folder, fname)

        mix_fnames = [
            "airport-xyz.geojson",
            "water-xyz.geojson",
        ]
        self.subtest_parse_xyzjson_mix(folder, mix_fnames)

    def test_parse_xyzjson_map_similarity_0(self):
        s = self.similarity_threshold
        self.similarity_threshold = 0
        try:
            folder = "xyzjson-small"
            fnames = [
                "mixed-xyz.geojson",
            ]

            for fname in fnames:
                with self.subTest(
                    folder=folder, fname=fname, similarity_threshold=self.similarity_threshold
                ):
                    map_fields = self._parse_xyzjson_map_simple(folder, fname)
                    self._assert_map_fields_similarity_0(map_fields)

        finally:
            self.similarity_threshold = s

    def test_parse_xyzjson_map_dupe_case(self):
        self.mixed_case_duplicate = True
        folder = "xyzjson-small"
        fnames = [
            "airport-xyz.geojson",
            "water-xyz.geojson",
        ]
        for fname in fnames:
            self.subtest_parse_xyzjson_map_dupe_case(folder, fname)

    def _parse_xyzjson_map_simple(self, folder, fname):
        resource = TestFolder(folder)
        txt = resource.load(fname)
        obj = json.loads(txt)
        return self.subtest_parse_xyzjson_map_chunk(obj)

    def subtest_parse_xyzjson_map_dupe_case(self, folder, fname):
        with self.subTest(folder=folder, fname=fname):
            import random

            mix_case = lambda txt, idx: "".join(
                [
                    (s.lower() if s.isupper() else s.upper()) if i == idx else s
                    for i, s in enumerate(txt)
                ]
            )
            new_feat = lambda ft, props: dict(ft, properties=dict(props))
            n_new_ft = 2
            with self.subTest(folder=folder, fname=fname):
                resource = TestFolder(folder)
                txt = resource.load(fname)
                obj = json.loads(txt)
                features = obj["features"]
                features[0]["properties"].update(fid=1)  # test fid
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
                            idx = random.randint(0, len(k) - 1)
                            if k == "fid":
                                idx = i
                            new_k = mix_case(k, idx)
                        if new_k not in lst_new_k:
                            lst_new_k.append(new_k)
                        debug_msg += format_long_args("\n", "mix_case", k, new_k, props[k], idx)
                        props[new_k] = props.pop(k) or ""
                        new_ft = new_feat(ft, props)
                        features.append(new_ft)
                map_fields = self.subtest_parse_xyzjson_map_chunk(obj, chunk_size=1)

                # assert that parser handle dupe of case insensitive prop name, e.g. name vs Name
                self.assertEqual(len(map_fields), 1, "not single geom")
                lst_fields = list(map_fields.values())[0]
                for k in lst_k:
                    self.assertIn(k, lst_fields[0].names())

                for k in lst_new_k:
                    self.assertIn(k, [parser.normal_field_name(n) for n in lst_fields[0].names()])

                return

                # debug
                debug_msg += format_long_args("\n", lst_fields[0].names())
                for k, fields in zip(lst_new_k, lst_fields[1:]):
                    if k.lower() in {parser.QGS_ID, parser.QGS_XYZ_ID}:
                        k = "{}_{}".format(
                            k, "".join(str(i) for i, s in enumerate(k) if s.isupper())
                        )
                    debug_msg += format_long_args("\n", k in fields.names(), k, fields.names())

                # self.assertEqual(len(lst_fields), len(lst_new_k) + 1)
                for k, fields in zip(lst_new_k, lst_fields[1:]):
                    if k.lower() in {parser.QGS_ID, parser.QGS_XYZ_ID}:
                        k = "{}_{}".format(
                            k, "".join(str(i) for i, s in enumerate(k) if s.isupper())
                        )
                    self.assertIn(
                        k,
                        fields.names(),
                        "len lst_fields vs. len keys: %s != %s"
                        % (len(lst_fields), len(lst_new_k) + 1)
                        + debug_msg,
                    )

    def subtest_parse_xyzjson_map(self, folder, fname):
        with self.subTest(folder=folder, fname=fname):
            resource = TestFolder(folder)
            txt = resource.load(fname)
            obj = json.loads(txt)
            self.subtest_parse_xyzjson_map_shuffle(obj)
            self.subtest_parse_xyzjson_map_multi_chunk(obj)

    def subtest_parse_xyzjson_mix(self, folder, fnames):
        if len(fnames) < 2:
            return
        with self.subTest(folder=folder, fname="mix:" + ",".join(fnames)):
            resource = TestFolder(folder)
            lst_obj = [json.loads(resource.load(fname)) for fname in fnames]
            obj = lst_obj[0]
            for o in lst_obj[1:]:
                obj["features"].extend(o["features"])
            random.seed(0.1)
            random.shuffle(obj["features"])
            self.subtest_parse_xyzjson_map_shuffle(obj)
            self.subtest_parse_xyzjson_map_multi_chunk(obj)

    def subtest_parse_xyzjson_map_multi_chunk(self, obj, lst_chunk_size=None):
        if not lst_chunk_size:
            p10 = 1 + len(str(len(obj["features"])))
            lst_chunk_size = [10**i for i in range(p10)]
        with self.subTest(lst_chunk_size=lst_chunk_size):
            ref_map_feat, ref_map_fields = self.do_test_parse_xyzjson_map(obj)
            lst_map_fields = list()
            for chunk_size in lst_chunk_size:
                map_fields = self.subtest_parse_xyzjson_map_chunk(obj, chunk_size)
                if map_fields is None:
                    continue
                lst_map_fields.append(map_fields)

            for map_fields, chunk_size in zip(lst_map_fields, lst_chunk_size):
                with self.subTest(chunk_size=chunk_size):
                    self._assert_len_map_fields(map_fields, ref_map_fields)

    def subtest_parse_xyzjson_map_shuffle(self, obj, n_shuffle=5, chunk_size=10):
        with self.subTest(n_shuffle=n_shuffle):
            o = dict(obj)
            ref_map_feat, ref_map_fields = self.do_test_parse_xyzjson_map(o)
            lst_map_fields = list()
            random.seed(0.5)
            for i in range(n_shuffle):
                with self.subTest(shuffle=i):
                    random.shuffle(o["features"])
                    map_fields = self.subtest_parse_xyzjson_map_chunk(o, chunk_size)
                    if map_fields is None:
                        continue
                    lst_map_fields.append(map_fields)

                    # self._log_debug("parsed fields shuffle", len_of_struct(map_fields))

            for i, map_fields in enumerate(lst_map_fields):
                with self.subTest(shuffle=i):
                    self._assert_len_map_fields(map_fields, ref_map_fields)

    def subtest_parse_xyzjson_map_chunk(self, obj, chunk_size=100):
        similarity_threshold = self.similarity_threshold
        with self.subTest(chunk_size=chunk_size, similarity_threshold=similarity_threshold):
            o = dict(obj)
            obj_feat = list(obj["features"])
            lst_map_feat = list()
            map_fields = dict()
            for i0 in range(0, len(obj_feat), chunk_size):
                chunk = obj_feat[i0 : i0 + chunk_size]
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
        map_feat, map_fields = parser.xyz_json_to_feature_map(
            obj, similarity_threshold=similarity_threshold
        )

        self._log_debug("len feat", len(obj_feat))
        self._log_debug("parsed feat", len_of_struct(map_feat))
        self._log_debug("parsed fields", len_of_struct(map_fields))

        self._assert_parsed_map(obj_feat, map_feat, map_fields)
        return map_feat, map_fields

    def _assert_len_map_fields(self, map_fields, ref, strict=False):
        len_ = len_of_struct if strict else len_of_struct_sorted
        self.assertEqual(
            len_(map_fields),
            len_(ref),
            "\n".join(
                [
                    "map_fields, ref_map_fields",
                    format_map_fields(map_fields),
                    format_map_fields(ref),
                ]
            ),
        )

    def _assert_parsed_map(self, obj_feat, map_feat, map_fields):
        self._assert_len_map_feat_fields(map_feat, map_fields)
        self.assertEqual(
            len(obj_feat),
            sum(len(lst) for lst_lst in map_feat.values() for lst in lst_lst),
            "total len of parsed feat incorrect",
        )

        # NOTE: obj_feat order does not corresponds to that of map_feat
        # -> use unorder assert
        # NOTE: group obj_feat by geom_str for element-wise assert
        for geom_str in map_feat:
            obj_feat_by_geom = [
                o for o in obj_feat if (o["geometry"] and o["geometry"]["type"]) == geom_str
            ]
            feat_by_geom = sum(map_feat[geom_str], [])
            self._assert_parsed_feat(obj_feat_by_geom, feat_by_geom)
            self._assert_parsed_geom_unorder(obj_feat_by_geom, feat_by_geom, None, geom_str)

            if not self.has_many_fields:
                # element-wise assert
                self._assert_parsed_geom(obj_feat_by_geom, feat_by_geom, None, geom_str)

            for feat, fields in zip(map_feat[geom_str], map_fields[geom_str]):
                self._assert_parsed_fields_unorder(obj_feat_by_geom, feat, fields)
                if not self.mixed_case_duplicate and not self.has_many_fields:
                    # element-wise assert
                    self._assert_parsed_fields(obj_feat_by_geom, feat, fields)

    def _assert_len_map_feat_fields(self, map_feat, map_fields):
        self.assertEqual(map_feat.keys(), map_fields.keys())
        for geom_str in map_feat:
            self.assertEqual(
                len(map_feat[geom_str]),
                len(map_fields[geom_str]),
                "len mismatch: map_feat, map_fields"
                + "\n %s \n %s" % (len_of_struct(map_feat), len_of_struct(map_fields)),
            )

    def _assert_map_fields_similarity_0(self, map_fields):
        fields_cnt = {k: len(lst_fields) for k, lst_fields in map_fields.items()}
        ref = {k: 1 for k in map_fields}
        self.assertEqual(
            fields_cnt,
            ref,
            "given similarity_threshold=0, "
            + "map_fields should have exact 1 layer/fields per geom",
        )

    def test_parse_xyzjson_map_large(self):
        folder = "xyzjson-large"
        fnames = [
            "cmcs-osm-dev-building-xyz.geojson",
            "cmcs-osm-dev-road-xyz.geojson",
        ]
        for fname in fnames:
            self.subtest_parse_xyzjson_map(folder, fname)

    # ######## Parse QgsFeature -> json
    def test_parse_qgsfeature(self):
        # self.subtest_parse_qgsfeature("geojson-small", "airport-qgis.geojson")  # no xyz_id
        self.subtest_parse_qgsfeature("xyzjson-small", "airport-xyz.geojson")
        self.subtest_parse_qgsfeature_2way("xyzjson-small", "airport-xyz.geojson")
        self.subtest_parse_qgsfeature_livemap("xyzjson-small", "livemap-xyz.geojson")

    def subtest_parse_qgsfeature(self, folder, fname):
        # qgs layer load geojson -> qgs feature
        # parse feature to geojson
        # compare geojson and geojson
        with self.subTest(folder=folder, fname=fname):

            resource = TestFolder(folder)
            path = resource.fullpath(fname)
            txt = resource.load(fname)
            obj = json.loads(txt)

            vlayer = QgsVectorLayer(path, "test", "ogr")
            feat = parser.feature_to_xyz_json(
                list(vlayer.getFeatures()), is_new=True
            )  # remove QGS_XYZ_ID if exist
            self._log_debug(feat)

            self.maxDiff = None
            # no need to convert 0.0 to 0
            expected = obj
            for ft in expected["features"]:
                ft.pop("id", None)
                ft["properties"].pop("@ns:com:here:xyz", None)
            for ft in feat:
                ft["properties"].pop("id", None)  # cleanup unexpected "id" field in input data
            self.assertListEqual(expected["features"], feat)
            self.assertEqual(len(expected["features"]), len(feat))

    def subtest_parse_qgsfeature_2way(self, folder, fname):
        # parse xyz geojson to qgs feature
        # parse feature to xyz geojson
        # compare geojson and xyz geojson
        with self.subTest(folder=folder, fname=fname, mode="2way", target="QgsFeature"):
            qgs_feat = self.subtest_parse_xyzjson(folder, fname)

        with self.subTest(folder=folder, fname=fname, mode="2way", target="XYZ Geojson"):

            resource = TestFolder(folder)
            txt = resource.load(fname)
            obj = json.loads(txt)
            expected = obj

            feat = parser.feature_to_xyz_json(qgs_feat)
            self._log_debug(feat)

            self.maxDiff = None
            # no need to convert 0.0 to 0
            for ft in expected["features"]:
                ft["properties"].pop("@ns:com:here:xyz", None)
            self.assertListEqual(expected["features"], feat)
            self.assertEqual(len(expected["features"]), len(feat))

            feat = parser.feature_to_xyz_json(qgs_feat, is_new=True)
            self._log_debug(feat)

            for ft in expected["features"]:
                ft.pop("id", None)
            self.assertListEqual(expected["features"], feat)
            self.assertEqual(len(expected["features"]), len(feat))

    def subtest_parse_qgsfeature_livemap(self, folder, fname):
        # test parse livemap qgsfeature
        with self.subTest(folder=folder, fname=fname, mode="livemap", target="QgsFeature"):
            qgs_feat = self.subtest_parse_xyzjson(folder, fname)

        with self.subTest(folder=folder, fname=fname, mode="livemap", target="XYZ Geojson"):
            resource = TestFolder(folder)
            txt = resource.load(fname)
            obj = json.loads(txt)

            feat = parser.feature_to_xyz_json(qgs_feat, is_livemap=True)

            self.maxDiff = None
            expected = obj
            for ft in expected["features"]:
                ft.pop("momType", None)
                props = ft["properties"]

                changeState = "UPDATED" if "@ns:com:here:mom:delta" in props else "CREATED"
                delta = {
                    "reviewState": "UNPUBLISHED",
                    "changeState": changeState,
                    "taskGridId": "",
                }
                if ft.get("id"):
                    delta.update({"originId": ft.get("id")})

                ignored_sepcial_keys = [k for k in props.keys() if k.startswith("@")]
                ignored_keys = [k for k, v in props.items() if v is None]
                for k in ignored_sepcial_keys + ignored_keys:
                    props.pop(k, None)

                props.update({"@ns:com:here:mom:delta": delta})

            lst_coords_ref = [
                ft.pop("geometry", dict()).get("coordinates", list())
                for ft in expected["features"]
            ]
            lst_coords = [ft.pop("geometry", dict()).get("coordinates", list()) for ft in feat]

            self.assertListEqual(expected["features"], feat)
            self.assertEqual(len(expected["features"]), len(feat))

            # self.assertEqual(flatten(lst_coords_ref), flatten(lst_coords))
            for coords_ref, coords in zip(lst_coords_ref, lst_coords):
                self.assertLess(
                    np.max(np.abs(np.array(coords_ref) - np.array(coords))),
                    1e-13,
                    "parsed geometry error > 1e-13",
                )

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
    unittest.main(defaultTest=tests)
