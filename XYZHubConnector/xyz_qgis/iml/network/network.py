# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2021 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import time
import base64
import json
from typing import Dict

from .login_webengine import PlatformUserAuthentication
from .net_handler import IMLNetworkHandler
from .platform_server import PlatformServer
from ...common.crypter import decrypt_text
from ...models import SpaceConnectionInfo
from ...network.network import NetManager
from ...network.net_utils import (
    CookieUtils,
    make_conn_request,
    make_payload,
    make_bytes_payload,
    PlatformSettings,
)
from ...common.signal import make_print_qgis

print_qgis = make_print_qgis("iml.network")


class IMLNetworkManager(NetManager):
    TIMEOUT_COUNT = 10000

    API_GROUP_INTERACTIVE = "interactive"
    API_GROUP_CONFIG = "config"
    API_GROUP_AUTH = "auth"
    API_GROUP_OAUTH = "oauth"

    API_SIT = "SIT"
    API_PRD = "PRD"
    API_KOREA = "KOREA"
    API_CHINA = "CHINA"

    API_URL = {
        API_GROUP_INTERACTIVE: {
            API_PRD: PlatformServer.API_PRD_URL,
            API_SIT: decrypt_text(PlatformServer.API_SIT_URL),
            API_KOREA: decrypt_text(PlatformServer.API_KOREA_URL),
            API_CHINA: decrypt_text(PlatformServer.API_CHINA_URL),
        },
        API_GROUP_CONFIG: {
            API_PRD: PlatformServer.API_CONFIG_PRD_URL,
            API_SIT: decrypt_text(PlatformServer.API_CONFIG_SIT_URL),
            API_CHINA: decrypt_text(PlatformServer.API_CONFIG_CHINA_URL),
        },
        API_GROUP_AUTH: {
            API_PRD: PlatformServer.API_AUTH_PRD_URL,
            API_SIT: decrypt_text(PlatformServer.API_AUTH_SIT_URL),
            API_CHINA: decrypt_text(PlatformServer.API_AUTH_CHINA_URL),
        },
        API_GROUP_OAUTH: {
            API_PRD: PlatformServer.API_OAUTH_PRD_URL,
            API_SIT: decrypt_text(PlatformServer.API_OAUTH_SIT_URL),
            API_CHINA: decrypt_text(PlatformServer.API_OAUTH_CHINA_URL),
        },
    }

    ENDPOINTS = {
        "space_meta": "/catalogs/{catalog_hrn}/layers/{layer_id}",
        "statistics": "/catalogs/{catalog_hrn}/layers/{layer_id}/statistics",
        "count": "/catalogs/{catalog_hrn}/layers/{layer_id}/count",
        "edit_space": "/catalogs/{catalog_hrn}/layers/{layer_id}",
        "del_space": "/catalogs/{catalog_hrn}/layers/{layer_id}",
        "list_spaces": "/catalogs",
        "add_space": "/catalogs/{catalog_hrn}",
        "load_features_bbox": "/catalogs/{catalog_hrn}/layers/{layer_id}/bbox",
        "load_features_iterate": "/catalogs/{catalog_hrn}/layers/{layer_id}/iterate",
        "load_features_search": "/catalogs/{catalog_hrn}/layers/{layer_id}/search",
        "load_features_tile": "/catalogs/{catalog_hrn}/layers/{layer_id}/tile/{tile_schema}/{"
        "tile_id}",
        "add_features": "/catalogs/{catalog_hrn}/layers/{layer_id}/features",
        "del_features": "/catalogs/{catalog_hrn}/layers/{layer_id}/features",
        "get_project": "/resources/{catalog_hrn}/projects",
        "create_project": "/projects",
        "create_catalog": "/catalogs",
        "update_catalog": "/catalogs/{catalog_hrn}",
        "get_catalog": "/catalogs/{catalog_hrn}",
        "add_layer": "/catalogs/{catalog_hrn}",
        "edit_layer": "/catalogs/{catalog_hrn}/layers/{layer_id}",
        "del_layer": "/catalogs/{catalog_hrn}/layers/{layer_id}",
    }

    API_GROUP = {
        "space_meta": API_GROUP_CONFIG,
        "statistics": API_GROUP_INTERACTIVE,
        "count": API_GROUP_INTERACTIVE,
        "edit_space": API_GROUP_CONFIG,
        "del_space": API_GROUP_CONFIG,
        "list_spaces": API_GROUP_CONFIG,
        "add_space": API_GROUP_CONFIG,
        "load_features_bbox": API_GROUP_INTERACTIVE,
        "load_features_iterate": API_GROUP_INTERACTIVE,
        "load_features_search": API_GROUP_INTERACTIVE,
        "load_features_tile": API_GROUP_INTERACTIVE,
        "add_features": API_GROUP_INTERACTIVE,
        "del_features": API_GROUP_INTERACTIVE,
        "get_project": API_GROUP_AUTH,
        "create_project": API_GROUP_AUTH,
        "create_catalog": API_GROUP_CONFIG,
        "update_catalog": API_GROUP_CONFIG,
        "get_catalog": API_GROUP_CONFIG,
        "add_layer": API_GROUP_CONFIG,
        "edit_layer": API_GROUP_CONFIG,
        "del_layer": API_GROUP_CONFIG,
    }

    API_PAYLOAD_ALLOW_KEYS = {
        "create_catalog": [
            "id",
            "name",
            "summary",
            "description",
            "tags",
            "layers",
            "version",
            "notifications",
            "replication",
            "automaticVersionDeletion",
        ],
        "edit_layer": [
            "layerType",
            "id",
            "name",
            "summary",
            "description",
            "coverage",
            "schema",
            "partitioning",
            "indexProperties",
            "streamProperties",
            "interactiveMapsProperties",
            "interactiveMapProperties",
            "tags",
            "billingTags",
            "crc",
            "digest",
            "ttl",
            "contentType",
            "contentEncoding",
        ],
    }

    API_PAYLOAD_ALLOW_KEYS.update(
        {
            "update_catalog": API_PAYLOAD_ALLOW_KEYS["create_catalog"],
            "add_layer": API_PAYLOAD_ALLOW_KEYS["create_catalog"],
        }
    )

    #############

    def print_cookies(self):
        return CookieUtils.print_cookies(self.network)

    #############
    def __init__(self, parent):
        super().__init__(parent)
        self.user_auth_module = PlatformUserAuthentication(self.network)
        self._connected_conn_info: Dict[str, SpaceConnectionInfo] = dict()
        self.load_all_connected_conn_info_from_settings()

    def _get_api_url(self, server: str, api_group):
        api_env = server.replace("PLATFORM_", "").upper()
        urls = self.API_URL[api_group]
        return urls.get(api_env, urls[self.API_PRD])

    def _pre_send_request(
        self, conn_info: SpaceConnectionInfo, endpoint_key: str, kw_path=dict(), kw_request=dict()
    ):
        token = conn_info.get_("token")
        catalog_hrn = conn_info.get_("catalog_hrn")
        layer_id = conn_info.get_id()
        server = conn_info.get_server()

        api_group = self.API_GROUP.get(endpoint_key, self.API_GROUP_INTERACTIVE)
        api_url = self._get_api_url(server, api_group)
        # api_url = conn_info.get_("server", api_url).rstrip("/")

        endpoint = self.ENDPOINTS[endpoint_key]
        url = api_url + endpoint.format(catalog_hrn=catalog_hrn, layer_id=layer_id, **kw_path)
        request = make_conn_request(url, token, **kw_request)
        return request

    @classmethod
    def trim_payload(cls, payload, endpoint_key):
        keys = cls.API_PAYLOAD_ALLOW_KEYS.get(endpoint_key, [])
        return {k: payload[k] for k in keys if k in payload}

    #############

    def list_spaces(self, conn_info):
        endpoint_key = "list_spaces"
        kw_request = dict(verbose="true", layerType="interactivemap")
        kw_prop = dict(reply_tag="spaces", **kw_request)
        return self._send_request(conn_info, endpoint_key, kw_request=kw_request, kw_prop=kw_prop)

    def get_project(self, conn_info):
        endpoint_key = "get_project"
        kw_request = dict()  # dict(relation="home")
        kw_prop = dict(reply_tag=endpoint_key)
        return self._send_request(conn_info, endpoint_key, kw_request=kw_request, kw_prop=kw_prop)

    def get_catalog(self, conn_info):
        endpoint_key = "get_catalog"
        kw_request = dict()
        kw_prop = dict(reply_tag=endpoint_key)
        return self._send_request(conn_info, endpoint_key, kw_request=kw_request, kw_prop=kw_prop)

    def add_layer(self, conn_info, space_info: dict, catalog_info: dict = None):
        endpoint_key = "add_layer"

        catalog_hrn = conn_info.get_("catalog_hrn")
        payload = self.trim_payload(catalog_info or dict(), endpoint_key)
        payload.setdefault("layers", list()).append(space_info)

        kw_request = dict(req_type="json", catalog_hrn=catalog_hrn)
        kw_prop = dict(reply_tag=endpoint_key)
        request = self._pre_send_request(conn_info, endpoint_key, kw_request=kw_request)
        reply = self.network.sendCustomRequest(request, b"PUT", make_bytes_payload(payload))
        self._post_send_request(reply, conn_info, kw_prop=kw_prop)
        return reply

    def edit_layer(self, conn_info, space_info: dict):
        endpoint_key = "edit_layer"

        catalog_hrn = conn_info.get_("catalog_hrn")
        layer_id = conn_info.get_id()
        payload = self.trim_payload(space_info, endpoint_key)

        kw_request = dict(req_type="json", catalog_hrn=catalog_hrn, layer_id=layer_id)
        kw_prop = dict(reply_tag=endpoint_key)
        request = self._pre_send_request(conn_info, endpoint_key, kw_request=kw_request)
        reply = self.network.sendCustomRequest(request, b"PATCH", make_bytes_payload(payload))
        self._post_send_request(reply, conn_info, kw_prop=kw_prop)
        print_qgis(request.url())
        return reply

    def del_layer(self, conn_info):
        endpoint_key = "del_layer"
        kw_request = dict()
        kw_prop = dict(reply_tag=endpoint_key)
        request = self._pre_send_request(conn_info, endpoint_key, kw_request=kw_request)
        reply = self.network.sendCustomRequest(request, b"DELETE")
        self._post_send_request(reply, conn_info, kw_prop=kw_prop)
        return reply

    ####################
    # Authentication Public
    ####################

    def auth_project(self, conn_info, expires_in=7200):
        if conn_info.is_user_login():
            return self.user_auth_module.auth_project(conn_info)
        else:
            return self.app_auth_project(conn_info, expires_in=expires_in)

    def auth(self, conn_info, expires_in=7200, project_hrn: str = None):
        if conn_info.is_user_login():
            return self.user_auth_module.auth(conn_info)
        else:
            return self.app_auth(conn_info, expires_in=expires_in, project_hrn=project_hrn)

    ####################
    # App Authentication
    ####################

    def app_auth_project(self, conn_info, expires_in=7200):
        project_hrn = conn_info.get_("project_hrn")
        return self.app_auth(conn_info, expires_in=expires_in, project_hrn=project_hrn)

    def app_auth(self, conn_info: SpaceConnectionInfo, expires_in=7200, project_hrn: str = None):
        reply_tag = "oauth"

        conn_info.load_here_credentials()
        server = conn_info.get_server()

        url = self._get_api_url(server, self.API_GROUP_OAUTH)

        request = make_conn_request(url, token=None, req_type="json")
        payload = {
            "grantType": "client_credentials",
            "expiresIn": expires_in,
        }

        if project_hrn:
            payload.update({"scope": project_hrn})
            reply_tag = "oauth_project"

        kw_prop = dict(reply_tag=reply_tag, auth_req_payload=payload)

        auth_header = generate_oauth_header(url, conn_info)
        request.setRawHeader(b"Authorization", auth_header)
        reply = self.network.post(request, make_payload(payload))

        self._post_send_request(reply, conn_info, kw_prop=kw_prop)
        return reply

    #################
    # Network Handler
    #################

    def on_received(self, reply):
        return IMLNetworkHandler.on_received(reply)

    #################
    # Select Auth
    #################

    def apply_connected_conn_info(self, conn_info: SpaceConnectionInfo):
        if not conn_info.is_protected():
            connected = self.get_connected_conn_info(conn_info.get_server())
            if (
                connected
                and connected.is_valid()
                and connected.get_platform_auth() != conn_info.get_platform_auth()
            ):
                # print("auth", conn_info.get_platform_auth(), connected.get_platform_auth())
                conn_info.set_(token="", **connected.get_platform_auth())
        return conn_info

    def open_login_view(self, conn_info: SpaceConnectionInfo, callback=None):
        conn_info = self.user_auth_module.apply_token(conn_info)
        if not conn_info.has_token():
            try:
                self.user_auth_module.open_login_dialog(conn_info, cb_login_view_closed=callback)
            except Exception as e:
                if callback:
                    callback()
                raise e
        else:
            if callback:
                callback()

    def set_connected_conn_info(self, conn_info: SpaceConnectionInfo, *a):
        self._connected_conn_info[conn_info.get_server()] = conn_info
        # PlatformSettings.save_default_token_from_conn_info(conn_info)
        PlatformSettings.save_connected_conn_info(conn_info)

    def clear_auth(self, conn_info: SpaceConnectionInfo):
        connected = self.get_connected_conn_info(conn_info.get_server())
        if connected and connected.is_valid() and connected.get_server() == conn_info.get_server():
            self._connected_conn_info.pop(conn_info.get_server(), None)
            PlatformSettings.remove_connected_conn_info(conn_info.get_server())
        if conn_info.is_user_login():
            self.user_auth_module.reset_auth(conn_info)
        conn_info.unmark_protected()

    def get_connected_conn_info(self, server):
        return self._connected_conn_info.get(server)

    def get_all_connected_conn_info(self):
        return self._connected_conn_info

    def load_all_connected_conn_info_from_settings(self):
        self._connected_conn_info = PlatformSettings.load_all_connected_conn_info()


def generate_oauth_header(url, conn_info):
    from oauthlib import oauth1

    client = oauth1.Client(
        conn_info.get_("here_client_key", ""),
        client_secret=conn_info.get_("here_client_secret", ""),
    )
    uri, headers, body = client.sign(url, "POST")
    return headers.get("Authorization", "").encode("utf-8")


def check_oauth2_token(token):
    parts = token.split(".")  # header, payload, signature
    header = parts[0]
    # b64 decode header
    header_str = base64.b64decode(header)
    header_obj = json.loads(header_str)
    if "exp" not in header_obj:
        raise Exception("Invalid oauth2 token")

    is_expired = int(time.time()) >= int(header_obj["exp"])
    return is_expired
