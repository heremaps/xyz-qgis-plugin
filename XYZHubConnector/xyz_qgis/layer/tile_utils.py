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
        (0.5 - math.log((1 + sinLatitude) / (1 - sinLatitude)) / (4 * math.pi))
    ))
    return [y_percent, x_percent]

# https://developer.here.com/documentation/map-tile/common/map_tile/topics/mercator-projection.html
def coord_to_percent_here_mercator(coord, level):
    lon_, lat_ = coord
    lon, lat = map(math.radians,coord)
    tan = math.tan(math.pi/4 + lat/2)
    if tan == 0: 
        return coord_to_percent_here_mercator([lon_,lat_+1e-9],level)
        
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

# RowColLevel -> coordinate extent
def coord_from_percent_here_simple(y_percent, x_percent, level):
    longitude = max(-180, min(180,
        x_percent * 360 - 180
    ))
    latitude = max(-90, min(90,
        y_percent * 180 - 90
    ))
    return [longitude, latitude]

def coord_from_percent_web_mercator(y_percent, x_percent, level):
    x = x_percent - 0.5
    y = 0.5 - y_percent
    longitude = 360 * x
    latitude = 90 - 360 * math.atan(math.exp(-y * 2 * math.pi)) / math.pi
    # y_percent = max(0, min(1,
    #     1-(0.5 - math.log((1 + sinLatitude) / (1 - sinLatitude)) / (4 * math.pi))
    # ))
    return [longitude, latitude]

def coord_from_percent(y_percent, x_percent, level, schema="here"):
    if schema == "web":
        return coord_from_percent_web_mercator(y_percent,x_percent,level)
    else:
        return coord_from_percent_here_simple(y_percent,x_percent,level)

def extent_from_row_col(row, col, level, schema="here"):
    nrow, ncol = get_row_col_bounds(level, schema)
    r = row/nrow
    r1 = (row+1)/nrow
    c = col/ncol
    c1 = (col+1)/ncol
    if schema == "here":
        xy_min = coord_from_percent(r,c,level,schema)
        xy_max = coord_from_percent(r1,c1,level,schema)
        extent = xy_min + xy_max
    elif schema == "web":
        xy_min = coord_from_percent(r1,c,level,schema)
        xy_max = coord_from_percent(r,c1,level,schema)
        extent = xy_min + xy_max
    else:
        extent = [0,0,1,1] # dummy 
    # print(schema, level, extent, r,c,r1,c1)
    return extent

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
    return max(zoom, 1)

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

def get_tile_format(schema="here"):
    return "{level}_{col}_{row}"

def parse_tile_id(tile_id, schema="here"):
    return dict(zip(
        ["level","col","row"],
        map(int, tile_id.split("_"))
        ))

def bboxToListColRow(x_min,y_min,x_max,y_max,level,schema="here"):
    r1,r2,c1,c2 = bboxToLevelRowCol(x_min,y_min,x_max,y_max,level,schema)
    # clockwise spiral for web schema, counter-clockwise spiral for web schema
    # reverse one list to reverse spiral
    lst_row = list(range(r1,r2+1))
    lst_col = list(range(c1,c2+1))
    # print(schema, level, [x_min,y_min,x_max,y_max], lst_col, lst_row)
    return [get_tile_format(schema=schema).format(level=level,row=row,col=col)
    for col, row in spiral_iter(lst_col, lst_row)]

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

def bboxFromLevelColRow():
    pass
