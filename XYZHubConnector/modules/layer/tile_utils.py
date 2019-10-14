# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import math

# hth GeoTools.ts
def tileXYToQuadKey(levelOfDetail, column, row):
    quadKey = ""
    for i in range(levelOfDetail,0,-1):
        digit = 0
        mask = 1 << (i - 1)
        if (row & mask) != 0:
            digit += 1
        if (column & mask) != 0:
            digit += 1
            digit += 1
        quadKey += str(digit)
    return quadKey

# hth GeoTools.ts
def coord_to_percent_bing_reversed(coord, level):
    longitude, latitude = coord
    sinLatitude = math.sin((latitude * math.pi) / 180)
    if abs(sinLatitude) == 1:
        return coord_to_percent_bing_reversed([longitude, latitude+1e-9], level)

    x_percent = max(0, min(1,
        ((longitude + 180) / 360)
    ))
    y_percent = max(0, min(1,
        1-(0.5 - math.log((1 + sinLatitude) / (1 - sinLatitude)) / (4 * math.pi))
    ))
    return [y_percent, x_percent]

# https://developer.here.com/documentation/map-tile/common/map_tile/topics/mercator-projection.html
def coord_to_percent_here_mercator(coord, level):
    lon_, lat_ = coord
    lon, lat = map(math.radians,coord)
    tan = math.tan(math.pi/4 + lat/2)
    if tan == 0: 
        return coord_to_percent([lon_,lat_+1e-9],level)
        
    x = lon/math.pi
    y = math.log(tan) / math.pi
    xmin, xmax = -1, 1
    fnY = lambda lat: math.log(math.tan(math.pi/4 + lat/2)) / math.pi
    ymin, ymax = map(fnY,map(math.radians,[-(90-1e-9), 90-1e-9]))
    col_percent = (x - xmin) / (xmax-xmin)
    row_percent = max(0,min(1, (y - ymin) / (ymax-ymin))) # incorrect scale
    return [row_percent, col_percent]

def coord_to_percent_here_simple(coord, level):
    longitude, latitude = coord
    x_percent = max(0, min(1,
        ((longitude + 180) / 360)
    ))
    y_percent = max(0, min(1,
        ((latitude + 90) / 180)
    ))
    return [y_percent, x_percent]

def get_row_col_bounds(level, schema="here"):
    """ 
    schema "here"
        [x,y], start from bottom left, go anti-clockwise
        level 0: 0,0
        level 1: 0,0; 1,0
        level 2: 0,0; 0,1; 1,0; 1,1; 2,0; 2,1; 3,0; 3,1
    """
    if schema == "here":
        nrow = 2**(level-1) if level else 1
        ncol = 2**level
    else:
        nrow = 2**(level) if level else 1
        ncol = 2**level
    return nrow, ncol
def coord_to_percent(coord, level, schema="here"):
    if schema == "here":
        row_percent, col_percent = coord_to_percent_here_simple(coord, level)
    else:
        row_percent, col_percent = coord_to_percent_bing_reversed(coord, level)
    return row_percent, col_percent
def coord_to_row_col(coord, level, schema="here"):
    r, c = coord_to_percent(coord, level, schema)
    nrow, ncol = get_row_col_bounds(level, schema)
    row = max(0,min(nrow-1, math.floor(r*nrow)))
    col = max(0,min(ncol-1, math.floor(c*ncol)))
    return row, col

def get_zoom_level_schema(level, schema="here"):
    """ 
    return valid zoom level according to schema
    """
    if schema == "here":
        level = min(max(level,0),31)
    else:
        pass
    return level

# vector_tiles_reader, tile_helper.py

_upper_bound_scale_to_zoom_level = {
    1000000000: 0,
    500000000: 1,
    200000000: 2,
    50000000: 3,
    25000000: 4,
    12500000: 5,
    6500000: 6,
    3000000: 7,
    1500000: 8,
    750000: 9,
    400000: 10,
    200000: 11,
    100000: 12,
    50000: 13,
    25000: 14,
    12500: 15,
    5000: 16,
    2500: 17,
    1500: 18,
    750: 19,
    500: 20,
    250: 21,
    100: 22,
    0: 23,
}


def get_zoom_for_current_map_scale(canvas):
	# canvas = self.iface.mapCanvas()
    scale = int(round(canvas.scale()))
    if scale < 0:
        return 23
    zoom = 0
    for upper_bound in sorted(_upper_bound_scale_to_zoom_level):
        if scale < upper_bound:
            zoom = _upper_bound_scale_to_zoom_level[upper_bound]
            break
    return zoom

def get_zoom_level(iface):
    # https://gis.stackexchange.com/questions/268890/get-current-zoom-level-from-qgis-map-canvas
    scale=iface.mapCanvas().scale()
    dpi=iface.mainWindow().physicalDpiX()
    maxScalePerPixel = 156543.04
    inchesPerMeter = 39.37
    zoomlevel = int(round(math.log( ((dpi* inchesPerMeter * maxScalePerPixel) / scale), 2 ), 0))
    return zoomlevel

# bbox

from .bbox_utils import spiral_index

def bboxToLevelRowCol(x_min,y_min,x_max,y_max,level,schema="here"):
    r1, c1 = coord_to_row_col([x_min,y_min],level,schema)
    r2, c2 = coord_to_row_col([x_max,y_max],level,schema)
    if r1 > r2:
        r1, r2 = r2, r1
    if c1 > c2:
        c1, c2 = c2, c1
    return r1, r2, c1, c2

def spiral_iter(lstX, lstY):
    for ix, iy in spiral_index(len(lstX), len(lstY)):
        yield (lstX[ix], lstY[iy]) 

def bboxToListColRow(x_min,y_min,x_max,y_max,level,schema="here"):
    level = get_zoom_level_schema(level, schema)
    r1,r2,c1,c2 = bboxToLevelRowCol(x_min,y_min,x_max,y_max,level,schema)
    lst_row = list(range(r1,r2+1))
    lst_col = list(range(c1,c2+1))
    return ["{level}_{col}_{row}".format(level=level,row=row,col=col)
    for col, row in spiral_iter(lst_col, lst_row)]

#### unused
def bboxToListQuadkey(x_min,y_min,x_max,y_max,level):
    r1,r2,c1,c2 = bboxToLevelRowCol(x_min,y_min,x_max,y_max,level)
    lst_row = list(range(r1,r2+1))
    lst_col = list(range(c1,c2+1))

    tiles = list()
    cached = set()
    for col, row in spiral_iter(lst_col, lst_row):
        t = tileXYToQuadKey(level, col, row)
        if t not in cached:
            tiles.append(t)
            cached.add(t)
    return tiles

def spiral_fast_iter(x_min,y_min,x_max,y_max):
    for ix, iy in spiral_index(x_max-x_min+1, y_max-y_min+1):
        yield x_min + ix, y_min +iy

def bboxToListQuadkeyFast(x_min,y_min,x_max,y_max,level):
    # not really faster
    r1,r2,c1,c2 = bboxToLevelRowCol(x_min,y_min,x_max,y_max,level)
    return [tileXYToQuadKey(level, col, row)
        for row, col in spiral_fast_iter(r1,r2,c1,c2)]
