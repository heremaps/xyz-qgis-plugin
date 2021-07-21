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

from test.utils import BaseTestAsync, format_long_args

from qgis.core import QgsFields
from qgis.testing import unittest
from XYZHubConnector.xyz_qgis.layer import parser


# import unittest
# class TestParser(BaseTestAsync, unittest.TestCase):
class TestFieldsSimilarity(BaseTestAsync):
    def _similarity_of_fields_names_and_props_keys(self, fields_names, props_keys):
        props = dict((v, k) for k, v in enumerate(props_keys))

        # from parser.prepare_fields
        orig_props_names = [k for k, v in props.items() if v is not None]
        parser.rename_special_props(props)  # rename fid in props
        props_names = [k for k, v in props.items() if v is not None]

        return parser.fields_similarity(fields_names, orig_props_names, props_names)

    def subtest_similarity_score(self, fields_names, props_keys, expected):
        with self.subTest(fields_names=fields_names, props_keys=props_keys):
            score = self._similarity_of_fields_names_and_props_keys(fields_names, props_keys)
            self._log_debug("score", score)
            self.assertEqual(score, expected)
            return score

    def test_simple(self):
        fid = parser.QGS_ID
        xid = parser.QGS_XYZ_ID
        xyz_special_key = "@ns:com:here:xyz"
        score = self.subtest_similarity_score([fid, "a", "b"], ["a", "b"], 1)
        score = self.subtest_similarity_score([fid, "a"], ["a", "b"], 1)
        score = self.subtest_similarity_score([fid, "a"], ["b"], 0)
        score = self.subtest_similarity_score([fid, "a", "c"], ["a", "b"], 0.5)
        score = self.subtest_similarity_score(
            [fid, xyz_special_key, "a", "b", "c"], [xyz_special_key, "a"], 1
        )

    def test_empty(self):
        fid = parser.QGS_ID
        xid = parser.QGS_XYZ_ID
        xyz_special_key = "@ns:com:here:xyz"
        # empty fields, shall returns merge fields (score 1)
        score = self.subtest_similarity_score([fid], [], 1)
        score = self.subtest_similarity_score([], [], 1)
        score = self.subtest_similarity_score([xyz_special_key], [], 1)
        score = self.subtest_similarity_score([xyz_special_key], [xyz_special_key], 1)
        score = self.subtest_similarity_score([fid, xyz_special_key], [], 1)
        score = self.subtest_similarity_score([fid, xyz_special_key], [xyz_special_key], 1)
        score = self.subtest_similarity_score([fid], [], 1)
        score = self.subtest_similarity_score([fid], [xyz_special_key], 1)

    @unittest.skip("skip logic variant 1")
    def test_empty_variant_1(self):
        fid = parser.QGS_ID
        xid = parser.QGS_XYZ_ID
        xyz_special_key = "@ns:com:here:xyz"
        # variant 1: empty props will be merged to any fields
        # empty fields will be merged with any props
        # merge if empty fields OR empty props

        score = self.subtest_similarity_score([fid], ["a"], 1)
        score = self.subtest_similarity_score([fid, "a"], [], 1)
        score = self.subtest_similarity_score([fid, xyz_special_key], ["a", xyz_special_key], 1)
        score = self.subtest_similarity_score([fid], [fid], 1)
        score = self.subtest_similarity_score([fid, xyz_special_key], [fid], 1)

    def test_empty_variant_2(self):
        fid = parser.QGS_ID
        xid = parser.QGS_XYZ_ID
        xyz_special_key = "@ns:com:here:xyz"
        # variant 2: empty props will be merged to empty fields only
        # special keys are excluded when calculating similarity score
        # create new fields if either fields or props is not empty (score 0)
        # merge if empty fields AND empty props (score 1)

        # fields or props not empty
        score = self.subtest_similarity_score([fid], ["a"], 0)
        score = self.subtest_similarity_score([fid, "a"], [], 0)
        score = self.subtest_similarity_score([fid, xyz_special_key], ["a", xyz_special_key], 0)

        # fields and props empty
        score = self.subtest_similarity_score([fid], [], 1)
        score = self.subtest_similarity_score([fid], [xyz_special_key], 1)
        score = self.subtest_similarity_score([xid], [xyz_special_key], 1)
        score = self.subtest_similarity_score([fid, xid], [xyz_special_key], 1)
        score = self.subtest_similarity_score([fid, xyz_special_key], [xyz_special_key], 1)
        score = self.subtest_similarity_score([fid, xid, xyz_special_key], [xyz_special_key], 1)

        # fields and props share common prop
        score = self.subtest_similarity_score(
            [fid, xyz_special_key, "a"], [xyz_special_key, "a"], 1
        )
        score = self.subtest_similarity_score(
            [fid, xid, xyz_special_key, "a"], [xyz_special_key, "a"], 1
        )

        # special key in props will be renamed, thus not excluded
        score = self.subtest_similarity_score([fid], [fid], 0)
        score = self.subtest_similarity_score([xid], [xid], 0)
        score = self.subtest_similarity_score([fid], [xid], 0)
        score = self.subtest_similarity_score([fid, xid], [fid, xid], 0)
        score = self.subtest_similarity_score([fid, xyz_special_key], [fid], 0)
        score = self.subtest_similarity_score([fid, xid, xyz_special_key], [fid], 0)
        score = self.subtest_similarity_score([fid, xyz_special_key], [fid, xyz_special_key], 0)
        # non-xyz special key are considered as props, thus not excluded
        score = self.subtest_similarity_score([fid, xyz_special_key], ["@ns:com:here:hello"], 0)

    def test_renamed_props(self):
        fid = parser.QGS_ID
        xid = parser.QGS_XYZ_ID
        xyz_special_key = "@ns:com:here:xyz"

        score = self.subtest_similarity_score([fid, xid, parser.unique_field_name(fid)], [fid], 1)
        score = self.subtest_similarity_score(
            [fid, xid, parser.unique_field_name(fid.upper())], [fid.upper()], 1
        )
        score = self.subtest_similarity_score(
            [parser.unique_field_name(fid.upper())], [fid.upper()], 1
        )
        score = self.subtest_similarity_score(
            [fid, xid, xyz_special_key, parser.unique_field_name(fid.upper())],
            [xyz_special_key, fid.upper()],
            1,
        )
        score = self.subtest_similarity_score(
            [fid, xid, xyz_special_key, parser.unique_field_name(xid.upper())],
            [xyz_special_key, xid.upper()],
            1,
        )
        score = self.subtest_similarity_score(
            [fid, xid, xyz_special_key, parser.unique_field_name(fid), "a"],
            [xyz_special_key, fid, "a"],
            1,
        )
        score = self.subtest_similarity_score(
            [fid, xid, xyz_special_key, parser.unique_field_name(fid), "a"],
            [xyz_special_key, fid.upper(), "a"],
            1 / 2,
        )

    def test_complex(self):
        feat_json = dict(properties=dict(a=1, b=2))
        lst_fields = list()
        # prepare_fields


