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

from .net_utils import make_conn_request, set_qt_property, prepare_new_space_info, make_payload, make_buffer

TIMEOUT_COUNT = 1000

##########

class NetManager(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self.network = QNetworkAccessManager(self)

    #############
    def _pre_send_request(self,conn_info, endpoint, kw_request=dict()):
        assert(isinstance(endpoint,str))
        request = make_conn_request(conn_info, endpoint,**kw_request)
        return request

    def _post_send_request(self, reply, conn_info, kw_prop=dict()):
        set_qt_property(reply, conn_info=conn_info, **kw_prop)

    def _send_request(self,conn_info, endpoint, kw_request=dict(), kw_prop=dict()):
        
        request = self._pre_send_request(conn_info,endpoint,kw_request=kw_request)

        reply = self.network.get(request)

        self._post_send_request(reply,conn_info, kw_prop=kw_prop)
        return reply

    #############
    # TODO: remove callback params
    def get_statistics(self, conn_info):
        reply = self._get_space_(conn_info, "statistics")
        timeout = TIMEOUT_COUNT
        QTimer.singleShot(timeout, reply.abort)
        return reply
    def get_count(self, conn_info):
        reply = self._get_space_(conn_info, "count")
        return reply
    def get_meta(self, conn_info):
        return self._get_space_(conn_info, "space_meta")

    def _get_space_(self, conn_info, reply_tag):
        tag = "/" + reply_tag if reply_tag != "space_meta" else ""
        
        endpoint = "/spaces/{space_id}" + tag
        kw_request = dict()
        kw_prop = dict(reply_tag=reply_tag)
        return self._send_request(conn_info, endpoint, kw_request=kw_request, kw_prop=kw_prop)
        
    def list_spaces(self, conn_info):
        endpoint = "/spaces"
        kw_request = dict(includeRights="true")
        kw_prop = dict(reply_tag="spaces")
        return self._send_request(conn_info, endpoint, kw_request=kw_request, kw_prop=kw_prop)
        
    def add_space(self, conn_info, space_info):
        space_info = prepare_new_space_info(space_info)
        
        endpoint = "/spaces"
        kw_request = dict(req_type="json")
        kw_prop = dict(reply_tag="add_space")

        request = self._pre_send_request(conn_info,endpoint,kw_request=kw_request)
        reply = self.network.post(request, make_payload(space_info))

        self._post_send_request(reply,conn_info, kw_prop=kw_prop)
        return reply
    def edit_space(self, conn_info, space_info):
                
        endpoint = "/spaces/{space_id}"
        kw_request = dict(req_type="json")
        kw_prop = dict(reply_tag="edit_space")

        request = self._pre_send_request(conn_info,endpoint,kw_request=kw_request)
        buffer = make_buffer(space_info)
        reply = self.network.sendCustomRequest(request, b"PATCH", buffer)
        buffer.setParent(reply)
        
        self._post_send_request(reply,conn_info, kw_prop=kw_prop)
        return reply
        
    def del_space(self, conn_info):
        
        endpoint = "/spaces/{space_id}"
        kw_request = dict()
        kw_prop = dict(reply_tag="del_space")

        request = self._pre_send_request(conn_info,endpoint,kw_request=kw_request)
        reply = self.network.sendCustomRequest(request, b"DELETE")

        self._post_send_request(reply,conn_info, kw_prop=kw_prop)
        
        return reply

    def _prefix_query(self, txt, prefix="p.", prefixes=tuple()):
        """ return prefix to xyz query: 
            prefixes = ["p.", "f."] # add prefix if none in prefixes exists
            prefixes = [] # always add prefix, dont check existing
        """
        return prefix if not any(map(txt.startswith, prefixes)) else ""

    def _process_queries(self, kw):
        selection = ",".join(
            "{prefix}{name}".format(
                name=p,
                prefix=self._prefix_query(p, "p.")
            )
            for p in kw.pop("selection", "").split(",") if p
        )
        if selection: kw["selection"] = selection
        self._process_raw_queries(kw)

    def _process_raw_queries(self, kw):
        filters = [
            "{prefix}{name}{operator}{value}".format(
                name=p["name"],
                operator=p["operator"],
                value=p["values"],
                prefix=self._prefix_query(p["name"], "p.")
            )
            for p in kw.pop("filters", list())
        ]
        if filters: kw.setdefault("raw_queries", list()).extend(filters)

    def load_features_bbox(self, conn_info, bbox, **kw):
        reply_tag = "bbox"
        endpoint = "/spaces/{space_id}/bbox"
        self._process_queries(kw)
        kw_request = dict(bbox, **kw)
        kw_prop = dict(reply_tag=reply_tag, bbox=bbox, **kw)
        return self._send_request(conn_info, endpoint, kw_request=kw_request, kw_prop=kw_prop)

    def load_features_tile(self, conn_info, tile_id="0", tile_schema="quadkey", **kw):
        reply_tag = "tile"
        kw_tile = dict(tile_schema=tile_schema, tile_id=tile_id)
        tile_url = "tile/{tile_schema}/{tile_id}".format(**kw_tile)
        endpoint = "/spaces/{space_id}/" + tile_url
        self._process_queries(kw)
        kw_prop = dict(reply_tag=reply_tag, **dict(kw, **kw_tile))
        return self._send_request(conn_info, endpoint, kw_request=kw, kw_prop=kw_prop)

    def load_features_iterate(self, conn_info, **kw):
        reply_tag = kw.pop("reply_tag","iterate")
        endpoint = "/spaces/{space_id}/iterate"
        self._process_queries(kw)
        kw_prop = dict(reply_tag=reply_tag, **kw)
        return self._send_request(conn_info, endpoint, kw_request=kw, kw_prop=kw_prop)

    def load_features_search(self, conn_info, **kw):
        reply_tag = kw.pop("reply_tag","search")
        endpoint = "/spaces/{space_id}/search"
        self._process_queries(kw)
        kw_prop = dict(reply_tag=reply_tag, **kw)
        return self._send_request(conn_info, endpoint, kw_request=kw, kw_prop=kw_prop)
        
    ###### feature function
    def add_features(self, conn_info, added_feat, **kw):
        send_request = self.network.post # create or modify (merge existing feature with payload) # might add attributes
        return self._add_features(conn_info, added_feat, send_request, **kw)
    def modify_features(self, conn_info, added_feat, **kw):
        return self.add_features(conn_info, added_feat, **kw)
    def replace_features(self, conn_info, added_feat, **kw):
        send_request = self.network.put # create or replace (replace existing feature with payload) # might add or drop attributes
        return self._add_features(conn_info, added_feat, send_request, **kw)
    def _add_features(self, conn_info, added_feat, send_request, **kw):
        # POST, payload: list of FeatureCollection
        
        endpoint = "/spaces/{space_id}/features"
        if "tags" in kw: kw["addTags"] = kw["tags"]
        kw_request = dict(req_type="geo", **kw) # kw: query
        kw_prop = dict(reply_tag="add_feat")
        kw_prop.update(kw)
        request = self._pre_send_request(conn_info,endpoint,kw_request=kw_request)
        
        payload = make_payload(added_feat)
        reply = send_request(request, payload)
        self._post_send_request(reply, conn_info, kw_prop=kw_prop)

        #parallel case (merge output ? split input?)
        return reply
    def del_features(self, conn_info, removed_feat, **kw):
        # DELETE by Query URL, required list of feat_id

        query_del = {"id": ",".join(str(i) for i in removed_feat)}
        kw.update(query_del)

        endpoint = "/spaces/{space_id}/features"
        kw_request = dict(kw) # kw: query
        kw_prop = dict(reply_tag="del_feat")

        request = self._pre_send_request(conn_info,endpoint,kw_request=kw_request)
    
        reply = self.network.sendCustomRequest(request, b"DELETE")
        self._post_send_request(reply, conn_info, kw_prop=kw_prop)

        return reply
