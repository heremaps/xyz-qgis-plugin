# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import json
import math

from osgeo import ogr
from qgis.PyQt.QtCore import QVariant

from qgis.core import (QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform, QgsFeature, QgsProject, 
                       QgsField, QgsFields, QgsGeometry, QgsJsonUtils)

from ..common.signal import make_print_qgis

print_qgis = make_print_qgis("parser")

QGS_XYZ_ID = "xyz_id"
XYZ_ID = "id"

QGS_ID = "fid"


def unique_field_name(name, i):
    if name.startswith("@"):
        return name
    return name + ".%s"%i 
def normal_field_name(name):
    if name.startswith("@"):
        return name
    parts = name.split(".")
    if len(parts) > 1 and parts[-1].isdigit():
        return ".".join(parts[0:-1])
    return name

LIMIT = int(1e7) # Amazon API limit: 10485760
def estimate_chunk_size(byt):
    chunk_size = LIMIT // len(byt) # round down
    return chunk_size

def estimate_upload_chunk_single(lst):
    # CAREFUL estimate chunk size using 1 feature not works everytime
    # each feature has different size !!!
    b=json.dumps(lst[0]).encode("utf-8")
    chunk_size = estimate_chunk_size(b)
    if len(b) > LIMIT:
        print("impossible to upload. 1 feature is larger than API LIMIT")
    print("Features size: %s. Chunk size: %s. N: %s"%(len(lst), chunk_size, math.ceil(len(lst)/chunk_size) ))
    return chunk_size
def make_lst_feature_collection(features):
    if len(features) == 0: 
        return list()
    chunk_size = estimate_upload_chunk_single(features)
    def _iter_collection():
        i0, i1= 0,0
        while i1 < len(features):
            siz = LIMIT + 1
            i1 = i0 + (chunk_size * 2)
            while siz > LIMIT:
                step = (i1-i0) // 2
                i1 = i0 + step
                obj = feature_collection(features[i0:i1])
                siz = len(json.dumps(obj).encode("utf-8"))
            if step == 0:
                print("impossible to upload. 1 feature is larger than API LIMIT")
                return
            yield obj
            i0=i1
    return list(_iter_collection())
def split_feature_collection(collection,size_first=1):
    c1 = dict(collection)
    c1["features"] = c1["features"][0:size_first]
    collection["features"] = collection["features"][size_first:]
    return c1, collection
def split_feature_collection_txt(txt,size_first=1):
    obj = json.loads(txt)
    c1,c2 = split_feature_collection(obj, size_first)
    return json.dumps(c1), json.dumps(c2)
def feature_collection(features):
    return {
        "type": "FeatureCollection",
        "features": features
    }

def feature_to_xyz_json(feature, vlayer, is_new=False):
    def _xyz_props(props):
        # for all key start with @ (internal): str to dict (disabled)
        # k = "@ns:com:here:xyz"
        new_props = dict()
        for t in props.keys():
            # drop @ field, for consistency
            if t.startswith("@ns:com:here:xyz"): continue
            k = normal_field_name(t)
            new_props[k] = props[t]

            # # disabled
            # if not k.startswith("@"): continue
            # v = new_props[k]
            # if isinstance(v,str): # no need to handle json str in props
            #     # print_qgis(json.dumps(dict(v=v), ensure_ascii=False))
            #     try: new_props[k] = json.loads(v)
            #     except json.JSONDecodeError: pass # naively handle error
        return new_props
    def _single_feature(feat, transformer):
        # existing feature json
        obj = {
            "type": "Feature"
        }
        json_str = QgsJsonUtils.exportAttributes(feat)
        props = json.loads(json_str)
        props.pop(QGS_ID,"")
        if QGS_XYZ_ID in props:
            v = props.pop(QGS_XYZ_ID)
            if not is_new: obj[XYZ_ID] = v
                
        props = _xyz_props(props)
        obj["properties"] = props

        geom = feat.geometry()
        res = geom.transform(transformer)
        geom_ = json.loads(geom.asJson())
        if geom_ is None: 
            # print(obj)
            return obj
        obj["geometry"] = geom_

        # bbox = geom.boundingBox()
        # # print("bbox: %s"%bbox.toString())
        # if bbox.isEmpty():
        #     if "coordinates" in geom_:
        #         obj["bbox"] = list(geom_["coordinates"]) * 2
        # else:
        #     obj["bbox"] = [bbox.xMinimum(), bbox.yMinimum(), 0.0, bbox.xMaximum(), bbox.yMaximum(), 0.0]
        #     obj["bbox"] = [bbox.xMinimum(), bbox.yMinimum(), bbox.xMaximum(), bbox.yMaximum()]
        return obj
        
    assert isinstance(feature,(list, tuple))
    crs_src = vlayer.crs()
    crs_dst = QgsCoordinateReferenceSystem('EPSG:4326')
    transformer = QgsCoordinateTransform(crs_src, crs_dst, QgsProject.instance())
    return list( 
        _single_feature(ft, transformer) 
        for ft in feature if ft.hasGeometry() # FIX: XYZHub doesnt like empty geom
    )

