# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2021 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

# from PyQt5.QtWebEngineWidgets import QWebEngineView # import error
import json
from typing import Optional

from qgis.PyQt.QtCore import QUrl, QObject
from qgis.PyQt.QtNetwork import QNetworkAccessManager
from qgis.PyQt.QtWebKit import QWebSettings
from qgis.PyQt.QtWebKitWidgets import QWebPage, QWebView, QWebInspector
from qgis.PyQt.QtWidgets import QDialog, QGridLayout
from qgis.PyQt.QtCore import Qt

from .net_handler import IMLNetworkHandler
from ...common.signal import BasicSignal
from ...models import API_TYPES, SpaceConnectionInfo
from ...network.net_handler import NetworkError
from ...network.net_utils import (
    CookieUtils,
    make_payload,
    make_conn_request,
    set_qt_property,
)


class WebPage(QWebPage):
    def __init__(self, parent, *a, **kw):
        super().__init__(*a, **kw)
        self.parent_widget = parent

        settings = self.settings()
        settings.setAttribute(QWebSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebSettings.LocalStorageEnabled, True)
        settings.setAttribute(QWebSettings.JavascriptCanOpenWindows, True)
        settings.setAttribute(QWebSettings.JavascriptCanCloseWindows, True)
        # settings.setAttribute(QWebSettings.PrivateBrowsingEnabled, True)
        settings.setAttribute(QWebSettings.DeveloperExtrasEnabled, True)
        settings.setAttribute(QWebSettings.WebGLEnabled, True)
        settings.setAttribute(QWebSettings.PluginsEnabled, True)
        settings.setThirdPartyCookiePolicy(settings.AlwaysAllowThirdPartyCookies)

    def createWindow(self, window_type):
        # WindowDialog is just a simple QDialog with a QWebView

        parent = self.parent_widget
        dialog = QDialog(parent)
        page = self.new_page(dialog, self.networkAccessManager())
        dialog.show()

        return page

    @classmethod
    def new_page(cls, dialog: QDialog, network: QNetworkAccessManager):
        parent = dialog
        dialog.setAttribute(Qt.WA_DeleteOnClose, True)
        dialog.raise_()
        # dialog.setWindowModality(Qt.WindowModal)

        page = WebPage(parent)
        page.setNetworkAccessManager(network)

        view = QWebView(parent)
        view.setPage(page)

        mainLayout = QGridLayout(parent)
        mainLayout.addWidget(view, 0, 0)

        dialog.resize(600, 600)
        dialog.setLayout(mainLayout)

        # cls.attach_inspector(dialog, page)
        return page

    @classmethod
    def attach_inspector(cls, dialog: QDialog, page: "WebPage"):
        parent = page.parent_widget
        inspector = QWebInspector(parent)
        inspector.setPage(page)
        inspector.setMinimumHeight(400)
        dialog.layout().addWidget(inspector, 1, 0)
        dialog.resize(800, 600)


