# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.core import (QgsCoordinateReferenceSystem, QgsCoordinateTransform,
                       QgsGeometry, QgsProject)
from qgis.gui import QgsMapCanvas
from typing import Iterable, Tuple

def get_bounding_box(canvas: QgsMapCanvas , crs="EPSG:4326"):
    """
    Get the geometry of the bbox in WGS84

    @rtype: QGsRectangle in WGS84
    @return: the extent of the map canvas
    """
    radioButton_extentMapCanvas = True
    # get extend of mapcanvas
    if radioButton_extentMapCanvas:
        geom_extent = canvas.extent()
        if hasattr(canvas, "mapSettings"):
            source_crs = canvas.mapSettings().destinationCrs()
        else:
            source_crs = canvas.mapRenderer().destinationCrs()
    # get extend of layer
    else: 
        # layer = self.comboBox_extentLayer.currentLayer()
        # geom_extent = layer.extent()
        # source_crs = layer.crs()
        pass
    geom_extent = QgsGeometry.fromRect(geom_extent)
    dest_crs = QgsCoordinateReferenceSystem(crs)
    crs_transform = QgsCoordinateTransform(
        source_crs, dest_crs, QgsProject.instance())
    geom_extent.transform(crs_transform)
    return geom_extent.boundingBox()
    
def extent_to_rect(extent):
    y_min = extent.yMinimum()
    y_max = extent.yMaximum()
    x_min = extent.xMinimum()
    x_max = extent.xMaximum()
    x_min = max(x_min,-180)
    x_max = min(x_max, 180)
    y_min = max(y_min,-90)
    y_max = min(y_max, 90)
    return (x_min,y_min,x_max,y_max)

def extend_to_bbox(extent):
    (x_min,y_min,x_max,y_max) = extent_to_rect(extent)
    return rect_to_bbox(x_min,y_min,x_max,y_max)

def rect_to_bbox(x_min,y_min,x_max,y_max):
    bbox = dict(zip(
        ["west","east","south","north"],
        (x_min,x_max,y_min,y_max)
    ))
    # print(bbox)
    return bbox
def bbox_to_rect(bbox):
    rect = [bbox[k] for k in ["west","south","east","north"]]
    return rect
def _linspace(x0,x1,n):
    """ return a list from x0 to x1 with n+1 element (n gaps)
    """
    dx = (x1-x0)/n
    lst = [x0 + dx*i for i in range(n)]
    lst.append(x1)
    lst = list(map(lambda x: round(x,2), lst))
    return lst
def _split_lim(x0,x1,n):
    x = _linspace(x0,x1,n)
    return list(zip(x, x[1:]))
def split_bbox(bbox,nx,ny):
    def _up_down_left_right():
        return [
            rect_to_bbox(x[0],y[0],x[1],y[1]) 
            for y in reversed(y_pairs) for x in x_pairs
            # for y in y_pairs for x in x_pairs
        ]
    def _spiral_pairs():
        it = ((x_pairs[ix], y_pairs[iy]) for ix, iy in spiral_index(len(x_pairs), len(y_pairs)))
        return [
            rect_to_bbox(x[0],y[0],x[1],y[1]) 
            for x, y in it
        ]
    x_min,y_min,x_max,y_max = bbox_to_rect(bbox)

    x_pairs = _split_lim(x_min, x_max, nx)
    y_pairs = _split_lim(y_min, y_max, ny)
    
    return list(_spiral_pairs())
    # return list(_up_down_left_right())

# https://stackoverflow.com/questions/398299/looping-in-a-spiral
def spiral_index(X, Y) -> Iterable[Tuple[int,int]]:
    """ center x,y = (0,0)
    xmin,xmax = ( -(X-xmax-1), X//2)
    ymin,ymax = ( -(Y-ymax-1), Y//2)
    top left x,y=( xmin, ymax)
    bottom right x,y=( xmax, ymin)
    """
    xmax,ymax = X//2, Y//2
    xmin,ymin = -(X-xmax-1), -(Y-ymax-1)
    x = y = 0
    dx = 0
    dy = -1
    for i in range(max(X, Y)**2):
        if (-X/2 < x <= X/2) and (-Y/2 < y <= Y/2): # check bound
            # print (x, y) 
            yield (x - xmin, y - ymin) # convert to index
        # if on diagonal (top-right, bot-left) or top left diag or in right line
        if x == y or (x < 0 and x == -y) or (x > 0 and x == 1-y):
            dx, dy = -dy, dx # change direction
        x, y = x+dx, y+dy
