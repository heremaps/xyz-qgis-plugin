# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2023 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import json
import os

from PyQt5.QtQuick import QQuickView
from qgis.PyQt.QtCore import QUrl, QObject
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtNetwork import (
    QNetworkAccessManager,
)

from ...common.signal import BasicSignal
from ...common.utils import get_qml_full_path
from ...models import SpaceConnectionInfo
from ...network.net_utils import (
    PlatformSettings,
    make_payload,
    make_conn_request,
    set_qt_property,
)


class QmlError(Exception):
    pass


class PlatformAuthLoginView:
    API_SIT = "SIT"
    API_PRD = "PRD"

    def __init__(self):
        self.view = None

    # public

    def save_access_token(self, conn_info: SpaceConnectionInfo):
        if not self.view:
            return
        token_json = self.view.rootObject().getToken()
        if not token_json:
            return
        api_env = self.get_api_env(conn_info)
        PlatformSettings.save_token_json(
            token_json,
            api_env,
            conn_info.get_user_email(),
            conn_info.get_realm(),
        )
        return token_json

    def open_login_view(
        self, conn_info: SpaceConnectionInfo, parent=None, cb_login_view_closed=None
    ):
        # TODO: show qml dialog
        self.view = self.create_qml_view(
            title=self._dialog_title(conn_info),
            cb_login_view_closed=lambda *a: self.cb_login_view_closed(
                conn_info, cb_login_view_closed, *a
            ),
        )
        self.view.setModality(Qt.ApplicationModal)
        self.view.show()
        return self.view

    def cb_login_view_closed(self, conn_info: SpaceConnectionInfo, callback, *a):
        self._handle_error()
        self.save_access_token(conn_info)
        if callback:
            callback()

    def _handle_error(self):
        if not self.view:
            return
        error = self.view.rootObject().getError()
        if error:
            raise QmlError(error)

    # static

    @classmethod
    def get_access_token(self, conn_info: SpaceConnectionInfo) -> str:
        # TODO: get from settings
        api_env = self.get_api_env(conn_info)
        token_json = PlatformSettings.load_token_json(
            api_env,
            conn_info.get_user_email(),
            conn_info.get_realm(),
        )
        try:
            token_obj = json.loads(token_json) if token_json else dict()
        except json.JSONDecodeError:
            token_obj = dict()
        return token_obj.get("accessToken", "") if isinstance(token_obj, dict) else ""

    @classmethod
    def apply_token(cls, conn_info: SpaceConnectionInfo) -> str:
        token = cls.get_access_token(conn_info)
        conn_info.set_(token=token)
        return conn_info

    @classmethod
    def create_qml_view(cls, title="", cb_login_view_closed=None):
        view = QQuickView()
        view.setInitialProperties({"debugMode": os.environ.get("HERE_QML_DEBUG", "")})
        view.setSource(QUrl.fromLocalFile(get_qml_full_path("web.qml")))
        errors = [e.toString() for e in view.errors()]
        # print(errors)
        if len(errors):
            raise QmlError(errors)
        if cb_login_view_closed:
            view.closing.connect(cb_login_view_closed)
        if title:
            view.setTitle(title)
        # view.resize(600, 600)
        # view.setResizeMode(view.SizeRootObjectToView)
        return view

    # helper

    @classmethod
    def _dialog_title(cls, conn_info: SpaceConnectionInfo):
        api_env = cls.get_api_env(conn_info)
        title = "HERE Platform" if api_env == cls.API_PRD else "HERE Platform SIT"
        return title

    @classmethod
    def get_api_env(cls, conn_info: SpaceConnectionInfo):
        return cls.API_SIT if conn_info.is_platform_sit() else cls.API_PRD

    # other

    @classmethod
    def remove_access_token(cls, conn_info: SpaceConnectionInfo):
        api_env = cls.get_api_env(conn_info)
        email = conn_info.get_user_email()
        realm = conn_info.get_realm()
        PlatformSettings.remove_token_json(api_env, email, realm)
        conn_info.set_(token=None)
        return conn_info


class PlatformUserAuthentication:
    PLATFORM_URL_SIT = "https://platform.in.here.com"
    PLATFORM_URL_PRD = "https://platform.here.com"
    ENDPOINT_ACCESS_TOKEN = "/api/portal/accessToken"
    ENDPOINT_TOKEN_EXCHANGE = "/api/portal/authTokenExchange"
    ENDPOINT_SCOPED_TOKEN = "/api/portal/scopedTokenExchange"

    def __init__(self, network: QNetworkAccessManager):
        self.signal = BasicSignal()
        self.network = network

    # public

    def auth_project(self, conn_info: SpaceConnectionInfo):
        reply_tag = "oauth_project"

        project_hrn = conn_info.get_("project_hrn")
        platform_server = (
            self.PLATFORM_URL_SIT if conn_info.is_platform_sit() else self.PLATFORM_URL_PRD
        )
        url = "{platform_server}{endpoint}".format(
            platform_server=platform_server, endpoint=self.ENDPOINT_SCOPED_TOKEN
        )
        payload = {"scope": project_hrn}
        kw_prop = dict(reply_tag=reply_tag, req_payload=payload)

        token, _ = conn_info.get_xyz_space()
        reply = self.network.post(
            make_conn_request(url, token=token, req_type="json"), make_payload(payload)
        )
        set_qt_property(reply, conn_info=conn_info, **kw_prop)
        return reply

    def auth(self, conn_info: SpaceConnectionInfo):

        reply_tag = "oauth"
        kw_prop = dict(reply_tag=reply_tag)

        # parent = self.network
        parent = None
        PlatformAuthLoginView.apply_token(conn_info)
        return self.make_dummy_reply(parent, conn_info, **kw_prop)

    def reset_auth(self, conn_info: SpaceConnectionInfo):
        PlatformAuthLoginView.remove_access_token(conn_info)

    # private

    def make_dummy_reply(self, parent, conn_info: SpaceConnectionInfo, **kw_prop):
        qobj = QObject(parent)
        set_qt_property(qobj, conn_info=conn_info, **kw_prop)
        return qobj
