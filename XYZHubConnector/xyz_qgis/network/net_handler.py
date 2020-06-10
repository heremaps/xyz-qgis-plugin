# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtNetwork import QNetworkRequest

from qgis.core import Qgis, QgsMessageLog # to be removed
from .net_utils import decode_byte, get_qt_property
from ..controller import make_qt_args
from ..common import config

from ..common.signal import make_print_qgis
print_qgis = make_print_qgis("net_handler")

class NetworkError(Exception): 
    pass
class NetworkTimeout(Exception): 
    pass

############# reply handler
    
def get_status(reply):
    return reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
def get_reason(reply):
    return reply.attribute(QNetworkRequest.HttpReasonPhraseAttribute)

def check_status(reply):
    err = reply.error()
    err_str = reply.errorString()
    status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
    reason = reply.attribute(QNetworkRequest.HttpReasonPhraseAttribute)
    
    conn_info, reply_tag = get_qt_property(reply,["conn_info", "reply_tag"])
    token, space_id = conn_info.get_xyz_space() if not conn_info is None else (None, None)
    url = reply.request().url().toString()

    if err > 0:
        msg = "%s: %s: %s. %s. %s - %s. request: %s"%(reply_tag, status, reason, err_str, token, space_id, url)
        QgsMessageLog.logMessage( 
            "Network Error! : %s"%msg, config.TAG_PLUGIN, Qgis.Warning
        )
    else:
        msg = "%s: %s: %s. %s - %s. request: %s"%(reply_tag, status, reason, token, space_id, url)
        QgsMessageLog.logMessage(
            "Network Ok! : %s"%msg, config.TAG_PLUGIN, Qgis.Success
        )
    return reply_tag, status, reason, err, err_str

def on_received(reply):
    reply_tag, status, reason, err, err_str = check_status( reply)
    url = reply.request().url().toString()
    if err == reply.OperationCanceledError: # operation canceled
        reason = "Timeout"
        body = ""
        raise NetworkTimeout(reply_tag, status, reason, body, err_str, url, reply)
    elif err > 0:
        raw = reply.readAll()
        byt, body, obj = decode_byte( raw)
        raise NetworkError(reply_tag, status, reason, body, err_str, url, reply)
    return _onReceived( reply)

def _onReceived(reply):

    print_qgis("Receiving")
    raw = reply.readAll()
    byt, txt, obj = decode_byte( raw)
    conn_info, reply_tag = get_qt_property(reply,["conn_info", "reply_tag"])
    token, space_id = conn_info.get_xyz_space() if not conn_info is None else (None, None)
    limit, handle, meta = get_qt_property(reply,["limit", "handle", "meta"])
    tile_schema, tile_id = get_qt_property(reply,["tile_schema", "tile_id"])

    args = list()
    kw = dict()
    
    if reply_tag == "spaces":
        print_qgis(txt)
        args = [obj]
    elif reply_tag in ("tile","bbox","iterate","search"):
        print_qgis(txt[:100])
        print_qgis(txt[-10:])

        print_qgis("feature count:%s"%len(obj["features"]) if "features" in obj else "no features key")
        print_qgis(obj.keys())

        args = [obj]
        if reply_tag == "tile":
            kw = dict(limit=limit, tile_schema=tile_schema, tile_id=tile_id)
        else:
            kw = dict(handle=handle, limit=limit)
            
    elif reply_tag in ("init_layer"):
        print_qgis(txt[:100])
        print_qgis(txt[-10:])
        args = [txt, raw]
    elif reply_tag in ("add_feat","del_feat","sync_feat"):
        #TODO: error handling, rollback layer, but already commited  !?!
        if len(txt):
            print_qgis("updated features")
        else:
            print_qgis("added/removed features")
        print_qgis(txt[:100])
        
        args = [obj]
    elif reply_tag in ("add_space","edit_space","del_space"):

        args = [conn_info, obj]
    elif reply_tag in ("statistics", "count","space_meta"):
        print_qgis(txt[:100])
        args = [conn_info, obj]
    else:
        print_qgis(reply_tag)
        print_qgis(txt[:100])
    reply.deleteLater()
    # return make_qt_args(reply_tag, *args, **kw)
    return make_qt_args(*args, **kw)
    