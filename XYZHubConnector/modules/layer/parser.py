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
    return name # disable
    if name.startswith("@"):
        return name
    return name + ".%s"%i 
def normal_field_name(name):
    return name # disable
    if name.startswith("@"):
        return name
    parts = name.split(".")
    if len(parts) > 1 and parts[-1].isdigit():
        return ".".join(parts[0:-1])
    return name

PAYLOAD_LIMIT = int(1e7) # Amazon API limit: 10485760
URL_LIMIT = 2000 # max url length: 2000
URL_BASE_LEN = 60 # https://xyz.api.here.com/hub/spaces/12345678/features/

def make_lst_removed_ids(removed_ids):
    if len(removed_ids) > 0:
        len_id = len(removed_ids[0]) + 1
        limit = URL_LIMIT-URL_BASE_LEN
        chunk_size = max(1, limit // len_id)
    else:
        chunk_size = 1
    print_qgis("chunk", chunk_size)
    return [removed_ids[i:i+chunk_size] 
        for i in range(0,len(removed_ids),chunk_size)]

def estimate_chunk_size(byt):
    chunk_size = PAYLOAD_LIMIT // len(byt) # round down
    return chunk_size

def estimate_upload_chunk_single(lst):
    # CAREFUL estimate chunk size using 1 feature not works everytime
    # each feature has different size !!!
    b=json.dumps(lst[0]).encode("utf-8")
    chunk_size = estimate_chunk_size(b)
    if len(b) > PAYLOAD_LIMIT:
        print_qgis("impossible to upload. 1 feature is larger than API LIMIT")
    print_qgis("Features size: %s. Chunk size: %s. N: %s"%(len(lst), chunk_size, math.ceil(len(lst)/chunk_size) ))
    return chunk_size
def make_lst_feature_collection(features):
    if len(features) == 0: 
        return list()
    chunk_size = estimate_upload_chunk_single(features)
    def _filter(features):
        return list(filter(None, features))
    def _iter_collection(features):
        i0, i1= 0,0
        while i1 < len(features):
            siz = PAYLOAD_LIMIT + 1
            i1 = i0 + (chunk_size * 2)
            while siz > PAYLOAD_LIMIT:
                step = (i1-i0) // 2
                i1 = i0 + step
                obj = feature_collection(features[i0:i1])
                siz = len(json.dumps(obj).encode("utf-8"))
            if step == 0:
                print_qgis("impossible to upload. 1 feature is larger than API LIMIT")
                return
            yield obj
            i0=i1
    return list(_iter_collection(_filter(features)))
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

def feature_to_xyz_json(feature, vlayer, is_new=False, ignore_null=True):
    def _xyz_props(props):
        # for all key start with @ (internal): str to dict (disabled)
        # k = "@ns:com:here:xyz"
        new_props = dict()
        for t in props.keys():
            # drop @ field, for consistency
            if t.startswith("@ns:com:here:xyz"): continue
            if ignore_null and props[t] is None: continue
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
        if feat is None: return None
        obj = {
            "type": "Feature"
        }
        json_str = QgsJsonUtils.exportAttributes(feat)
        props = json.loads(json_str)
        props.pop(QGS_ID, None)
        v = props.pop(QGS_XYZ_ID, None)
        if (v is not None and v is not ""):
            if v in exist_feat_id:
                return None
            exist_feat_id.add(v)
            if not is_new: obj[XYZ_ID] = v
                
        props = _xyz_props(props)
        obj["properties"] = props

        geom = feat.geometry()
        res = geom.transform(transformer)
        geom_ = json.loads(geom.asJson())
        if geom_ is None: 
            # print_qgis(obj)
            return obj
        obj["geometry"] = geom_

        # bbox = geom.boundingBox()
        # # print_qgis("bbox: %s"%bbox.toString())
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
    exist_feat_id = set()
    return [
        _single_feature(ft, transformer) 
        for ft in feature
    ]

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
def make_field_from_type_name(k, f_typeName):
    """
    make QgsField from qgis typeName (values of `valid_fieldTypes`).
    TypeName is also shown in QGIS: 
    layer Properties > Information > Fields
    """
    return QgsField(k, typeName=f_typeName)

def fix_json_geom_single(ft):
    if not "uom" in ft["properties"]:
        return ft
    uom = ft["properties"].pop("uom")
    for k in ["geometry", "bbox"]:
        if k in uom:
            ft[k] = uom[k]
    ft["properties"].update(uom["properties"])
    return ft

def is_new_fields(ref_names, names):
    return fields_similarity(ref_names, names) < 0.5
def has_case_different_dupe(ref_names, names):
    all_names = set(ref_names).union(names)
    lnames = list(map(str.lower, all_names))
    has_dupe = len(set(lnames)) < len(lnames)
    if has_dupe:
        for n in set(lnames):
            lnames.remove(n)
        # print("dupe case", lnames)
    return has_dupe

def to_props_names(fields_names):
    return [s for s in fields_names if s not in [QGS_ID, QGS_XYZ_ID]]
def fields_similarity(ref_names, names):
    """
    compute fields similarity [0..1]. 
    
    High score means 2 given fields are similar and should be merged
    """
    # ref_names = ref_fields.names()
    # names = fields.names()

    if has_case_different_dupe(ref_names, names):
        return 0
    ref_names = to_props_names(ref_names)
    same_names = set(ref_names).intersection(names)
    return max(
        (1.0*len(same_names)/x) if x > 0 else 0
        for x in map(len, [ref_names, names])
        )
def new_fields_gpkg():
    fields = QgsFields()
    fields.append(
        make_field_from_type_name(QGS_ID, "Integer64"))
    return fields
def rename_special_props(props):
    """
    rename json properties that duplicate qgis special keys
    """
    special_keys = {QGS_ID, QGS_XYZ_ID}
    new_name_fmt = "{old}_{upper_idx}"
    for old in props:
        if old.lower() not in special_keys: continue
        upper_idx = "".join(str(i) for i, s in enumerate(old) if s.isupper())
        new_name = new_name_fmt.format(
            old=old, upper_idx=upper_idx)
        props[new_name] = props.pop(old, None) # rename fid in props
def _attrs(props):
    """ Convert types to string, because QgsField cannot handle
    """
    for k,v in props.items():
        if isinstance(v, (dict,list,tuple)):
            o = json.dumps(v,ensure_ascii = False) 
        else:
            o = v
        yield k, o
def xyz_json_to_feat(feat_json, fields): 
    """ Convert xyz geojson to feature
    assume input geojson use crs = QgsCoordinateReferenceSystem('EPSG:4326')
    or geom.transform(transformer)
    """

    names = fields.names()

    qattrs = list()

    # handle xyz id
    v = feat_json.get(XYZ_ID,"")
    val = QVariant(v)
    qattrs.append([QGS_XYZ_ID,val])

    if QGS_XYZ_ID not in names:
        fields.append( make_field(QGS_XYZ_ID, val) )

    props = feat_json.get("properties")
    rename_special_props(props) # rename fid in props
    if isinstance(props, dict):
        attrs = list(_attrs(props))
        for k, v in attrs:
            val = QVariant(v)
            # if not val.isValid():
            #     val = QVariant("")
            if not val.type() in valid_fieldTypes:
                for cast in [QVariant.Int, QVariant.String]:
                    if val.canConvert(cast):
                        val.convert(cast)
                        break
            if not val.type() in valid_qvariant:
                print_qgis("Invalid type", k, val.typeName())
                continue
            if k not in names:
                fields.append( make_field(k, val))
            qattrs.append([k,val])

    feat=QgsFeature(fields)

    for k, v in qattrs:
        feat.setAttribute(k, v)

    geom = feat_json.get("geometry")
    if geom is not None:
        s = json.dumps(geom)
        geom_ = QgsGeometry.fromWkt(ogr.CreateGeometryFromJson(s).ExportToWkt())
        feat.setGeometry(geom_)

    return feat

def prepare_fields(feat_json, lst_fields):
    """
    Decide to merge fields or create new fields based on fields similarity score.
    Low score will result in creating new fields instead of merging fields
    """
    # adapt to existing fields
    props = feat_json.get("properties")
    # rename_special_props(props) # rename fid in props
    props_names = (
        [k for k, v in props.items() if v is not None] 
    if isinstance(props, dict) else [])
    lst_score = [fields_similarity(
        (fields.names()), props_names)
        for fields in lst_fields]
    print_qgis("score", lst_score)
    idx, score = max(enumerate(lst_score), key=lambda x:x[1],default=[0,0])
    print_qgis(idx, score)

    fields = new_fields_gpkg()
    if score < 0.8: # new fields
        idx = len(lst_fields)
        lst_fields.append(fields)
    else:
        fields = lst_fields[idx]
    
    return fields, idx

def xyz_json_to_feature_map(obj, map_fields=None):
    """ 
    xyz json to feature, organize in to map of geometry, 
    then to list of list of features. 
    Features in inner lists have the same fields. 
    """

    def _single_feature_map(feat_json, map_feat, map_fields):
        geom = feat_json.get("geometry")
        g = geom["type"] if geom is not None else None

        # # promote to multi geom
        # if g is not None and not g.startswith("Multi"): g = "Multi" + g
        
        lst_fields = map_fields.setdefault(g, list())
        fields, idx = prepare_fields(feat_json, lst_fields)
        ft = xyz_json_to_feat(feat_json, fields)

        lst = map_feat.setdefault(g, list())
        
        while len(lst) < len(lst_fields):
            lst.append(list())
        lst[idx].append(ft)

        
    lst_feat = obj["features"]
    if map_fields is None: map_fields = dict()
    # map_feat = dict()
    map_feat = dict(
        (k, [list() for i in enumerate(v)])
        for k, v in map_fields.items())
    crs = QgsCoordinateReferenceSystem('EPSG:4326')

    for ft in lst_feat:
        _single_feature_map(ft, map_feat, map_fields) 

    return map_feat, map_fields
