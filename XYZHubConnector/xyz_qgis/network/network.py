# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


from qgis.PyQt.QtCore import QObject, QTimer
from qgis.PyQt.QtNetwork import QNetworkAccessManager

from . import datahub_servers
from .net_handler import NetworkHandler
from .net_utils import (
    make_conn_request,
    set_qt_property,
    prepare_new_space_info,
    make_payload,
    make_bytes_payload,
)
from ..models import SpaceConnectionInfo


##########


class NetManager(QObject):
    TIMEOUT_COUNT = 1000

    API_URL = datahub_servers.API_URL

    ENDPOINTS = {
        "space_meta": "/spaces/{space_id}",
        "statistics": "/spaces/{space_id}/statistics",
        "count": "/spaces/{space_id}/count",
        "edit_space": "/spaces/{space_id}",
        "del_space": "/spaces/{space_id}",
        "list_spaces": "/spaces",
        "add_space": "/spaces",
        "load_features_bbox": "/spaces/{space_id}/bbox",
        "load_features_iterate": "/spaces/{space_id}/iterate",
        "load_features_search": "/spaces/{space_id}/search",
        "load_features_tile": "/spaces/{space_id}/tile/{tile_schema}/{tile_id}",
        "add_features": "/spaces/{space_id}/features",
        "del_features": "/spaces/{space_id}/features",
    }

    def __init__(self, parent):
        super().__init__(parent)
        self.network = QNetworkAccessManager(self)

    #############
    def _pre_send_request(self, conn_info, endpoint_key: str, kw_path=dict(), kw_request=dict()):
        token, space_id = conn_info.get_xyz_space()

        api_url = conn_info.get_("server", self.API_URL["PRD"]).rstrip("/")
        endpoint = self.ENDPOINTS[endpoint_key]
        url = api_url + endpoint.format(space_id=space_id, **kw_path)
        request = make_conn_request(url, token, **kw_request)
        return request

    def _post_send_request(self, reply, conn_info, kw_prop=dict()):
        set_qt_property(reply, conn_info=conn_info, **kw_prop)

    def _send_request(
        self, conn_info, endpoint_key, kw_path=dict(), kw_request=dict(), kw_prop=dict()
    ):

        request = self._pre_send_request(
            conn_info, endpoint_key, kw_path=kw_path, kw_request=kw_request
        )

        reply = self.network.get(request)

        self._post_send_request(reply, conn_info, kw_prop=kw_prop)
        return reply

    #############
    # TODO: remove callback params
    def get_statistics(self, conn_info, kw_request=None):
        reply = self._get_space_(conn_info, "statistics", kw_request=kw_request)
        timeout = self.TIMEOUT_COUNT
        QTimer.singleShot(timeout, reply.abort)
        return reply

    def get_count(self, conn_info):
        reply = self._get_space_(conn_info, "count")
        return reply

    def get_meta(self, conn_info):
        return self._get_space_(conn_info, "space_meta")

    def _get_space_(self, conn_info, reply_tag, kw_request: dict = None):
        endpoint_key = reply_tag
        kw_request = kw_request or dict()
        kw_prop = dict(reply_tag=reply_tag)
        return self._send_request(conn_info, endpoint_key, kw_request=kw_request, kw_prop=kw_prop)

    def list_spaces(self, conn_info):
        endpoint_key = "list_spaces"
        kw_request = dict(includeRights="true")
        kw_prop = dict(reply_tag="spaces")
        return self._send_request(conn_info, endpoint_key, kw_request=kw_request, kw_prop=kw_prop)

    def add_space(self, conn_info, space_info):
        space_info = prepare_new_space_info(space_info)

        endpoint_key = "add_space"
        kw_request = dict(req_type="json")
        kw_prop = dict(reply_tag="add_space")

        request = self._pre_send_request(conn_info, endpoint_key, kw_request=kw_request)
        reply = self.network.post(request, make_payload(space_info))

        self._post_send_request(reply, conn_info, kw_prop=kw_prop)
        return reply

    def edit_space(self, conn_info, space_info):

        endpoint_key = "edit_space"
        kw_request = dict(req_type="json")
        kw_prop = dict(reply_tag="edit_space")

        request = self._pre_send_request(conn_info, endpoint_key, kw_request=kw_request)
        reply = self.network.sendCustomRequest(request, b"PATCH", make_bytes_payload(space_info))

        self._post_send_request(reply, conn_info, kw_prop=kw_prop)
        return reply

    def del_space(self, conn_info):

        endpoint_key = "del_space"
        kw_request = dict()
        kw_prop = dict(reply_tag="del_space")

        request = self._pre_send_request(conn_info, endpoint_key, kw_request=kw_request)
        reply = self.network.sendCustomRequest(request, b"DELETE")

        self._post_send_request(reply, conn_info, kw_prop=kw_prop)

        return reply

    def _prefix_query(self, txt, prefix="p.", prefixes=tuple()):
        """return prefix to xyz query:
        prefixes = ["p.", "f."] # add prefix if none in prefixes exists
        prefixes = [] # always add prefix, dont check existing
        """
        return prefix if not any(map(txt.startswith, prefixes)) else ""

    def _process_queries(self, kw):
        selection = ",".join(
            "{prefix}{name}".format(name=p, prefix=self._prefix_query(p, "p."))
            for p in kw.pop("selection", "").split(",")
            if p
        )
        if selection:
            kw["selection"] = selection
        self._process_raw_queries(kw)

    def _process_raw_queries(self, kw):
        filters = [
            "{prefix}{name}{operator}{value}".format(
                name=p["name"],
                operator=p["operator"],
                value=p["values"],
                prefix=self._prefix_query(p["name"], "p."),
            )
            for p in kw.pop("filters", list())
        ]
        if filters:
            kw.setdefault("raw_queries", list()).extend(filters)

    def load_features_bbox(self, conn_info, bbox, **kw):
        reply_tag = "bbox"
        endpoint_key = "load_features_bbox"
        self._process_queries(kw)
        kw_request = dict(bbox, **kw)
        kw_prop = dict(reply_tag=reply_tag, bbox=bbox, **kw)
        return self._send_request(conn_info, endpoint_key, kw_request=kw_request, kw_prop=kw_prop)

    def load_features_tile(self, conn_info, tile_id="0", tile_schema="quadkey", **kw):
        reply_tag = "tile"
        kw_tile = dict(tile_schema=tile_schema, tile_id=tile_id)
        endpoint_key = "load_features_tile"
        self._process_queries(kw)
        kw_prop = dict(reply_tag=reply_tag, **kw, **kw_tile)
        return self._send_request(
            conn_info, endpoint_key, kw_path=kw_tile, kw_request=kw, kw_prop=kw_prop
        )

    def load_features_iterate(self, conn_info, **kw):
        reply_tag = kw.pop("reply_tag", "iterate")
        endpoint_key = "load_features_iterate"
        self._process_queries(kw)
        kw_prop = dict(reply_tag=reply_tag, **kw)
        return self._send_request(conn_info, endpoint_key, kw_request=kw, kw_prop=kw_prop)

    def load_features_search(self, conn_info, **kw):
        reply_tag = kw.pop("reply_tag", "search")
        endpoint_key = "load_features_search"
        self._process_queries(kw)
        kw_prop = dict(reply_tag=reply_tag, **kw)
        return self._send_request(conn_info, endpoint_key, kw_request=kw, kw_prop=kw_prop)

    # feature function
    def add_features(self, conn_info, added_feat, **kw):
        send_request = (
            self.network.post
        )  # create or modify (merge existing feature with payload) # might add attributes
        return self._add_features(conn_info, added_feat, send_request, **kw)

    def modify_features(self, conn_info, added_feat, **kw):
        return self.add_features(conn_info, added_feat, **kw)

    def replace_features(self, conn_info, added_feat, **kw):
        # create or replace (replace existing feature with payload) # might add or drop attributes
        send_request = self.network.put
        return self._add_features(conn_info, added_feat, send_request, **kw)

    def _add_features(self, conn_info, added_feat, send_request, **kw):
        # POST, payload: list of FeatureCollection

        endpoint_key = "add_features"
        if "tags" in kw:
            kw["addTags"] = kw["tags"]
        kw_request = dict(req_type="geo", **kw)  # kw: query
        kw_prop = dict(reply_tag="add_feat")
        kw_prop.update(kw)
        request = self._pre_send_request(conn_info, endpoint_key, kw_request=kw_request)

        payload = make_payload(added_feat)
        reply = send_request(request, payload)
        self._post_send_request(reply, conn_info, kw_prop=kw_prop)

        # parallel case (merge output ? split input?)
        return reply

    def del_features(self, conn_info, removed_feat, **kw):
        # DELETE by Query URL, required list of feat_id

        query_del = {"id": ",".join(str(i) for i in removed_feat)}
        kw.update(query_del)

        endpoint_key = "del_features"
        kw_request = dict(kw)  # kw: query
        kw_prop = dict(reply_tag="del_feat")

        request = self._pre_send_request(conn_info, endpoint_key, kw_request=kw_request)

        reply = self.network.sendCustomRequest(request, b"DELETE")
        self._post_send_request(reply, conn_info, kw_prop=kw_prop)

        return reply

    def apply_connected_conn_info(self, conn_info: SpaceConnectionInfo):
        return conn_info

    #################
    # Network Handler
    #################

    def on_received(self, reply):
        return NetworkHandler.on_received(reply)
