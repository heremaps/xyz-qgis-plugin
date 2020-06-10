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

from qgis.core import QgsFeatureRequest, QgsProject
from qgis.PyQt.QtCore import QVariant


from ..models import SpaceConnectionInfo
from ..controller import make_qt_args
from . import parser
from .layer_props import QProps


def is_valid_json(txt):
    try:
        obj = json.loads(txt)
    except ValueError as e:
        return False
    return True
def load_json_default(txt, default=None):
    obj = default
    try:
        obj = json.loads(txt)
    except ValueError as e:
        pass
    return obj

def get_feat_iter(vlayer):
    # assert isinstance(vlayer, QgsVectorLayer)
    return vlayer.getFeatures(), vlayer
def get_feat_upload_from_iter_args(feat_iter, vlayer):
    a = get_feat_upload_from_iter(feat_iter, vlayer)
    return make_qt_args(*a)
def get_feat_upload_from_iter(feat_iter, vlayer, lst_fid=list(), lst_xyz_id=list()):
    """ get feature as geojson from iter. Also return lst_fid ordering
    optinal input: lst_fid order and lst_xyz_id mapping
    ensure same order as lst_fid
    """
    map_feat = dict(map(lambda ft: (ft.id(), ft), feat_iter))
    if len(map_feat) == 0:
        return list(), list()
    if len(lst_fid) > 0:
        it = ((k, map_feat.get(k)) for k in lst_fid)
    else:
        it = map_feat.items()
    lst_fid, lst_feat = zip(*it)

    crs_src = vlayer.crs()
    crs_dst = 'EPSG:4326'
    transformer = parser.make_transformer(crs_src, crs_dst)
    if transformer.isValid() and not transformer.isShortCircuited():
        lst_feat = filter(None, (
            parser.transform_geom(ft, transformer) for ft in lst_feat
        ))

    added_feat = parser.feature_to_xyz_json(lst_feat, is_new=False) 
    for ft, xyz_id in zip(added_feat, lst_xyz_id):
        if ft is None or xyz_id is None: continue
        ft[parser.XYZ_ID] = xyz_id
    it = zip(lst_fid, added_feat)
    lst_fid, added_feat = zip(*[(k, v) for k, v in it if v is not None])
    obj = parser.make_lst_feature_collection(added_feat)
    return obj, lst_fid
def get_xyz_id_from_feat(ft, null=None):
    x = ft.attribute(parser.QGS_XYZ_ID)
    if x is None or (isinstance(x, QVariant) and (x.isNull() or not x.isValid())):
        x = null
    return x
def get_iter_xyz_id_from_src(src):
    return src.getFeatures(
        QgsFeatureRequest().setSubsetOfAttributes([parser.QGS_XYZ_ID], src.fields())
        .setFlags(QgsFeatureRequest.NoGeometry)
    )
def get_feat_cnt_from_src(src):
    return len(list(get_iter_xyz_id_from_src(src)))
def make_xyz_id_map_from_src(src, lst_fid):
    it = src.getFeatures(
        QgsFeatureRequest(lst_fid).setSubsetOfAttributes([parser.QGS_XYZ_ID], src.fields())
        .setFlags(QgsFeatureRequest.NoGeometry)
    )
    m = dict([
        (ft.id(), get_xyz_id_from_feat(ft)) for ft in it
    ])
    return m
def get_xyz_id_from_iter(feat_iter):
    return list(map(get_xyz_id_from_feat, feat_iter))
def get_xyz_id_from_layer(vlayer, fid):
    ft = vlayer.getFeature(fid)
    return get_xyz_id_from_feat(ft)
def is_layer_committed(vlayer):
    return not (vlayer.isEditable() and vlayer.undoStack().count() > 0)
def update_feat_of_layer(vlayer, ft):
    """ Precondition: given feature has fid that exists in vlayer or vlayer.dataProvider()
    """
    fid = ft.id()
    if not is_layer_committed(vlayer):
        if fid >= 0:
            ft.setAttribute(0, fid) # ensure updating matching, non-null fid
        vlayer.updateFeature(ft)
    else:
        attr_map = {fid: dict(list(enumerate(ft.attributes()))[1:])} # skip updating fid
        geom_map = {fid: ft.geometry()}
        vlayer.dataProvider().changeAttributeValues(attr_map)
        if ft.hasGeometry():
            vlayer.dataProvider().changeGeometryValues(geom_map)
        vlayer.updateExtents()
        
def update_feat_non_null(vlayer, ft):
    """ Precondition: given feature has fid that exists in vlayer or vlayer.dataProvider()
    """
    fid = ft.id()
    attrs = list(enumerate(ft.attributes()))
    attr_map = dict((i,v) for i, v in attrs if v is not None)
    geom = ft.geometry()
    if not is_layer_committed(vlayer):
        # if fid >= 0:
        #     ft.setAttribute(0, fid) # ensure updating matching, non-null fid
        vlayer.changeAttributeValues(fid, attr_map)
        if ft.hasGeometry():
            vlayer.changeGeometry(fid, geom)
    else:
        vlayer.dataProvider().changeAttributeValues({fid: attr_map})
        if ft.hasGeometry():
            vlayer.dataProvider().changeGeometryValues({fid: geom})
        vlayer.updateExtents()
def get_layer(layer_id):
    return QgsProject.instance().mapLayer(layer_id)
def get_customProperty_str(qnode, key):
    return str(QProps.getProperty(qnode,key))

def get_conn_info_from_layer(layer_id):
    vlayer = get_layer(layer_id)
    if vlayer is None: return
    conn_info = get_customProperty_str(vlayer, QProps.CONN_INFO)
    conn_info = json.loads(conn_info)
    conn_info = SpaceConnectionInfo.from_dict(conn_info)
    return conn_info

def updated_xyz_node(qnode):
    QProps.updatePropsVersion(qnode)
    return qnode
def is_xyz_supported_node(qnode):
    meta = get_customProperty_str(qnode, QProps.LAYER_META)
    flag = isinstance(meta, str) and is_valid_json(meta)
    return flag
def is_xyz_supported_layer(vlayer):
    return is_xyz_supported_node(vlayer)
def iter_group_node(root):
    for g in root.findGroups():
        yield g
        for gg in iter_group_node(g):
            yield gg
