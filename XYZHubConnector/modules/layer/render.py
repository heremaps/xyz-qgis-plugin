# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
#
###############################################################################

from qgis.core import QgsVectorLayer, QgsWkbTypes, QgsProject
from qgis.utils import iface

from . import parser
from ..common.signal import make_print_qgis

print_qgis = make_print_qgis("render")



######### to Memory Layer
import json
def geojson_to_meta_str(txt):
    """ txt is assumed to be small
    """
    # # fix bad geom (copy from uom)
    # obj = json.loads(txt)
    # if "geometry" not in obj["features"][0]:
    #     obj["features"] = [parser.fix_json_geom_single(ft) for ft in obj["features"]]
    # txt = json.dumps(obj) 

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
    
# mixed-geom (TODO)
def merge_feature(txt, vlayer, fields, exist_feat_id):
    raise NotImplementedError("parsed_feat")
    key = parser.QGS_XYZ_ID
    feat, new_fields = parser.xyz_json_to_feature(txt, fields)
    feat = [ft for ft in feat if ft.attribute(key) not in exist_feat_id]
    return vlayer, feat, new_fields

# mixed-geom
def parse_feature(txt, map_fields):
    map_feat, map_fields = parser.xyz_json_to_feature(txt, map_fields)
    return map_feat, map_fields
    
def truncate_add_render(vlayer, feat, new_fields):
    pr = vlayer.dataProvider()
    if pr.truncate():
        vlayer.updateExtents()
    return add_feature_render(vlayer, feat, new_fields)
def add_feature_render(vlayer, feat, new_fields):
    pr = vlayer.dataProvider()
    geom_type = QgsWkbTypes.geometryType(pr.wkbType())

    # print_qgis("wkb_type: %s. geom1: %s"%(geom_type, QgsWkbTypes.geometryType(feat[0].geometry().wkbType()) ))

    if geom_type < QgsWkbTypes.UnknownGeometry:
        feat = [ft for ft in feat if QgsWkbTypes.geometryType(ft.geometry().wkbType()) == geom_type]

    # print_qgis("wkb_type: %s. feat len: %s"%(geom_type,len(feat)))

    names = set(vlayer.fields().names())
    diff_fields = [f for f in new_fields if not f.name() in names]
    
    print_qgis(len(names), names)
    print_qgis(len(new_fields), new_fields.names())
    print_qgis(len(diff_fields), [f.name() for f in diff_fields])

    pr.addAttributes(diff_fields)
    vlayer.updateFields()

    pr.addFeatures(feat)
    vlayer.updateExtents() # will hide default progress bar
    # post_render(vlayer) # disable in order to keep default progress bar running

def post_render(vlayer):
    # print_qgis("Feature count:", vlayer.featureCount())

    if iface.mapCanvas().isCachingEnabled():
        vlayer.triggerRepaint()
    else:
        iface.mapCanvas().refresh()

    # # force showing progress bar after refresh has little effect 
    # pb = iface.statusBarIface().children()[2]
    # pb.show()
    
#     # update cache in manager
#     if not layer_id in self.qfeat_id:
#         self.qfeat_id[layer_id] = set()
#     self.qfeat_id[layer_id] = self.qfeat_id[layer_id].union(ft.id() for ft in vlayer.getFeatures())
