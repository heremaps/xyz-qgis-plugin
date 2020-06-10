# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from XYZHubConnector.xyz_qgis.layer import parser, tile_utils, bbox_utils
from XYZHubConnector.xyz_qgis.network import net_handler
from test.make_point_layer import step_from_level, iter_lon_lat
from qgis.testing import start_app

app = start_app()

class Counter():
    def __init__(self, total, callback):
        self.cnt = 0
        self.total = total
        self.callback = callback
    def count_reply(self, reply):
        self.cnt += 1
        print("Progress: %s/%s"%(self.cnt, self.total))
        if self.cnt == self.total:
            self.callback()
            print("Done")

def get_row_col_bounds_here(level):
    """ 
    [x,y] or [col, row], start from bottom left, go anti-clockwise
    level 0: 0,0
    level 1: 0,0; 1,0
    level 2: 0,0; 0,1; 1,0; 1,1; 2,0; 2,1; 3,0; 3,1
    """
    nrow = 2**(level-1) if level else 1
    ncol = 2**level
    return nrow, ncol

def get_row_col_bounds_web(level):
    """ 
    coord [x,y]
    """
    nrow = 2**(level) if level else 1
    ncol = 2**level
    return nrow, ncol

def get_row_col_bounds_tms(level):
    """ 
    coord [x,y]
    """
    nrow = 2**(level) if level else 1
    ncol = 2**level
    return nrow, ncol

def generate_tile(level,schema="web"):
    lst = list()
    if schema == "here":
        nrow, ncol = get_row_col_bounds_here(level)
    elif schema in ("web"):
        nrow, ncol = get_row_col_bounds_web(level) # missing coord y=-90
    elif schema in ("tms"):
        nrow, ncol = get_row_col_bounds_tms(level) # missing coord y=-90
    else:
        nrow, ncol = get_row_col_bounds_here(level)
    lst = [
        "%s_%s_%s"%(level,c,r)
        for r in range(nrow) for c in range(ncol)
    ]
    # lst = ["0_0_0","0_0_1","0_0_2","0_0_3","0_0_4","0_0_5","0_0_6","0_0_100"] # tms
    # lst = ["1_1_1","1_0_1","1_1_0","1_0_0"] # + lst
    # lst += ["2_1_2"]
    return lst

def make_coord(level):
    step = step_from_level(level)
    return list(iter_lon_lat(step))

def make_tuple_coord(level):
    return set(tuple(coord) for coord in make_coord(level))
class Validator():
    def __init__(self, level):
        self.level = level
        self.cnt_x = (180*2)//step_from_level(level) + 1
        lst_coord = make_tuple_coord(level)
        self.expected = dict(
            cnt=len(lst_coord),
            lst_coord=set(lst_coord)
        )
        self.actual = dict(cnt=0, lst_coord=list())

    def check_cnt(self, cnt):
        print("feat per tile", cnt)
        actual, expected = self._get_case("cnt", cnt)
        print(actual, expected, actual == expected,
            "cnt")

    def check_coord(self, lst_coord):
        actual_, expected = self._get_case("lst_coord", lst_coord)
        actual = set(actual_)
        print(len(actual_), len(actual), len(actual_) - len(actual),
            "overlap")
        print(len(actual), len(expected), len(actual) == len(expected),
            "unique")
        print("len y=-90", self.cnt_x)
        actual_ = sorted(actual_)
        print("actual", actual_[:1], actual_[-1:])
        missing = sorted(expected.difference(actual))
        print("missing", len(missing), list(missing)[:2], list(missing)[-2:])

        diff = sorted(actual.difference(expected))
        print("diff", len(diff), list(diff)[:2], list(diff)[-2:])
        
    def _get_case(self, key, val):
        self.actual[key] += val
        return self.actual[key], self.expected[key]

    def check_reply(self, reply):
        a, kw = net_handler.on_received(reply)
        obj = a[0]
        feat = obj["features"]
        feat_cnt = len(feat)
        self.check_cnt(feat_cnt)
        lst_coord = set(tuple(ft["geometry"]["coordinates"]) for ft in feat)
        self.check_coord(lst_coord)

class BoundedValidator(Validator):
    def __init__(self, level, x_min, y_min, x_max, y_max):
        super().__init__(level)
        step = step_from_level(level)
        step = 1
        x_min, y_min, x_max, y_max = map(
            lambda x: int(x) + (0 if int(x) > x else 1), 
            [x_min, y_min, x_max, y_max])
        lst_coord = [(lon, lat)
            for lon in range(x_min,x_max,step) 
            for lat in range(y_min,y_max,step)
            ]
        self.expected = dict(
            cnt=len(lst_coord),
            lst_coord=set(lst_coord)
        )

if __name__ == "__main__":
    
    from XYZHubConnector.xyz_qgis.network import NetManager
    from qgis.PyQt.QtCore import QEventLoop, Qt
    from XYZHubConnector.xyz_qgis.models.connection import SpaceConnectionInfo
    conn_info = SpaceConnectionInfo()
    conn_info.set_(space_id="DicZ8XTR",token="AdOZrFlyIrXLzbAJeN5Lzts")

    tile_schema="here"
    level=9

    # # all
    # tags = "%s-%s"%("point",level)
    # rect = [-180, -90, 180, 90] 
    # lst_tiles = generate_tile(level, tile_schema)
    # print(lst_tiles)
    # validator = Validator(level)
    
    # bounded
    tags = "point"
    # rect = [-180, -90, -165, -65] 
    # rect = [-136.7, -61.5, -92.9, -34.0]  # level 5
    rect = [-136.9, -61.5, -130.9, -55.5] # level 9
    # higher level require moore precise coord
    
    lst_tiles = tile_utils.bboxToListColRow(*rect,level,tile_schema)
    print(lst_tiles)
    validator = BoundedValidator(level, *rect)

    lst_params = [
        dict(tile_schema=tile_schema, tile_id=t, limit=100000,tags=tags)
        for t in lst_tiles
    ]
    total = len(lst_tiles)

    loop = QEventLoop(app)
    network = NetManager(app)

    counter = Counter(total, loop.quit)

    network.network.finished.connect(validator.check_reply)
    network.network.finished.connect(counter.count_reply)

    for i,params in enumerate(lst_params):
        network.load_features_tile(conn_info, **params)

    loop.exec_()