# https://github.com/qgis/QGIS/blob/f3e9aaf79a9282b28a605abd0dadaab9951050c8/python/plugins/processing/algs/qgis/ui/FieldsMappingPanel.py
valid_fieldTypes = dict([
    (QVariant.Date, "Date"),
    (QVariant.DateTime, "DateTime"),
    (QVariant.Double, "Double"),
    (QVariant.Int, "Integer"),
    (QVariant.LongLong, "Integer64"),
    (QVariant.String, "String"),
    (QVariant.Bool, "Boolean")
])

# https://github.com/qgis/QGIS/blob/bcaad3a5dc30783e56ff6ab24467cd4046d76c42/src/core/providers/memory/qgsmemoryprovider.cpp#L431
valid_qvariant = [
    QVariant.Int,
    QVariant.Double,
    QVariant.String,
    QVariant.Date,
    QVariant.Time,
    QVariant.DateTime,
    QVariant.LongLong,
    QVariant.StringList,
    QVariant.List,
]
def make_field(k,val):
    qtype = val.type()
    f_typeName = valid_fieldTypes.get(qtype, "String")
    return QgsField(k, qtype, f_typeName)

def fix_json_geom_single(ft):
    if not "uom" in ft["properties"]:
        return ft
    uom = ft["properties"].pop("uom")
    for k in ["geometry", "bbox"]:
        if k in uom:
            ft[k] = uom[k]
    ft["properties"].update(uom["properties"])
    return ft

def xyz_json_to_feature(txt, map_fields=dict()):
    """ Convert xyz geojson to feature
    assume input geojson use crs = QgsCoordinateReferenceSystem('EPSG:4326')
    or geom.transform(transformer)
    """

    def _attrs(props):
        """ Convert types to string, because QgsField cannot handle
        """
        for k,v in props.items():
            if isinstance(v, (dict,list,tuple)):
                o = json.dumps(v,ensure_ascii = False) 
            else:
                o = v
            yield k, o
    def _single_feature(feat_json, fields):
        # adapt to existing fields
        feat=QgsFeature()
        
        names = fields.names()
        names_normal = list(map(normal_field_name, names))
        qattrs = list()

        # handle xyz id
        v = feat_json.get(XYZ_ID,"")
        val = QVariant(v)
        qattrs.append([QGS_XYZ_ID,val])

        if QGS_XYZ_ID not in names:
            fields.append( make_field(QGS_XYZ_ID, val) )
            

        props = feat_json.get("properties")
        if not props is None:
            attrs = list(_attrs(props))
            for k, v in attrs:
                val = QVariant(v)
                if not val.isValid():
                    val = QVariant("")
                # if not val.type() in valid_qvariant:
                if not val.type() in valid_fieldTypes:
                    for cast in [QVariant.Int, QVariant.String]:
                        if val.canConvert(cast):
                            val.convert(cast)
                            break
                if not val.type() in valid_qvariant:
                    print_qgis("Invalid type", k, val.typeName())
                    continue
                if k not in names_normal:
                    k = unique_field_name(k, len(fields))
                    fields.append( make_field(k, val))
                else:
                    idx = names_normal.index(k)
                    k = names[idx]
                qattrs.append([k,val])

            feat.setFields(fields)

        for k, v in qattrs:
            feat.setAttribute(k, v)

        return feat

    def _single_feature_map(feat_json, map_feat, map_fields):
        geom = feat_json.get("geometry")
        g = geom["type"] if geom is not None else None

        # promote to multi geom
        if g is not None and not g.startswith("Multi"): g = "Multi" + g
        
        fields = map_fields[g]
        ft = _single_feature(feat_json, fields)

        if g in map_feat:
            map_feat[g].append(ft)
        else:
            map_feat[g] = [ft]

        if g is None: return
            
        s = json.dumps(geom)
        geom_ = QgsGeometry.fromWkt(ogr.CreateGeometryFromJson(s).ExportToWkt())
        ft.setGeometry(geom_)
        
    obj = json.loads(txt)
    feature = obj["features"]

    map_feat = dict()
    crs = QgsCoordinateReferenceSystem('EPSG:4326')

    for ft in feature:
        _single_feature_map(ft, map_feat, map_fields) 

    return map_feat, map_fields
