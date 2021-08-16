# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2021 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import base64
import json
import time

from qgis.PyQt.QtCore import QUrl

from .login import PlatformUserAuthentication
from .net_handler import IMLNetworkHandler
from ...models import SpaceConnectionInfo
from ...network.network import NetManager, make_conn_request, make_payload
from ...network.net_utils import CookieUtils
from ...common.signal import make_print_qgis

print_qgis = make_print_qgis("iml.network")


class IMLNetworkManager(NetManager):
    TIMEOUT_COUNT = 2000

    API_PRD_URL = "https://interactive.data.api.platform.here.com/interactive/v1"
    API_SIT_URL = "https://interactive-dev-eu-west-1.api-gateway.sit.ls.hereapi.com/interactive/v1"
    API_CONFIG_PRD_URL = "https://config.data.api.platform.here.com/config/v1"
    API_CONFIG_SIT_URL = "https://config.data.api.platform.sit.here.com/config/v1"
    API_OAUTH_PRD_URL = "https://account.api.here.com/oauth2/token"
    API_OAUTH_SIT_URL = "https://stg.account.api.here.com/oauth2/token"
    API_AUTH_PRD_URL = "https://account.api.here.com/authorization/v1.1"
    API_AUTH_SIT_URL = "https://stg.account.api.here.com/authorization/v1.1"

    API_GROUP_INTERACTIVE = "interactive"
    API_GROUP_CONFIG = "config"
    API_GROUP_OAUTH = "oauth"
    API_GROUP_AUTH = "auth"

    API_SIT = "SIT"
    API_PRD = "PRD"

    API_URL = {
        API_GROUP_INTERACTIVE: {
            API_PRD: API_PRD_URL,
            API_SIT: API_SIT_URL,
        },
        API_GROUP_CONFIG: {
            API_PRD: API_CONFIG_PRD_URL,
            API_SIT: API_CONFIG_SIT_URL,
        },
        API_GROUP_OAUTH: {
            API_PRD: API_OAUTH_PRD_URL,
            API_SIT: API_OAUTH_SIT_URL,
        },
        API_GROUP_AUTH: {
            API_PRD: API_AUTH_PRD_URL,
            API_SIT: API_AUTH_SIT_URL,
        },
    }

    ENDPOINTS = {
        "space_meta": "/catalogs/{catalog_hrn}/layers/{layer_id}",
        "statistics": "/catalogs/{catalog_hrn}/layers/{layer_id}/statistics",
        "count": "/catalogs/{catalog_hrn}/layers/{layer_id}/count",
        "edit_space": "/catalogs/{catalog_hrn}/layers/{layer_id}",
        "del_space": "/catalogs/{catalog_hrn}/layers/{layer_id}",
        "list_spaces": "/catalogs",
        "add_space": "/catalogs/{catalog_hrn}/layers",
        "load_features_bbox": "/catalogs/{catalog_hrn}/layers/{layer_id}/bbox",
        "load_features_iterate": "/catalogs/{catalog_hrn}/layers/{layer_id}/iterate",
        "load_features_search": "/catalogs/{catalog_hrn}/layers/{layer_id}/search",
        "load_features_tile": "/catalogs/{catalog_hrn}/layers/{layer_id}/tile/{tile_schema}/{"
        "tile_id}",
        "add_features": "/catalogs/{catalog_hrn}/layers/{layer_id}/features",
        "del_features": "/catalogs/{catalog_hrn}/layers/{layer_id}/features",
        "get_project": "/resources/{catalog_hrn}/projects",
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
    }

    #############

    def print_cookies(self):
        return CookieUtils.print_cookies(self.network)

    #############
    def __init__(self, parent):
        super().__init__(parent)
        self.user_auth_module = PlatformUserAuthentication(self.network)

    def _get_api_env(self, conn_info: SpaceConnectionInfo):
        server: str = conn_info.get_("server")
        if conn_info.is_platform_server():
            return self.API_SIT if conn_info.is_platform_sit() else self.API_PRD
        else:
            raise Exception(
                "Unrecognized Platform Server: {}. "
                "Expecting place holder prefix 'PLATFORM_' ".format(server)
            )

    def _pre_send_request(self, conn_info, endpoint_key: str, kw_path=dict(), kw_request=dict()):
        token = conn_info.get_("token")
        catalog_hrn = conn_info.get_("catalog_hrn")
        layer_id = conn_info.get_("space_id")
        api_env = self._get_api_env(conn_info)

        api_group = self.API_GROUP.get(endpoint_key, self.API_GROUP_INTERACTIVE)
        api_url = self.API_URL[api_group][api_env]
        # api_url = conn_info.get_("server", api_url).rstrip("/")

        endpoint = self.ENDPOINTS[endpoint_key]
        url = api_url + endpoint.format(catalog_hrn=catalog_hrn, layer_id=layer_id, **kw_path)
        request = make_conn_request(url, token, **kw_request)
        return request

    #############

    def list_spaces(self, conn_info):
        endpoint_key = "list_spaces"
        kw_request = dict(verbose="true", layerType="interactivemap")
        kw_prop = dict(reply_tag="spaces", **kw_request)
        return self._send_request(conn_info, endpoint_key, kw_request=kw_request, kw_prop=kw_prop)

    def get_project(self, conn_info):
        endpoint_key = "get_project"
        kw_request = dict(relation="home")
        kw_prop = dict(reply_tag=endpoint_key)
        return self._send_request(conn_info, endpoint_key, kw_request=kw_request, kw_prop=kw_prop)

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

    def app_auth(self, conn_info, expires_in=7200, project_hrn: str = None):
        reply_tag = "oauth"

        api_env = self._get_api_env(conn_info)
        url = self.API_URL[self.API_GROUP_OAUTH][api_env]

        request = make_conn_request(url, token=None, req_type="json")
        payload = {
            "grantType": "client_credentials",
            "expiresIn": expires_in,
        }

        if project_hrn:
            payload.update({"scope": project_hrn})

        kw_prop = dict(reply_tag=reply_tag, auth_req_payload=payload)

        # generate_auth_headers
        # auth_header = auth.generateAuthorizationHeader(auth_headers)
        # auth_header = generate_oauth_header(url, conn_info)
        # print(auth_header)
        auth_header = generate_oauth_header_2(url, conn_info)
        # print("oauthlib", auth_header)
        request.setRawHeader(b"Authorization", auth_header)
        reply = self.network.post(request, make_payload(payload))

        # reply = auth.post(request.url(), payload)

        self._post_send_request(reply, conn_info, kw_prop=kw_prop)
        return reply

    #################
    # Network Handler
    #################

    def on_received(self, reply):
        return IMLNetworkHandler.on_received(reply)


