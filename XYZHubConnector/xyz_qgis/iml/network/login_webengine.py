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
import platform
from typing import Callable

try:
    from PyQt5.Qt import PYQT_VERSION_STR

    PYQT_STR = "PyQt5 (Qt {version})".format(version=PYQT_VERSION_STR)
    print(PYQT_STR)
except Exception as e:
    PYQT_STR = "PyQt (unknown){error}".format(error=" - " + repr(e))

from PyQt5.QtGui import QSurfaceFormat
from PyQt5.QtQuick import QQuickView


from qgis.PyQt.QtCore import QUrl, QObject
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtNetwork import (
    QNetworkAccessManager,
)


from .platform_server import PlatformServer, PlatformEndpoint
from ...common.crypter import decrypt_text
from ...common.signal import BasicSignal
from ...common.utils import get_qml_full_path, add_qml_import_path
from ...models import SpaceConnectionInfo
from ...network.net_utils import (
    PlatformSettings,
    make_payload,
    make_conn_request,
    set_qt_property,
)


class QmlError(Exception):
    def __init__(self, *a, **kw):
        super().__init__(PYQT_STR, *a, **kw)


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
        token2 = self.view.rootObject().getTokenAgain()
        token_json = token_json or token2
        if not token_json:
            return
        PlatformSettings.save_token_json(
            token_json,
            conn_info.get_server(),
            conn_info.get_user_email(),
            conn_info.get_realm(),
        )
        return token_json

    def open_login_view(
        self, conn_info: SpaceConnectionInfo, parent=None, cb_login_view_closed=None
    ):
        login_url = PlatformLoginServer.get_login_url(conn_info.get_server())
        self.view = self.create_qml_view(
            login_url=login_url,
            title=self._dialog_title(conn_info),
            cb_login_view_closed=lambda *a: self.cb_login_view_closed(
                conn_info, cb_login_view_closed, *a
            ),
        )
        self.view.setModality(Qt.ApplicationModal)
        self.view.show()
        return self.view

    def cb_login_view_closed(self, conn_info: SpaceConnectionInfo, callback, *a):
        self.save_access_token(conn_info)
        self._handle_error()
        if callback:
            callback()

    def _handle_error(self):
        if not self.view:
            return
        lst_err = []
        error = self.view.rootObject().getError()
        if error:
            lst_err.append(error)
        errors = [e.toString() for e in self.view.errors()]
        if len(errors):
            lst_err.append(errors)
        if lst_err:
            raise QmlError(lst_err)

    # static

    @classmethod
    def get_access_token(self, conn_info: SpaceConnectionInfo) -> str:
        token_json = PlatformSettings.load_token_json(
            conn_info.get_server(),
            conn_info.get_user_email(),
            conn_info.get_realm(),
        )
        try:
            token_obj = json.loads(token_json) if token_json else dict()
        except json.JSONDecodeError:
            token_obj = dict()
        return token_obj.get("accessToken", "") if isinstance(token_obj, dict) else ""

    @classmethod
    def create_qml_view(cls, login_url: str, title="", cb_login_view_closed=None):
        os.environ["QML_USE_GLYPHCACHE_WORKAROUND"] = "1"

        if not (platform.system() == "Darwin" or os.name == "mac"):
            QSurfaceFormat.setDefaultFormat(QSurfaceFormat())  # fix fot windows rdp, break mac

        view = QQuickView()
        engine = view.engine()

        # engine.setImportPathList([])  # test init qml engine

        add_qml_import_path(engine)

        # QTWEBENGINE_REMOTE_DEBUGGING: port
        debugMode = os.environ.get("HERE_QML_DEBUG", "")
        view_props = {"loginUrl": login_url}
        if debugMode:
            title = title + " debug"
            view.setInitialProperties(dict(view_props, debugMode=debugMode))
            view.setSource(QUrl.fromLocalFile(get_qml_full_path("web_debug.qml")))
        else:
            view.setInitialProperties(dict(view_props))
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
        title = "HERE Platform" if not conn_info.is_platform_sit() else "HERE Platform SIT"
        return title

    # other

    @classmethod
    def remove_access_token(cls, conn_info: SpaceConnectionInfo):
        PlatformSettings.remove_token_json(
            conn_info.get_server(),
            conn_info.get_user_email(),
            conn_info.get_realm(),
        )
        conn_info.set_(token=None)
        return conn_info


class PlatformLoginServer:
    PLATFORM_URL_PRD = PlatformServer.PLATFORM_URL_PRD
    PLATFORM_SERVERS = {
        SpaceConnectionInfo.PLATFORM_PRD: PLATFORM_URL_PRD,
        SpaceConnectionInfo.PLATFORM_SIT: decrypt_text(PlatformServer.PLATFORM_URL_SIT),
        SpaceConnectionInfo.PLATFORM_KOREA: PLATFORM_URL_PRD,
        SpaceConnectionInfo.PLATFORM_CHINA: decrypt_text(PlatformServer.PLATFORM_URL_CHINA),
    }

    ENDPOINT_SCOPED_TOKEN = decrypt_text(PlatformEndpoint.ENDPOINT_SCOPED_TOKEN)

    @classmethod
    def get_login_url(cls, server):
        return cls.PLATFORM_SERVERS.get(server, cls.PLATFORM_URL_PRD)


class PlatformUserAuthentication:
    def __init__(self, network: QNetworkAccessManager):
        self.signal = BasicSignal()
        self.network = network
        self.platform_auth_view = PlatformAuthLoginView()

    # public

    def auth_project(self, conn_info: SpaceConnectionInfo):
        reply_tag = "oauth_project"

        project_hrn = conn_info.get_("project_hrn")
        platform_server = PlatformLoginServer.get_login_url(conn_info.get_server())
        url = "{platform_server}{endpoint}".format(
            platform_server=platform_server, endpoint=PlatformLoginServer.ENDPOINT_SCOPED_TOKEN
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
        self.apply_token(conn_info)
        return self.make_dummy_reply(parent, conn_info, **kw_prop)

    def reset_auth(self, conn_info: SpaceConnectionInfo):
        PlatformAuthLoginView.remove_access_token(conn_info)

    # private

    def make_dummy_reply(self, parent, conn_info: SpaceConnectionInfo, **kw_prop):
        qobj = QObject(parent)
        set_qt_property(qobj, conn_info=conn_info, **kw_prop)
        return qobj

    # dialog, token

    def open_login_dialog(
        self, conn_info: SpaceConnectionInfo, parent=None, cb_login_view_closed: Callable = None
    ):
        return self.platform_auth_view.open_login_view(conn_info, parent, cb_login_view_closed)

    def apply_token(self, conn_info: SpaceConnectionInfo) -> SpaceConnectionInfo:
        token = self.platform_auth_view.get_access_token(conn_info)
        conn_info.set_(token=token)
        return conn_info
