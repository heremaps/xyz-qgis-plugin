# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


# UTILS

import gzip
import json
from typing import List

from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import (
    QNetworkRequest,
    QNetworkAccessManager,
    QNetworkCookie,
    QNetworkCookieJar,
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtCore import QByteArray, QSettings
from qgis.PyQt.QtCore import QT_VERSION_STR
from qgis.PyQt.Qt import PYQT_VERSION_STR
from qgis.core import Qgis
import platform
from ..common import config
from ..models import API_TYPES

USER_AGENT = (
    "xyz-qgis-plugin/{plugin_version} QGIS/{qgis_version} Python/"
    "{py_version} Qt/{qt_version}".format(
        plugin_version=config.PLUGIN_VERSION,
        qgis_version=Qgis.QGIS_VERSION,
        py_version=platform.python_version(),
        qt_version=QT_VERSION_STR,
    )
)

from ..common.signal import make_print_qgis

print_qgis = make_print_qgis("net_utils")


def check_gzip(byt):
    return byt[:2] == b"\037\213"  # get from gzip.py


def decode_byte(byt):
    byt = bytes(byt)
    if check_gzip(byt):
        byt = gzip.decompress(byt)
    txt = byt.decode("utf-8")
    try:
        obj = json.loads(txt) if len(txt) else dict()
    except json.JSONDecodeError:
        obj = dict()

    return byt, txt, obj


def _make_headers(token, **params):
    h = {"Accept": "*/*", "Accept-Encoding": "gzip", "User-Agent": USER_AGENT}
    if isinstance(token, str) and token.strip():
        h.update(
            {
                "Authorization": "Bearer %s" % token,
            }
        )
    h.update(params)
    return h


def make_request(url, token, **header):
    request = QNetworkRequest(url)
    for k, v in _make_headers(token, **header).items():
        k = k.encode("utf-8")
        v = v.encode("utf-8")
        request.setRawHeader(k, v)
    return request


def make_gzip_request(url, token):
    header = {"Accept-Encoding": "gzip"}
    return make_request(url, token, **header)


def make_geo_request(url, token):
    header = {"Content-Type": "application/geo+json"}
    return make_request(url, token, **header)


def make_json_request(url, token):
    header = {"Content-Type": "application/json"}
    return make_request(url, token, **header)


def make_payload(obj):
    txt = json.dumps(obj, ensure_ascii=False)
    return txt.encode("utf-8")


def make_bytes_payload(obj):
    return QByteArray(make_payload(obj))


def make_query_url(url, **kw):
    raw_queries = list(kw.pop("raw_queries", list()))
    query = "&".join(raw_queries + ["%s=%s" % (k, v) for k, v in kw.items() if v is not None])
    if len(query):
        url = "%s?%s" % (url, query)
    url = QUrl(url)
    return url


HEADER_EXTRA_MAP = dict(
    normal={},
    geo={"Content-Type": "application/geo+json"},
    json={"Content-Type": "application/json"},
    gzip={"Accept-Encoding": "gzip"},
)


def make_conn_request(url: str, token: str, req_type="normal", **kw):
    """Make request from conn_info (token,space_id,api_url, auth,etc.)
    :param: req_type: type of request:
        "normal": normal
        "gzip"
        "geo"
        "json"

    """
    url = make_query_url(url, **kw)
    header = HEADER_EXTRA_MAP.get(req_type, dict())
    return make_request(url, token, **header)


# data flow in reply (QNetworkReply)


def set_qt_property(qobj, **kw):
    for k, v in kw.items():
        qobj.setProperty(str(k), QVariant(v))


def get_qt_property(qobj, keys):
    return [qobj.property(k) for k in keys]


#

META_SIGNATURE = "\n\n#XYZ+QGIS"


def prepare_new_space_info(space_info):
    """space_info = meta
    add qgis-xyz plugin signature
    remove fields for updating meta
    """
    space_info = dict(space_info)
    space_info.pop("owner", 0)
    space_info.pop("id", 0)
    space_info.pop("space_id", 0)
    # insertBBox false is not accepted by xyz
    if not space_info.get("insertBBox") is True:
        space_info.pop("insertBBox", 0)
    space_info["description"] += META_SIGNATURE
    return space_info


class CookieUtils:
    @classmethod
    def get_cookie_jar(cls, network: QNetworkAccessManager):
        return network.cookieJar()

    @classmethod
    def print_cookies(cls, network: QNetworkAccessManager):
        print([bytes(c.toRawForm()).decode("utf-8") for c in network.cookieJar().allCookies()])

    @classmethod
    def save_to_settings(
        cls,
        network: QNetworkAccessManager,
        api_type: str,
        api_env: str,
        user_email: str,
        realm: str,
    ):
        return cls.save_cookies_to_settings(
            network.cookieJar().allCookies(), api_type, api_env, user_email, realm
        )

    @classmethod
    def load_from_settings(
        cls,
        network: QNetworkAccessManager,
        api_type: str,
        api_env: str,
        user_email: str,
        realm: str,
    ):
        cookies = cls.load_cookies_from_settings(api_type, api_env, user_email, realm)
        cookie_jar = QNetworkCookieJar()
        cookie_jar.setAllCookies(cookies)
        network.setCookieJar(cookie_jar)

    @classmethod
    def _cookies_key(cls, api_type: str, api_env: str, user_email: str, realm: str):
        return "xyz_qgis/cookies/{api_type}/{api_env}/{user_email}/{realm}".format(
            api_type=api_type.lower(),
            api_env=api_env.lower(),
            user_email="None" if not user_email else user_email.lower(),
            realm="None" if not realm else realm.lower(),
        )

    @classmethod
    def save_cookies_to_settings(
        cls,
        cookies: List[QNetworkCookie],
        api_type: str,
        api_env: str,
        user_email: str,
        realm: str,
    ):
        key = cls._cookies_key(api_type, api_env, user_email, realm)
        txt = json.dumps([bytes(c.toRawForm()).decode("utf-8") for c in cookies])
        QSettings().setValue(key, txt)

    @classmethod
    def load_cookies_from_settings(cls, api_type: str, api_env: str, user_email: str, realm: str):
        key = cls._cookies_key(api_type, api_env, user_email, realm)
        txt = QSettings().value(key)
        obj = json.loads(txt) if txt else list()
        return [c for raw in obj for c in QNetworkCookie.parseCookies(raw.encode("utf-8"))]

    @classmethod
    def remove_cookies_from_settings(
        cls, api_type: str, api_env: str, user_email: str = None, realm: str = None
    ):
        s = QSettings()
        key = cls._cookies_key(api_type, api_env, user_email, realm)
        s.beginGroup(key)
        s.remove("")
        s.endGroup()

    @classmethod
    def remove_all_cookies_from_settings(cls):
        s = QSettings()
        key = "xyz_qgis/cookies"
        s.beginGroup(key)
        s.remove("")
        s.endGroup()

    @classmethod
    def get_cookies_from_url(cls, network: QNetworkAccessManager, url: QUrl):
        return network.cookieJar().cookiesForUrl(url)

    @classmethod
    def get_cookie_values(cls, network: QNetworkAccessManager, url: QUrl):
        return "; ".join(
            bytes(c.toRawForm(c.NameAndValueOnly)).decode("utf-8")
            for c in network.cookieJar().cookiesForUrl(url)
        )

    @classmethod
    def get_cookie(cls, network: QNetworkAccessManager, name: str):
        cookie = None
        for c in network.cookieJar().allCookies():
            if c.name() == name:
                cookie = c
        return cookie


class PlatformSettings:
    API_TYPE = API_TYPES.PLATFORM

    @classmethod
    def save_token_json(cls, token_json: str, api_env: str, user_email: str, realm: str):
        key = cls._token_setting_key(api_env, user_email, realm)
        QSettings().setValue(key, token_json)

    @classmethod
    def load_token_json(cls, api_env: str, user_email: str, realm: str) -> str:
        key = cls._token_setting_key(api_env, user_email, realm)
        txt = QSettings().value(key)
        return txt

    @classmethod
    def remove_token_json(cls, api_env: str, user_email: str, realm: str):
        s = QSettings()
        key = cls._token_setting_key(api_env, user_email, realm)
        s.beginGroup(key)
        s.remove("")
        s.endGroup()

    @classmethod
    def remove_settings(cls):
        key = "{settings_prefix}/{api_type}".format(
            settings_prefix="xyz_qgis/settings",
            api_type=cls.API_TYPE.lower(),
        )
        s = QSettings()
        s.beginGroup(key)
        s.remove("")
        s.endGroup()

    @classmethod
    def _token_setting_key(cls, api_env: str, user_email: str, realm: str):
        return cls._setting_key(api_env, user_email, realm, "tokenJson")

    @classmethod
    def _setting_key(cls, api_env: str, user_email: str, realm: str, key: str):
        # api_type: datahub, platform
        # api_env: prd, sit
        # user_email: default or some@email.com
        # realm: olp-here, ..
        return "{settings_prefix}/{api_type}/{api_env}/{user_email}/{realm}/{key}".format(
            settings_prefix="xyz_qgis/settings",
            api_type=cls.API_TYPE.lower(),
            api_env=api_env.lower(),
            user_email="None" if not user_email else user_email.lower(),
            realm="None" if not realm else realm.lower(),
            key=key,
        )
