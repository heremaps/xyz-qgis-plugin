# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.core import (QgsVectorLayer, QgsWkbTypes, QgsProject, QgsFeatureRequest,
    QgsCoordinateReferenceSystem, QgsCoordinateTransform)
from qgis.utils import iface

from . import parser
from ..common.signal import make_print_qgis

print_qgis = make_print_qgis("render")

######### to Memory Layer
import json
def geojson_to_meta_str(txt):
    """ txt is assumed to be small
    """
    vlayer = QgsVectorLayer(txt, "tmp", "ogr")

    crs_str = vlayer.sourceCrs().toWkt()
    wkb_type = vlayer.wkbType()
    geom_str = QgsWkbTypes.displayString(wkb_type)
    feat_cnt = vlayer.featureCount()
    return geom_str, crs_str, feat_cnt
def get_vlayer(layer_id):
    vlayer = QgsProject.instance().mapLayer(layer_id)
    if layer_id is None or vlayer is None: 
        print_qgis("no vlayer found!!")
        return None
    return vlayer

# mixed-geom
def parse_feature(obj, map_fields, similarity_threshold=None, **kw_params):
    map_feat, map_fields = parser.xyz_json_to_feature_map(obj, map_fields,similarity_threshold)
    return map_feat, map_fields, kw_params

def truncate_add_render(vlayer, feat, new_fields):
    pr = vlayer.dataProvider()
    if pr.truncate():
        vlayer.updateExtents()
    return add_feature_render(vlayer, feat, new_fields)

def clear_features_in_extent(vlayer, extent):
    pr = vlayer.dataProvider()
    
    crs_src = "EPSG:4326"
    crs_dst = vlayer.crs()

    transformer = parser.make_transformer(crs_src, crs_dst)
    if transformer.isValid() and not transformer.isShortCircuited():
        extent = transformer.transformBoundingBox(extent, handle180Crossover=True)

    it = pr.getFeatures(
        QgsFeatureRequest(extent).setSubsetOfAttributes([0])
        .setFlags(QgsFeatureRequest.NoGeometry)
    )
    lst_fid = [ft.id() for ft in it]
    pr.deleteFeatures(lst_fid)
    vlayer.updateExtents()

# unused
def clear_features_in_feat(vlayer, feat: list):
    lst_bbox = [ft.geometry().boundingBox() for ft in feat]
    extent = lst_bbox[0]
    for bbox in lst_bbox[1:]:
        extent.combineExtentWith(bbox)
    clear_features_in_extent(vlayer, extent)

def add_feature_render(vlayer, feat, new_fields):
    pr = vlayer.dataProvider()
    geom_type = QgsWkbTypes.geometryType(pr.wkbType())

    # redundant geom transform
    # vlayer in xyz layer default to use 4326
    crs_src = QgsCoordinateReferenceSystem('EPSG:4326')
    crs_dst = vlayer.crs()
    transformer = parser.make_transformer(crs_src, crs_dst)

    # feat should be according to geom in parser.py
    # if geom_type < QgsWkbTypes.UnknownGeometry:
    # if QgsWkbTypes.geometryType(ft.geometry().wkbType()) == geom_type

    if transformer.isValid() and not transformer.isShortCircuited():
        feat = filter(None, (
            parser.transform_geom(ft, transformer) for ft in feat if ft
        ))

    names = set(vlayer.fields().names())
    diff_fields = [f for f in new_fields if not f.name() in names]
    
    # print_qgis(len(names), names)
    # print_qgis(len(new_fields), new_fields.names())
    # print_qgis(len(diff_fields), [f.name() for f in diff_fields])
    # print_qgis("field cnt of each feat", [len(f.fields()) for f in feat])
    # print_qgis(len(feat), [f.attribute(parser.QGS_ID) for f in feat])

    # fid has some value because xyz space has fid 
    # reset fid value (deprecated thanks to unique field name)
    # for i,f in enumerate(feat): f.setAttribute(parser.QGS_ID,None) 

    pr.addAttributes(diff_fields)
    vlayer.updateFields()

    ok, out_feat = pr.addFeatures(feat)
    vlayer.updateExtents() # will hide default progress bar
    # post_render(vlayer) # disable in order to keep default progress bar running
    return ok, out_feat
def post_render(vlayer):
    # print_qgis("Feature count:", vlayer.featureCount())

    if iface.mapCanvas().isCachingEnabled():
        vlayer.triggerRepaint()
    else:
        iface.mapCanvas().refresh()
        