def generate_oauth_header_2(url, conn_info):
    from oauthlib import oauth1

    client = oauth1.Client(
        conn_info.get_("here_client_key", ""),
        client_secret=conn_info.get_("here_client_secret", ""),
    )
    uri, headers, body = client.sign(url, "POST")
    return headers.get("Authorization", "").encode("utf-8")


def generate_oauth_header(url, conn_info):
    from PyQt5.QtNetworkAuth import QOAuth1, QOAuth1Signature

    auth_headers = dict(
        oauth_consumer_key=conn_info.get_("here_client_key", ""),
        oauth_nonce=bytes(QOAuth1.nonce()).decode("utf-8"),
        oauth_signature_method="HMAC-SHA1",
        oauth_timestamp=int(time.time()),
        oauth_version="1.0",
    )
    signature = QOAuth1Signature(
        QUrl(url),
        conn_info.get_("here_client_secret"),
        "",
        QOAuth1Signature.HttpRequestMethod.Post,
        auth_headers,
    )
    auth_headers["oauth_signature"] = bytes(
        QUrl.toPercentEncoding(bytes(signature.hmacSha1().toBase64()).decode("utf-8"))
    ).decode("utf-8")
    auth_header = "OAuth {}".format(
        ",".join('{}="{}"'.format(k, v) for k, v in auth_headers.items())
    ).encode("utf-8")
    return auth_header


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
