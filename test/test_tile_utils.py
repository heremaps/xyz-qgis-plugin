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
from XYZHubConnector.xyz_qgis.layer import tile_utils


# import unittest
class TestTileUtils(BaseTestAsync):

    @unittest.skip("skip unused")
    def test_bbox_quadkey(self):
        tol = 1e-9
        tolY = 1e-3
        rect_all = (-180, -90, 180, 90)
        rect_lowerL = (-180, -90, 0-tol, 0-tolY)
        rect_lowerR = (0, -90, 180, 0-tolY)
        rect_upperL = (-180, 0, 0-tol, 90)
        rect_upperR = (0, 0, 180, 90)

        lst = tile_utils.bboxToListQuadkey(*rect_all, 1)
        self.assertEqual(
            sorted(tile_utils.bboxToListQuadkey(*rect_all, 1)), 
            ['0', '1', '2', '3'])

        self.assertEqual(
            [tile_utils.bboxToListQuadkey(*rect, 1)
            for rect in [rect_upperL, rect_upperR, rect_lowerR, rect_lowerL]],
            [['0'], ['1'], ['2'], ['3']]
            )

    def test_bbox_row_col_web(self):
        tol = 1e-9
        tolY = 1e-3
        rect_all = (-180, -90, 180, 90)
        rect_lowerL = (-180, -90, 0-tol, 0-tolY)
        rect_lowerR = (0, -90, 180, 0-tolY)
        rect_upperL = (-180, 0+tol, 0-tol, 90)
        rect_upperR = (0, 0+tol, 180, 90)

        for rect in [rect_all, rect_lowerL, rect_lowerR, rect_upperL, rect_upperR]:
            self.assertEqual(
                sorted(tile_utils.bboxToListColRow(*rect, 0, schema="web")), 
                ['0_0_0'])
            
        self.assertEqual(
            sorted(tile_utils.bboxToListColRow(*rect_all, 1, schema="web")), 
            ['1_0_0', '1_0_1', '1_1_0', '1_1_1'])
            
        self.assertEqual(
            [tile_utils.bboxToListColRow(*rect, 1, schema="web")
            for rect in [rect_upperL, rect_lowerL, rect_upperR, rect_lowerR]], 
            [['1_0_0'], ['1_0_1'], ['1_1_0'], ['1_1_1']])

        self.assertEqual(
            len(tile_utils.bboxToListColRow(*rect_all, 2, schema="web")),
            16)

        # print(
        #     (tile_utils.bboxToListColRow(*rect_all, 2, schema="web")),
        # )

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

    def print_coord_to_row_col(self):
        level=1
        for lon in [-180,-90,0,90,180]:
            for lat in [-90,-45,0,45,90]:
                coord = [lon,lat]
                rc = tile_utils.coord_to_row_col(coord, level)
                print(level,coord,"\t",rc)

    # @unittest.skip("skip")
    def test_coord_to_row_col(self):
        # self.print_coord_to_row_col()
        for schema, expected in [
            ["here", [547589, 407779]],
            ["web", [547589, 692956]]
        ]:
            with self.subTest(schema=schema):
                level = 20
                coord = [8,50]
                rc = tile_utils.coord_to_row_col(coord, level, schema)
                print(level,coord,rc,schema)
                # self.assertEqual(list(reversed(rc)), [547589, 355619]) # from geotool # rc vs xy
                self.assertEqual(list(reversed(rc)), expected) # 2^(n-1), reversed index # rc vs xy

    def test_coord_from_percent(self):
        avg = lambda lst: sum(x for x in lst)/len(lst)
        abs_avg = lambda lst: sum(abs(x) for x in lst)/len(lst)
        level = 1
        n_coord = 20
        lst_percent = np.linspace(0,1,n_coord)
        lst_x = [tile_utils.coord_from_percent(0,x,level)[0] for x in lst_percent]
        max_x = 180
        lst_y = [tile_utils.coord_from_percent(x,0,level)[1] for x in lst_percent]
        max_y = 90

        lst_debug_avg = [
            "\t" + "avg(lst_x), abs_avg(lst_x), avg(lst_y), abs_avg(lst_y)",
            "actual: \t" + "\t".join(map("{:.2f}".format, [
                avg(lst_x), abs_avg(lst_x), avg(lst_y), abs_avg(lst_y)
            ])),
            "expected: \t" + "\t".join(map("{:.2f}".format,[
                0, max_x/2, 0, max_y/2
            ]))
        ]
        # print("\n".join(lst_debug_avg))
        try:
            self.assertEqual(max(lst_x), max_x)
            self.assertEqual(-max_x, min(lst_x))
            self.assertEqual(max(lst_y), max_y)
            self.assertEqual(-max_y, min(lst_y))
            self.assertAlmostEqual(avg(lst_x), 0, 
                msg="x coordinates not average to 0")
            self.assertAlmostEqual(abs_avg(lst_x), max_x/2, delta=max_x*0.05, 
                msg="abs x coordinates not average to %s"%(max_x/2))
            self.assertAlmostEqual(avg(lst_y), 0, 
                msg="y coordinates not average to 0")
            self.assertAlmostEqual(abs_avg(lst_y), max_y/2, delta=max_y*0.05, 
                msg="abs y coordinates not average to %s"%(max_y/2))
        except Exception as e:
            linesep = "\n "
            debug_coord = ("percent" + "\t" + "coord" + linesep +
                linesep.join(map(lambda a: "{:.2f} \t{:.2f} {:.2f}".format(*a), 
                zip(lst_percent, lst_x, lst_y)))
                )
            e.args = (linesep.join([
                e.args[0], *lst_debug_avg, debug_coord
                ]), 
                *e.args[1:])
            raise e

    def test_extent_from_row_col(self):
        linesep = "\n "
        level = 1
        for schema in ["here", "web"]:
            lst_msg = list()
            lst_check = list()
            for lon in [-180,-90,0,90,180]:
                for lat in [-90,-45,0,45,90]:
                    coord = [lon,lat]
                    r, c = tile_utils.coord_to_row_col(coord, level, schema)
                    extent = tile_utils.extent_from_row_col(r, c, level, schema)
                    check = (
                        (extent[0] <= coord[0] <= extent[2] ) and
                        (extent[1] <= coord[1] <= extent[3] )
                        )
                    lst_msg.append(" ".join(map(str,
                        [level,[r,c],"\t",coord,"\t",extent,"\t",
                        "Ok" if check else "Fail"
                        ])))
                    lst_check.append(check)

            self.assertTrue(all(lst_check), 
                "schema: %s. " %(schema) +
                "Converted extent does not cover input coord" +
                linesep + linesep.join(lst_msg))

    @unittest.skip("skip example")
    def test_example_1(self):
        level=6
        for coord in [[-136.7, -61.5],[-136.7, 61.5], [-92.9, -34.0]]:
            rc = tile_utils.coord_to_row_col(coord, level)
            print(level,coord,rc)

    @unittest.skip("skip unused")
    def test_bbox_to_quad_tile(self):
        self._test_bbox_to_quad_tile(tile_utils.bboxToListQuadkey)
        # self._test_bbox_to_quad_tile(tile_utils.bboxToListColRow)

    def _test_bbox_to_quad_tile(self, fn):
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
