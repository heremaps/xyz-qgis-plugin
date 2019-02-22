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

from .net_utils import make_conn_request, set_qt_property, prepare_new_space_info, make_payload

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
        return self._get_space_(conn_info, "statistics")
    def get_count(self, conn_info):
        reply = self._get_space_(conn_info, "count")
        # timeout = 1000
        # QTimer.singleShot(timeout, reply.abort)
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
        reply = self.network.sendCustomRequest(request, b"PATCH", make_payload(space_info))
        
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
        
    def load_features_bbox(self, conn_info, bbox, **kw):

        endpoint = "/spaces/{space_id}/bbox"
        kw_request = dict(bbox)
        kw_request.update(kw)
        kw_prop = dict(reply_tag="bbox")
        kw_prop.update(kw)
        kw_prop["bbox"] = bbox
        
        return self._send_request(conn_info, endpoint, kw_request=kw_request, kw_prop=kw_prop)

    def load_features_iterate(self, conn_info, **kw_iterate):
        reply_tag = kw_iterate.pop("reply_tag","iterate")
        endpoint = "/spaces/{space_id}/iterate"
        return self._load_features_endpoint(endpoint, conn_info, reply_tag=reply_tag, **kw_iterate)

    def load_features_search(self, conn_info, **kw_iterate):
        reply_tag = kw_iterate.pop("reply_tag","search")
        endpoint = "/spaces/{space_id}/search"
        return self._load_features_endpoint(endpoint, conn_info, reply_tag=reply_tag, **kw_iterate)
        
    def _load_features_endpoint(self, endpoint, conn_info, reply_tag=None, **kw_iterate):
        """ Iterate through all ordered features (no feature is repeated twice)
        """
        kw_request = dict(kw_iterate)
        kw_prop = dict(reply_tag=reply_tag)
        kw_prop.update(kw_iterate)
        
        return self._send_request(conn_info, endpoint, kw_request=kw_request, kw_prop=kw_prop)

    ###### feature function

    def add_features(self, conn_info, added_feat, layer_id=None, **kw):
        # POST, payload: list of FeatureCollection
        
        endpoint = "/spaces/{space_id}/features"
        kw_request = dict(req_type="geo", **kw) # kw: query
        kw_prop = dict(reply_tag="add_feat",layer_id=layer_id)
        kw_prop.update(kw)
        request = self._pre_send_request(conn_info,endpoint,kw_request=kw_request)
        
        buffer = make_payload(added_feat)
        reply = self.network.post(request, buffer)
        self._post_send_request(reply, conn_info, kw_prop=kw_prop)

        #parallel case (merge output ? split input?)
        return reply
    def del_features(self, conn_info, removed_feat, layer_id, **kw):
        # DELETE by Query URL, required list of feat_id

        query_del = {"id": ",".join(str(i) for i in removed_feat)}
        kw.update(query_del)

        endpoint = "/spaces/{space_id}/features"
        kw_request = dict(kw) # kw: query
        kw_prop = dict(reply_tag="del_feat",layer_id=layer_id)

        request = self._pre_send_request(conn_info,endpoint,kw_request=kw_request)
    
        reply = self.network.sendCustomRequest(request, b"DELETE")
        self._post_send_request(reply, conn_info, kw_prop=kw_prop)

        return reply
    def sync(self, conn_info, feat, layer_id, **kw):
        added_feat, removed_feat = feat
        token, space_id = conn_info.get_xyz_space()
        if not added_feat is None:
            self.add_features(conn_info, added_feat, layer_id)
        if len(removed_feat):
            self.del_features(conn_info, removed_feat, layer_id)
            
