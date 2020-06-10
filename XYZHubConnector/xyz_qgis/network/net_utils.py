# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


########## UTILS

import gzip
import json
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtCore import QBuffer, QByteArray

API_CIT_URL = "https://xyz.cit.api.here.com/hub"
API_PRD_URL = "https://xyz.api.here.com/hub"
API_SIT_URL = "https://xyz.sit.cpdev.aws.in.here.com/hub"
API_URL = dict(PRD=API_PRD_URL, CIT=API_CIT_URL, SIT=API_SIT_URL)

from ..common.signal import make_print_qgis
print_qgis = make_print_qgis("net_utils")

def check_gzip(byt):
    return byt[:2] == b"\037\213" # get from gzip.py
def decode_byte(byt):
    byt = bytes(byt)
    if check_gzip(byt):
        byt = gzip.decompress(byt)
    txt = byt.decode("utf-8")
    try:
        obj = json.loads(txt) if len(txt) else dict()
    except json.JSONDecodeError:
        obj = dict()

    return byt, txt, obj
def _make_headers(token, **params):
    h = {
        "Authorization": "Bearer %s"% token,
        "Accept" : "*/*",
        "Accept-Encoding": "gzip"
    }
    h.update(params)
    return h
def make_request(url, token, **header):
    request = QNetworkRequest(url)
    for k, v in _make_headers(token, **header).items():
        k = k.encode("utf-8")
        v = v.encode("utf-8")
        request.setRawHeader(k, v)
    return request
def make_gzip_request( url, token):
    header = {
        "Accept-Encoding": "gzip"
    }
    return make_request(url, token, **header)
def make_geo_request( url, token):
    header = {
        "Content-Type": "application/geo+json"
    }
    return make_request(url, token, **header)
def make_json_request( url, token):
    header = {
        "Content-Type": "application/json"
    }
    return make_request(url, token, **header)
def make_payload( obj):
    txt = json.dumps(obj,ensure_ascii = False)
    return txt.encode("utf-8")
def make_buffer( obj):
    data = QByteArray(make_payload(obj))
    buffer = QBuffer()
    buffer.setData(data)
    buffer.open(buffer.ReadOnly)
    return buffer
def make_query_url( url, **kw):
    query = "&".join(
        "%s=%s"%(k,v)
        for k,v in kw.items() if not v is None
    )
    if len(query): 
        url = "%s?%s"%(url, query)
    url = QUrl(url)
    return url

HEADER_EXTRA_MAP = dict(
    normal = {},
    geo= {"Content-Type": "application/geo+json"},
    json={"Content-Type": "application/json"},
    gzip={"Accept-Encoding": "gzip"}
)
def make_conn_request(conn_info, endpoint, req_type="normal", **kw):
    """Make request from conn_info (token,space_id,api_url, auth,etc.) 
    :param: req_type: type of request:
        "normal": normal
        "gzip"
        "geo"
        "json"

    """
    token, space_id = conn_info.get_xyz_space()
    api_url = API_URL[conn_info.server]
    url = api_url + endpoint.format(space_id=space_id)
    url = make_query_url(url, **kw)
    header = HEADER_EXTRA_MAP.get(req_type,dict())
    return make_request(url, token, **header)

##########################################
# data flow in reply (QNetworkReply)

def set_qt_property(qobj, **kw):
    for k,v in kw.items():
        qobj.setProperty(str(k), QVariant(v))
def get_qt_property(qobj, keys):
    return [qobj.property(k) for k in keys] 

##########################################
    
META_SIGNATURE = "\n\n#XYZ+QGIS"

def prepare_new_space_info(space_info):
    """space_info = meta
    add qgis-xyz plugin signature
    remove fields for updating meta
    """
    space_info = dict(space_info)
    space_info.pop("owner",0)
    space_info.pop("id",0)
    space_info.pop("space_id",0)
    # insertBBox false is not accepted by xyz
    if not space_info.get("insertBBox") is True: 
        space_info.pop("insertBBox",0)
    space_info["description"] += META_SIGNATURE
    return space_info
