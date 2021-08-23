# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.PyQt.QtCore import QByteArray
from ...controller import make_qt_args

from ...network.net_handler import (
    NetworkHandler,
    NetworkResponse,
    NetworkTimeout,
    NetworkError,
    NetworkUnauthorized,
)

from ...common.signal import make_print_qgis

print_qgis = make_print_qgis("iml.net_handler")


class IMLNetworkUnauthorized(NetworkUnauthorized):
    pass


def on_received(reply):
    return IMLNetworkHandler.on_received(reply)


class IMLNetworkHandler(NetworkHandler):
    @classmethod
    def handle_error(cls, resp: NetworkResponse):
        resp.log_status()

        err = resp.get_error()
        status = resp.get_status()

        if err == resp.get_reply().OperationCanceledError:  # operation canceled
            raise NetworkTimeout(resp)
        elif status in (401, 403):
            raise IMLNetworkUnauthorized(resp)
        elif err > 0 or not status:
            raise NetworkError(resp)

    @classmethod
    def on_received_impl(cls, response):
        print_qgis("Receiving")
        if response.is_dummy():
            raw = QByteArray()
            txt = ""
            obj = {}
        else:
            raw = response.get_body_qbytearray()
            txt = response.get_body_txt()
            obj = response.get_body_json()

        conn_info, reply_tag = response.get_qt_property(["conn_info", "reply_tag"])
        token, space_id = conn_info.get_xyz_space() if conn_info is not None else (None, None)
        limit, handle, meta = response.get_qt_property(["limit", "handle", "meta"])
        tile_schema, tile_id = response.get_qt_property(["tile_schema", "tile_id"])
        (layerType,) = response.get_qt_property(["layerType"])

        args = list()
        kw = dict()

        if reply_tag == "spaces":
            print_qgis(txt)
            items = obj["results"]["items"]
            # aggregate layers from different catalog
            lst_layer_meta = [
                dict(catalog=it.get("id", ""), catalog_hrn=it.get("hrn", ""), **layer)
                for it in items
                for layer in it.get("layers", tuple())
                if not layerType
                or not layer.get("layerType")
                or layer.get("layerType") == layerType
            ]
            args = [conn_info, lst_layer_meta]
        elif reply_tag in ("tile", "bbox", "iterate", "search"):
            print_qgis(txt[:100])
            print_qgis(txt[-10:])

            print_qgis(
                "feature count:%s" % len(obj["features"])
                if "features" in obj
                else "no features key"
            )
            print_qgis(obj.keys())

            args = [obj]
            if reply_tag == "tile":
                kw = dict(limit=limit, tile_schema=tile_schema, tile_id=tile_id)
            else:
                kw = dict(handle=handle, limit=limit)

        elif reply_tag in ("init_layer",):
            print_qgis(txt[:100])
            print_qgis(txt[-10:])
            args = [txt, raw]
        elif reply_tag in ("add_feat", "del_feat", "sync_feat"):
            # TODO: error handling, rollback layer, but already commited  !?!
            if len(txt):
                print_qgis("updated features")
            else:
                print_qgis("added/removed features")
            print_qgis(txt[:100])

            args = [obj]
        elif reply_tag in ("add_space", "edit_space", "del_space"):
            args = [conn_info, obj]
        elif reply_tag in ("add_layer", "edit_layer", "del_layer"):
            args = [conn_info, obj]
        elif reply_tag in ("get_catalog",):
            args = [conn_info, obj]
        elif reply_tag in ("statistics", "count", "space_meta"):
            print_qgis(txt[:100])
            args = [conn_info, obj]
        elif reply_tag in ("oauth",):
            print_qgis(txt[:100])
            args = [conn_info, obj]
        elif reply_tag in ("get_project",):
            print_qgis(txt[:100])
            project = obj["items"][0] if obj["total"] > 0 else dict()
            args = [conn_info, project]
        else:
            print_qgis(reply_tag)
            print_qgis(txt[:100])
        # response.get_reply().deleteLater() #
        # return make_qt_args(reply_tag, *args, **kw)
        return make_qt_args(*args, **kw)
