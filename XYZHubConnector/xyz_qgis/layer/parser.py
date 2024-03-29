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
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCsException,
    QgsCoordinateTransform,
    QgsFeature,
    QgsProject,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsJsonUtils,
)

from ..common.signal import make_print_qgis, print_error

print_qgis = make_print_qgis("parser")

QGS_XYZ_ID = "xyz_id"
XYZ_ID = "id"
QGS_ID = "fid"
QGS_SPECIAL_KEYS = [QGS_ID, QGS_XYZ_ID]
XYZ_SPECIAL_KEYS = ["@ns:com:here:xyz"]
ALL_SPECIAL_KEYS = set(QGS_SPECIAL_KEYS).union(XYZ_SPECIAL_KEYS)


PAYLOAD_LIMIT = int(1e7)  # Amazon API limit: 10485760
URL_LIMIT = 2000  # max url length: 2000
URL_BASE_LEN = 60  # https://xyz.api.here.com/hub/spaces/12345678/features/
DEFAULT_SIMILARITY_THRESHOLD = 0  # single: 0, balnced: 80


def make_lst_removed_ids(removed_ids):
    if len(removed_ids) > 0:
        len_id = len(removed_ids[0]) + 1
        limit = URL_LIMIT - URL_BASE_LEN
        chunk_size = max(1, limit // len_id)
    else:
        chunk_size = 1
    print_qgis("chunk", chunk_size)
    return [removed_ids[i : i + chunk_size] for i in range(0, len(removed_ids), chunk_size)]


def estimate_chunk_size(byt):
    chunk_size = PAYLOAD_LIMIT // len(byt)  # round down
    return chunk_size


def estimate_upload_chunk_single(lst):
    # CAREFUL estimate chunk size using 1 feature not works everytime
    # each feature has different size !!!
    b = json.dumps(lst[0]).encode("utf-8")
    chunk_size = estimate_chunk_size(b)
    if len(b) > PAYLOAD_LIMIT:
        print_qgis("impossible to upload. 1 feature is larger than API LIMIT")
    print_qgis(
        "Features size: %s. Chunk size: %s. N: %s"
        % (len(lst), chunk_size, math.ceil(len(lst) / chunk_size))
    )
    return chunk_size


def make_lst_feature_collection(features):
    if len(features) == 0:
        return list()
    chunk_size = estimate_upload_chunk_single(features)

    def _filter(features):
        return list(filter(None, features))

    def _iter_collection(features):
        i0, i1 = 0, 0
        while i1 < len(features):
            siz = PAYLOAD_LIMIT + 1
            i1 = i0 + (chunk_size * 2)
            while siz > PAYLOAD_LIMIT:
                step = (i1 - i0) // 2
                i1 = i0 + step
                obj = feature_collection(features[i0:i1])
                siz = len(json.dumps(obj).encode("utf-8"))
            if step == 0:
                print_qgis("impossible to upload. 1 feature is larger than API LIMIT")
                return
            yield obj
            i0 = i1

    return list(_iter_collection(_filter(features)))


def split_feature_collection(collection, size_first=1):
    c1 = dict(collection)
    c1["features"] = c1["features"][0:size_first]
    collection["features"] = collection["features"][size_first:]
    return c1, collection


def split_feature_collection_txt(txt, size_first=1):
    obj = json.loads(txt)
    c1, c2 = split_feature_collection(obj, size_first)
    return json.dumps(c1), json.dumps(c2)


def feature_collection(features):
    return {"type": "FeatureCollection", "features": features}


def transform_geom(ft, transformer):
    geom = ft.geometry()
    try:
        geom.transform(transformer)
    except QgsCsException as e:
        print_error(e)
        return
    ft.setGeometry(geom)
    return ft


def make_transformer(crs_src, crs_dst):
    def _crs(crs):
        return QgsCoordinateReferenceSystem(crs) if isinstance(crs, str) else crs

    crs_src, crs_dst = map(_crs, [crs_src, crs_dst])
    return QgsCoordinateTransform(crs_src, crs_dst, QgsProject.instance())


def make_valid_xyz_json_geom(geom: dict):
    coord_str = json.dumps(geom["coordinates"])
    coord = json.loads(coord_str.replace("null", "0.0"))
    geom["coordinates"] = coord
    return geom


def non_expression_fields(fields):
    return [f for i, f in enumerate(fields) if fields.fieldOrigin(i) != fields.OriginExpression]


def check_non_expression_fields(fields):
    return all(fields.fieldOrigin(i) != fields.OriginExpression for i, f in enumerate(fields))


def feature_to_xyz_json(features, is_new=False, ignore_null=True, is_livemap=False):
    def _xyz_props(props, ignore_keys=tuple()):
        # convert from qgs case insensitive fields back to json properties
        # convert from json string to json object
        new_props = dict()
        for t in props.keys():
            if ignore_null and props[t] is None:
                continue
            k = normal_field_name(t)

            if k in ignore_keys:
                continue
            new_props[k] = props[t]

            # always handle json string in props
            new_props[k] = try_parse_json_string(new_props[k])
        return new_props

    def _livemap_props(props, xyz_id=None):
        # handle editing of delta layer
        delta = {"changeState": "CREATED", "reviewState": "UNPUBLISHED", "taskGridId": ""}
        if xyz_id:
            delta.update({"changeState": "UPDATED", "originId": xyz_id})
        return {"@ns:com:here:mom:delta": delta}

    def _clean_props(props):
        # drop @ fields for upload
        ignored_special_keys = [k for k in props.keys() if k.startswith("@")]
        for k in ignored_special_keys:
            props.pop(k, None)
        return props

    def _single_feature(feat):
        # existing feature json
        if feat is None:
            return None
        obj = {"type": "Feature"}
        json_str = QgsJsonUtils.exportAttributes(feat)
        props = json.loads(json_str)
        props.pop(QGS_ID, None)
        v = props.pop(QGS_XYZ_ID, None)
        if v is not None and v != "":
            if v in exist_feat_id:
                return None
            exist_feat_id.add(v)
            if not is_new:
                obj[XYZ_ID] = v
        fields = feat.fields()
        expression_field_names = [
            f.name()
            for i, f in enumerate(fields)
            if fields.fieldOrigin(i) == fields.OriginExpression
        ]
        # print({k.name(): fields.fieldOrigin(i) for i, k in enumerate(fields)})
        props = _xyz_props(props, ignore_keys=expression_field_names)
        livemap_props = _livemap_props(props, xyz_id=obj.get(XYZ_ID)) if is_livemap else dict()
        props = _clean_props(props)
        obj["properties"] = dict(props, **livemap_props)

        geom = feat.geometry()
        geom_ = json.loads(geom.asJson())
        if geom_ is None:
            # print_qgis(obj)
            return obj
        obj["geometry"] = make_valid_xyz_json_geom(geom_)

        # bbox = geom.boundingBox() # print_qgis("bbox: %s"%bbox.toString()) if bbox.isEmpty():
        # if "coordinates" in geom_: obj["bbox"] = list(geom_["coordinates"]) * 2 else: obj[
        # "bbox"] = [bbox.xMinimum(), bbox.yMinimum(), 0.0, bbox.xMaximum(), bbox.yMaximum(),
        # 0.0] obj["bbox"] = [bbox.xMinimum(), bbox.yMinimum(), bbox.xMaximum(), bbox.yMaximum()]
        return obj

    assert isinstance(features, (list, tuple))
    exist_feat_id = set()
    return [_single_feature(ft) for ft in features]


# https://github.com/qgis/QGIS/blob/f3e9aaf79a9282b28a605abd0dadaab9951050c8/python/plugins/processing/algs/qgis/ui/FieldsMappingPanel.py
valid_fieldTypes = dict(
    [
        (QVariant.Date, "Date"),
        (QVariant.DateTime, "DateTime"),
        (QVariant.Double, "Double"),
        (QVariant.Int, "Integer"),
        (QVariant.LongLong, "Integer64"),
        (QVariant.String, "String"),
        (QVariant.Bool, "Boolean"),
    ]
)

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


def make_field(k, val):
    qtype = val.type()
    f_typeName = valid_fieldTypes.get(qtype, "String")
    return QgsField(k, qtype, f_typeName)


def try_parse_json_string(v):
    if isinstance(v, str) and ("{" in v or "[" in v):
        # print_qgis(json.dumps(dict(v=v), ensure_ascii=False))
        try:
            obj = json.loads(v)
            return obj
        except json.JSONDecodeError:
            pass
    return v


def is_json_string(v):
    return v != try_parse_json_string(v)


def make_field_from_type_name(k, f_typeName):
    """
    make QgsField from qgis typeName (values of `valid_fieldTypes`).
    TypeName is also shown in QGIS:
    layer Properties > Information > Fields
    """
    return QgsField(k, typeName=f_typeName)


def fix_json_geom_single(ft):
    if "uom" not in ft["properties"]:
        return ft
    uom = ft["properties"].pop("uom")
    for k in ["geometry", "bbox"]:
        if k in uom:
            ft[k] = uom[k]
    ft["properties"].update(uom["properties"])
    return ft


def has_case_different_dupe(ref_names, names):
    all_names = set(ref_names).union(names)
    lnames = list(map(str.lower, all_names))
    has_dupe = len(set(lnames)) < len(lnames)
    if has_dupe:
        for n in set(lnames):
            lnames.remove(n)
        # print("dupe case", lnames)
    return has_dupe


def is_special_key(k):
    return k in ALL_SPECIAL_KEYS


def filter_props_names(fields_names):
    return [s for s in fields_names if not is_special_key(s)]


def fields_similarity(ref_names, orig_names, names) -> int:
    """
    compute fields similarity [0..100].

    High score means 2 given fields are similar and should be merged
    """
    ref_names = filter_props_names(ref_names)
    names = filter_props_names(names)
    same_names = set(ref_names).intersection(names)
    n1, n2 = map(len, [ref_names, names])
    x = len(same_names)
    # if n1 == 0 or n2 == 0: return 1 # handle empty, variant 1
    if n1 == 0 and n2 == 0:
        return 100  # handle empty, variant 2
    return int(max((100 * x / n) if n > 0 else 0 for n in [n1, n2]))


def new_fields_gpkg():
    fields = QgsFields()
    fields.append(make_field_from_type_name(QGS_ID, "Integer64"))
    return fields


def unique_field_name(name, new_name_fmt="{name}_{idx}"):
    if name.lower() not in QGS_SPECIAL_KEYS:
        return name
    upper_idx = "".join(str(i) for i, s in enumerate(name) if s.isupper())
    new_name = new_name_fmt.format(name=name, idx=upper_idx)
    return new_name


def normal_field_name(name):
    key = "_".join(name.split("_")[0:-1])
    if key.lower() not in QGS_SPECIAL_KEYS:
        return name
    return key


def rename_special_props(props):
    """
    rename json properties that duplicate qgis special keys, eg. id, fid
    """
    mapper = lambda key: unique_field_name(key) if key.lower() in QGS_SPECIAL_KEYS else key
    return {mapper(key): value for key, value in props.items()}


def _attrs(props):
    """Convert types to string, because QgsField cannot handle"""
    for k, v in props.items():
        if isinstance(v, (dict, list, tuple)):
            o = json.dumps(v, ensure_ascii=False)
        else:
            o = v
        yield k, o


def xyz_json_to_feature(feat_json, fields):
    """
    Convert xyz geojson to feature, given fields
    """

    names = set(fields.names())

    qattrs = list()

    # handle xyz id
    v = feat_json.get(XYZ_ID, "")
    val = QVariant(v)
    qattrs.append([QGS_XYZ_ID, val])

    if QGS_XYZ_ID not in names:
        fields.append(make_field(QGS_XYZ_ID, val))

    props = feat_json.get("properties")
    if isinstance(props, dict):
        props = rename_special_props(props)  # rename fid in props
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
                print_qgis("Field '%s': Invalid type: %s. Value: %s" % (k, val.typeName(), val))
                continue
            if k not in names:
                fields.append(make_field(k, val))
            qattrs.append([k, val])

    feat = QgsFeature(fields)

    for k, v in qattrs:
        feat.setAttribute(k, v)

    geom = feat_json.get("geometry")
    if geom is not None:
        s = json.dumps(geom)
        geom_ = QgsGeometry.fromWkt(ogr.CreateGeometryFromJson(s).ExportToWkt())
        feat.setGeometry(geom_)

    return feat


def check_same_fields(fields1: QgsFields, fields2: QgsFields):
    """
    Check if fields order, name and origin are equal

    :param fields1: QgsFields
    :param fields2: other QgsFields
    :return: True if 2 fields are equal (same order, name, origin)
    """
    len_ok = len(fields1) == len(fields2)
    name_ok = fields1.names() == fields2.names()
    field_origin_ok = all(
        fields1.fieldOrigin(i) == fields2.fieldOrigin(i)
        for i, (f1, f2) in enumerate(zip(fields1, fields2))
    )
    return len_ok and name_ok and field_origin_ok


def update_feature_fields(feat: QgsFeature, fields: QgsFields, ref: QgsFields):
    """
    Update fields of feature and its data (QgsAttributes)

    :param feat: QgsFeature
    :param fields: new QgsFields
    :return: new QgsFeature with updated fields
    """
    old_fields = feat.fields()
    names, old_names = fields.names(), old_fields.names()
    try:
        assert set(names).issuperset(set(old_names)), (
            "new fields must be a super set of existing fields of feature.\n"
            + "new: {} {}\nold: {} {}\nref: {} {}".format(
                len(names), names, len(old_names), old_names, len(ref.names()), ref.names()
            )
        )
    except AssertionError as e:
        print_error(e)
        return

    ft = QgsFeature(fields)
    for k in old_fields.names():
        ft.setAttribute(k, feat.attribute(k))
    ft.setGeometry(feat.geometry())
    return ft


def prepare_fields(feat_json, lst_fields, threshold=DEFAULT_SIMILARITY_THRESHOLD):
    """
    Decide to merge fields or create new fields based on fields similarity score [0..1].
    Score lower than threshold will result in creating new fields instead of merging fields
    """
    # adapt to existing fields
    props = feat_json.get("properties")
    if not isinstance(props, dict):
        orig_props_names = list()
        props_names = list()
    else:
        orig_props_names = [k for k, v in props.items() if v is not None]
        props = rename_special_props(props)  # rename fid in props
        props_names = [k for k, v in props.items() if v is not None]
    lst_score = [
        fields_similarity(
            [f.name() for f in non_expression_fields(fields)],
            orig_props_names,
            props_names,
        )
        if fields.size() > 1
        else -1  # mark empty fields
        for fields in lst_fields
    ]
    idx, score = max(enumerate(lst_score), key=lambda x: x[1], default=[0, 0])
    idx_min, score_min = min(enumerate(lst_score), key=lambda x: x[1], default=[0, 0])

    if len(lst_fields) == 0 or (score < threshold and score_min > -1):  # new fields
        idx = len(lst_fields)
        fields = new_fields_gpkg()
        lst_fields.append(fields)
    elif score_min == -1:  # select empty fields
        idx = idx_min
        fields = lst_fields[idx]
    else:  # select fields with highest score
        fields = lst_fields[idx]
    # print("len prop", len(props_names), idx, "score", lst_score, "lst_fields", len(lst_fields))
    # print("len fields", [f.size() for f in lst_fields])

    return fields, idx


def xyz_json_to_feature_map(
    obj, map_fields=None, similarity_threshold=DEFAULT_SIMILARITY_THRESHOLD
):
    """
    xyz json to feature, organize in to map of geometry,
    then to list of list of features.
    Features in inner lists have the same fields.

        :param map_fields: parse json object to existing map_fields
        :param similarity_threshold: percentage threshold of fields similarity from [0-100]
            0: map_fields should have 1 fields/geom
            100: map_fields should have as many as possible fields/geom
    """

    def _single_feature_map(feat_json, map_feat_, map_fields_):
        geom = feat_json.get("geometry")
        g = geom["type"] if geom is not None else None

        # # promote to multi geom
        # if g is not None and not g.startswith("Multi"): g = "Multi" + g

        lst_fields = map_fields_.setdefault(g, list())
        fields, idx = prepare_fields(feat_json, lst_fields, similarity_threshold)

        feat = xyz_json_to_feature(feat_json, fields)
        lst_fields[idx] = feat.fields()
        # FIX: as fields is modified during processing, reassign it to lst_fields

        lst_feat = map_feat_.setdefault(g, list())
        while len(lst_feat) < len(lst_fields):
            lst_feat.append(list())
        lst_feat[idx].append(feat)

    lst_all_feat = obj["features"]
    if map_fields is None:
        map_fields = dict()
    # map_feat = dict()
    map_feat = dict((k, [list() for _ in enumerate(v)]) for k, v in map_fields.items())

    for ft in lst_all_feat:
        _single_feature_map(ft, map_feat, map_fields)

    return map_feat, map_fields
