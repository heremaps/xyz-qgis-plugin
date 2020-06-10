# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os
import xml.etree.ElementTree as ET

from qgis.core import QgsDataSourceUri, QgsProject, QgsRasterLayer


def load_default_xml():
    d = os.path.dirname(__file__)
    return load_xml(os.path.join(d,"basemap.xml"))

def load_xml(file):
    tree = ET.parse(file)
    root = tree.getroot()
    map_meta = dict()
    for child in root:
        d = dict(child.attrib)
        map_meta[d["name"]] = d
    return map_meta
def add_auth(meta, app_id, app_code):
    sep = "&" if "?" in meta["url"] else "?"
    url = "{url}{sep}app_id={app_id}&app_code={app_code}".format(url=meta["url"], sep=sep, app_id=app_id, app_code=app_code)
    meta["url"] = url
# qgswmscapabilities.cpp
def parse_uri(meta):
    uri = QgsDataSourceUri()
    uri.setParam("type", "xyz")
    for k,v in meta.items():
        uri.setParam(k, v)
    return bytes(uri.encodedUri()).decode("utf-8")


def add_basemap_layer(meta, app_id, app_code):
    add_auth(meta, app_id, app_code)
    
    name = meta["name"]
    uri = parse_uri(meta)
    layer = QgsRasterLayer( uri, name, "wms")
    
    tree_root = QgsProject.instance().layerTreeRoot()
    pos = len(tree_root.children())  # Insert to bottom

    QgsProject.instance().addMapLayer(layer, False)
    
    tree_root.insertLayer(pos, layer)
