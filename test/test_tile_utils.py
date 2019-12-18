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
from XYZHubConnector.modules.layer import tile_utils


# import unittest
class TestTileUtils(BaseTestAsync):

    @unittest.skip("skip")
    def test_bbox_quad_key(self):
        rect= (-180,-90,180,90)
        lst = tile_utils.bboxToListQuadkey(*rect, 0)
        self.assertEqual(sorted(lst), ['0'])

        lst = tile_utils.bboxToListQuadkey(*rect, 1)
        self.assertEqual(sorted(lst), ['0', '1', '2', '3'])

    # @unittest.skip("skip")
    def test_bbox_row_col(self):
        tol = 1e-9
        tolY = 1e-3
        rect_all = (-180, -90, 180, 90)
        rect_lowerL = (-180, -90, 0-tol, 0-tolY)
        rect_lowerR = (0, -90, 180, 0-tolY)
        rect_upperL = (-180, 0, 0-tol, 90)
        rect_upperR = (0, 0, 180, 90)

        for rect in [rect_all, rect_lowerL, rect_lowerR, rect_upperL, rect_upperR]:
            self.assertEqual(
                sorted(tile_utils.bboxToListColRow(*rect, 0)), 
                ['0_0_0'])
            
        self.assertEqual(
            sorted(tile_utils.bboxToListColRow(*rect_all, 1)), 
            ['1_0_0', '1_1_0'])
        for rect in [rect_lowerL, rect_upperL]:
            self.assertEqual(
                sorted(tile_utils.bboxToListColRow(*rect, 1)), 
                ['1_0_0'])
        for rect in [rect_lowerR, rect_upperR]:
            self.assertEqual(
                sorted(tile_utils.bboxToListColRow(*rect, 1)), 
                ['1_1_0'])

        self.assertEqual(
            sorted(tile_utils.bboxToListColRow(*rect_all, 2)), 
            ['2_0_0', '2_0_1', '2_1_0', '2_1_1', '2_2_0', '2_2_1', '2_3_0', '2_3_1'])
            
        self.assertEqual( 
            sorted(tile_utils.bboxToListColRow(*rect_lowerL , 2)), 
            ['2_0_0', '2_1_0'])
        self.assertEqual( 
            sorted(tile_utils.bboxToListColRow(*rect_lowerR , 2)), 
            ['2_2_0', '2_3_0'])
        self.assertEqual( 
            sorted(tile_utils.bboxToListColRow(*rect_upperL , 2)), 
            ['2_0_1', '2_1_1'])
        self.assertEqual( 
            sorted(tile_utils.bboxToListColRow(*rect_upperR , 2)), 
            ['2_2_1', '2_3_1'])

    # @unittest.skip("skip")
    def test_coord_to_row_col(self):
        level=1
        for lon in [-180,-90,0,90,180]:
            for lat in [-90,-45,0,45,90]:
                coord = [lon,lat]
                rc = tile_utils.coord_to_row_col(coord, level)
                print(level,coord,"\t",rc)
        for schema in ["here","web"]:
            with self.subTest(schema=schema):
                level = 20
                coord = [8,50]
                rc = tile_utils.coord_to_row_col(coord, level, schema)
                print(level,coord,rc,schema)
                # self.assertEqual(list(reversed(rc)), [547589, 355619]) # from geotool # rc vs xy
                self.assertEqual(list(reversed(rc)), [547589, 346478]) # 2^(n-1), reversed index # rc vs xy

        # level=6
        # for coord in [[-136.7, -61.5],[-136.7, 61.5], [-92.9, -34.0]]:
        #     rc = tile_utils.coord_to_row_col(coord, level)
        #     print(level,coord,rc)

    def test_coord_from_percent(self):
        level = 1
        for r in [0, 0.5, 0.9]:
            for c in [0, 0.5, 0.9]:
                coord = tile_utils.coord_from_percent(r,c,level)
                print(r,c,coord)

    def test_row_col(self):
        level = 1
        for lon in [-180,-90,0,90,180]:
            for lat in [-90,-45,0,45,90]:
                coord = [lon,lat]
                r,c = tile_utils.coord_to_row_col(coord, level)
                extent = tile_utils.extent_from_row_col(r,c,level)
                print(level,[r,c],"\t",coord,"\t",extent)
                # self.assertEqual(coord, coord2, "not equal")

    def test_coord_from_row_col(self):
        level=1
        for row in [0]:
            for col in [0,1]:
                coord = tile_utils.extent_from_row_col(row, col, level)
                print(level,coord,"\t",row,col)

    @unittest.skip("skip")
    def test_bbox_to_tile(self):
        self._test_bbox_to_tile(tile_utils.bboxToListQuadkey)
        # self._test_bbox_to_tile(tile_utils.bboxToListColRow)

    def _test_bbox_to_tile(self, fn):
        # https://wiki.openstreetmap.org/wiki/Zoom_levels
        rect= (-180,-90,180,90)
        for level in range(2):
            with self.subTest(level=level, rect=rect):
                lst = tile_utils.bboxToListQuadkey(*rect,level)
                lst2 = tile_utils.bboxToListColRow(*rect,level)
                print(level, len(lst), len(lst2), lst, lst2)

                # lst = fn(*rect,level)
                # n_tiles = 2**(2*level)
                # print(level, len(lst), len(lst2), n_tiles, "diff: %s"%(n_tiles - len(lst)))
                # # self.assertEqual(len(lst), n_tiles, "diff: %s"%(n_tiles - len(lst)))
                


        
if __name__ == "__main__":
    unittest.main()

    # tests = [
        
    # ]
    # # unittest.main(defaultTest = tests, failfast=True) # will not run all subtest
    # unittest.main(defaultTest = tests)
