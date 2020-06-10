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

from test.utils import (BaseTestAsync, format_long_args)

from qgis.core import QgsFields
from qgis.testing import unittest
from XYZHubConnector.xyz_qgis.layer import parser


# import unittest
# class TestParser(BaseTestAsync, unittest.TestCase):
class TestFieldsSimilarity(BaseTestAsync):
    def _similarity_of_fields_names_and_props_keys(self, fields_names, props_keys):
        props = dict((v, k) for k, v in enumerate(props_keys))

        # from parser.prepare_fields
        orig_props_names = [k for k, v in props.items() 
            if v is not None] 
        parser.rename_special_props(props) # rename fid in props
        props_names = [k for k, v in props.items() 
            if v is not None] 

        return parser.fields_similarity(fields_names, orig_props_names, props_names)
    def subtest_similarity_score(self, fields_names, props_keys, expected):
        with self.subTest(fields_names=fields_names,props_keys=props_keys):
            score = self._similarity_of_fields_names_and_props_keys(fields_names, props_keys)
            self._log_debug("score", score)
            self.assertEqual(score, expected)
            return score
    def test_simple(self):
        fid = parser.QGS_ID
        xid = parser.QGS_XYZ_ID
        xyz_special_key = "@ns:com:here:xyz"
        score = self.subtest_similarity_score([fid, "a", "b"], ["a", "b"], 1)
        score = self.subtest_similarity_score([fid,"a"], ["a","b"], 1)
        score = self.subtest_similarity_score([fid,"a"], ["b"], 0)
        score = self.subtest_similarity_score([fid,"a","c"], ["a","b"], 0.5)
        score = self.subtest_similarity_score([fid, xyz_special_key,"a","b","c"], 
            [xyz_special_key,"a"], 1)

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

    def test_empty_variant_1(self):
        fid = parser.QGS_ID
        xid = parser.QGS_XYZ_ID
        xyz_special_key = "@ns:com:here:xyz"
        # variant 1: empty props will be merged to any fields
        # empty fields will be merged with any props
        score = self.subtest_similarity_score([fid], ["a"], 1) 
        score = self.subtest_similarity_score([fid,"a"], [], 1) 
        score = self.subtest_similarity_score([fid,xyz_special_key], ["a",xyz_special_key], 1) 
        score = self.subtest_similarity_score([fid], [fid], 1)
        score = self.subtest_similarity_score([fid, xyz_special_key], [fid], 1)

    def test_empty_variant_2(self):
        fid = parser.QGS_ID
        xid = parser.QGS_XYZ_ID
        xyz_special_key = "@ns:com:here:xyz"
        # variant 2: empty props will be merged to empty fields only
        # empty fields is reserved for empty props only
        # non-empty, shall returns new fields (score 0)
        score = self.subtest_similarity_score([fid], ["a"], 0) 
        score = self.subtest_similarity_score([fid,"a"], [], 0) 
        score = self.subtest_similarity_score([fid,xyz_special_key], ["a",xyz_special_key], 0) 
        score = self.subtest_similarity_score([fid], [fid], 0)
        score = self.subtest_similarity_score([fid, xyz_special_key], [fid], 0)


    def test_complex(self):
        feat_json = dict(properties=dict(a=1,b=2))
        lst_fields = list()
        # prepare_fields
        
if __name__ == "__main__":
    # unittest.main()

    tests = [
        "TestFieldsSimilarity.test_simple",
        "TestFieldsSimilarity.test_empty",
        # "TestFieldsSimilarity.test_empty_variant_1",
        "TestFieldsSimilarity.test_empty_variant_2",
    ]
    # unittest.main(defaultTest = tests, failfast=True) # will not run all subtest
    unittest.main(defaultTest = tests)