class TestUniqueFieldName(BaseTestAsync):
    def test_transform_unique_field_names(self):
        fid = parser.QGS_ID
        xid = parser.QGS_XYZ_ID
        xyz_special_key = "@ns:com:here:xyz"

        self.subtest_transform_unique_field_names(fid)
        self.subtest_transform_unique_field_names(xid)
        self.subtest_transform_unique_field_names(xyz_special_key)
        self.subtest_transform_unique_field_names("foobar")
        self.subtest_transform_unique_field_names("@ns:com:here:hello")
        self.subtest_transform_unique_field_names("foo.bar")

    def subtest_transform_unique_field_names(self, orig_name):
        names = [orig_name]
        names.extend(
            [
                "".join(s.upper() if i % k else s for i, s in enumerate(orig_name))
                for k in [2, 3, 5]
            ]
        )
        for name in names:
            with self.subTest(name=name):
                field_name = parser.unique_field_name(name)
                actual = parser.normal_field_name(field_name)
                self._log_debug("{} -> {} -> {}".format(name, field_name, actual))
                self.assertEqual(actual, name)


if __name__ == "__main__":
    unittest.main()
    # tests = [
    #     "TestFieldsSimilarity",
    #     "TestUniqueFieldName"
    # ]
    # unittest.main(defaultTest = tests)
    # unittest.main(defaultTest = tests, failfast=True) # will not run all subtest