class PlatformUserAuthentication:
    API_SIT = "SIT"
    API_PRD = "PRD"
    PLATFORM_URL_SIT = "platform.in.here.com"
    PLATFORM_URL_PRD = "platform.here.com"
    HERE_URL_SIT = "st.p.account.here.com"
    PLATFORM_LOGIN_URL_SIT = (
        "https://st.p.account.here.com/sign-in?version=4&oidc=true"
        "&client-id=TlZSbQzENfNkUFrOXh8Oag&no-sign-up=true"
        "&realm-input=true&sign-in-template=olp&self-certify-age=true"
        "&theme=brand&authorizeUri=%2Fauthorize%3Fresponse_type%3Dcode"
        "%26client_id%3DTlZSbQzENfNkUFrOXh8Oag%26scope%3Dopenid%2520email"
        "%2520phone%2520profile%2520readwrite%253Aha%26redirect_uri"
        "%3Dhttps%253A%252F%252Fplatform.in.here.com%252FauthHandler"
        "%26state%3D%257B%2522redirectUri%2522%253A%2522https"
        "%253A%252F%252Fplatform.in.here.com%252FauthHandler"
        "%2522%252C%2522redirect%2522%253A%2522https%25253A%25252F"
        "%25252Fplatform.in.here.com%25252F%2522%257D%26nonce"
        "%3D1628073689817%26prompt%3D&sign-in-screen-config=password"
    )
    PLATFORM_LOGIN_URL_PRD = (
        "https://account.here.com/sign-in?version=4&oidc=true"
        "&client-id=YQijV3hAPdxySAVtE6ZT&no-sign-up=true"
        "&realm-input=true&sign-in-template=olp&self-certify-age=true"
        "&theme=brand&authorizeUri=%2Fauthorize%3Fresponse_type%3Dcode"
        "%26client_id%3DYQijV3hAPdxySAVtE6ZT%26scope%3Dopenid%2520email"
        "%2520phone%2520profile%2520readwrite%253Aha%26redirect_uri"
        "%3Dhttps%253A%252F%252Fplatform.here.com%252FauthHandler"
        "%26state%3D%257B%2522redirectUri%2522%253A%2522https"
        "%253A%252F%252Fplatform.here.com%252FauthHandler"
        "%2522%252C%2522redirect%2522%253A%2522https%25253A%25252F"
        "%25252Fplatform.here.com%25252F%2522%257D%26nonce"
        "%3D1628073704030%26prompt%3D&sign-in-screen-config=password"
    )
    ENDPOINT_ACCESS_TOKEN = "/api/portal/accessToken"
    ENDPOINT_TOKEN_EXCHANGE = "/api/portal/authTokenExchange"
    ENDPOINT_SCOPED_TOKEN = "/api/portal/scopedTokenExchange"

    def __init__(self, network: QNetworkAccessManager):
        self.signal = BasicSignal()
        self.network = network
        self.dialog: QDialog = None
        self.page: WebPage = None

    # public

    def auth_project(self, conn_info):
        reply_tag = "oauth"

        project_hrn = conn_info.get_("project_hrn")
        platform_server = (
            self.PLATFORM_URL_SIT if conn_info.is_platform_sit() else self.PLATFORM_URL_PRD
        )
        url = "https://{platform_server}{endpoint}".format(
            platform_server=platform_server, endpoint=self.ENDPOINT_SCOPED_TOKEN
        )
        payload = {"scope": project_hrn}
        kw_prop = dict(reply_tag=reply_tag, req_payload=payload)

        # token = self.get_access_token()
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
        api_env = self.API_SIT if conn_info.is_platform_sit() else self.API_PRD
        CookieUtils.load_from_settings(self.network, API_TYPES.PLATFORM, api_env)
        token = self.get_access_token()
        if token:
            conn_info.set_(token=token)
        else:
            email = conn_info.get_("user_login")
            dialog = self.open_login_dialog(api_env, email=email)
            dialog.exec_()
            token = self.get_access_token()
            if token:
                conn_info.set_(token=token)
            else:
                self.reset_auth(conn_info)
        return self.make_dummy_reply(parent, conn_info, **kw_prop)

    def reset_auth(self, conn_info):
        api_env = self.API_SIT if conn_info.is_platform_sit() else self.API_PRD
        self._reset_auth(api_env)
        conn_info.set_(token=None)

    def _reset_auth(self, api_env):
        CookieUtils.remove_cookies_from_settings(API_TYPES.PLATFORM, api_env)

    # private

    def make_dummy_reply(self, parent, conn_info, **kw_prop):
        qobj = QObject(parent)
        set_qt_property(qobj, conn_info=conn_info, **kw_prop)
        return qobj

    def cb_dialog_closed(self, api_env: str, *a):
        self.dialog = None
        if self.get_access_token():
            CookieUtils.save_to_settings(self.network, API_TYPES.PLATFORM, api_env)

    def cb_url_changed(self, url: QUrl):
        if "/authHandler" in url.toString():
            self.auth_handler(url)
        elif "/sdk-callback-page" in url.toString():
            # "action=already signed in" in url.toString()
            self.dialog.close()
            api_env = self.API_SIT if url.host() == self.HERE_URL_SIT else self.API_PRD
            self._reset_auth(api_env)

    def cb_auth_handler(self, reply):
        try:
            IMLNetworkHandler.on_received(reply)
        except NetworkError as e:
            self.signal.error.emit(e)
        self.dialog.close()

    def get_access_token(self) -> Optional[str]:
        cookie = CookieUtils.get_cookie(self.network, "olp_portal_access")
        if not cookie:
            return
        val = QUrl.fromPercentEncoding(cookie.value())
        obj = json.loads(val)
        return obj.get("accessToken")

    def auth_handler(self, url: QUrl):
        """
        Handle auth handler url to get cookies with access token
        :param url:
        :return:

        Example:
        QUrl('https://platform.here.com/authHandler?code=bfO-Yz6l3ZDPK0VIyC4tPkBH9K05-d8JQHP869q8MmA&state=%7B%22redirectUri%22%3A%22https%3A%2F%2Fplatform.here.com%2FauthHandler%22%2C%22redirect%22%3A%22https%253A%252F%252Fplatform.here.com%252F%22%7D'))
        """
        query_kv = dict(s.split("=", 1) for s in url.query().split("&"))
        for k, v in query_kv.items():
            query_kv[k] = url.fromPercentEncoding(v.encode("utf-8"))
        platform_server = url.host()
        url = "https://{platform_server}{endpoint}".format(
            platform_server=platform_server, endpoint=self.ENDPOINT_TOKEN_EXCHANGE
        )
        reply = self.network.post(
            make_conn_request(url, token=None, req_type="json"),
            make_payload(query_kv),
        )
        reply.finished.connect(lambda: self.cb_auth_handler(reply))
        # reply.waitForReadyRead(1000)
        # self.cb_auth_handler(reply)

    def open_login_dialog(self, api_env: str, email: str = None, parent=None):
        if not self.dialog:
            dialog = QDialog(parent)
            page = WebPage.new_page(dialog, self.network)
            self.page = page
            self.dialog = dialog

            view = page.view()

            # url = "https://platform.here.com/"
            url = (
                self.PLATFORM_LOGIN_URL_PRD
                if api_env == self.API_PRD
                else self.PLATFORM_LOGIN_URL_SIT
            )
            if email:
                url = "&".join([url, "prefill-email-addr={email}".format(email=email)])

            page.currentFrame().urlChanged.connect(self.cb_url_changed)
            dialog.finished.connect(lambda *a: self.cb_dialog_closed(api_env, *a))

            dialog.open()
            view.load(QUrl(url))
        else:
            dialog = self.dialog
            dialog.show()
        return dialog