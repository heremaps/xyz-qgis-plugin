# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from ..common.here_credentials import HereCredentials


def mask_token(token):
    return "{!s:.7}***".format(token)


def parse_copyright(v):
    if not isinstance(v, list):
        return v
    lst = [". ".join(el[j] for j in ["label", "alt"] if j in el) for el in v]
    return lst


class SpaceConnectionInfo(object):
    EXCLUDE_PROJECT_KEYS = ["here_client_secret"]
    LIVEMAP = "LIVEMAP"
    LIVEMAP_CID = "3fN7oveDupmTGsr5mUM5"
    PLATFORM_SIT = "PLATFORM_SIT"
    PLATFORM_PRD = "PLATFORM_PRD"
    PLATFORM_KOREA = "PLATFORM_KOREA"
    PLATFORM_CHINA = "PLATFORM_CHINA"
    PLATFORM_SERVERS = [PLATFORM_PRD, PLATFORM_SIT, PLATFORM_KOREA, PLATFORM_CHINA]
    PLATFORM_AUTH_KEYS = ["user_login", "realm", "here_credentials"]
    PLATFORM_KEYS = ["server"] + PLATFORM_AUTH_KEYS
    PLATFORM_DEFAULT_USER_LOGIN = "email"
    PLATFORM_SERVER_NAMES = {
        PLATFORM_PRD: "HERE Platform",
        PLATFORM_SIT: "HERE Platform SIT",
        PLATFORM_KOREA: "HERE Platform Korea",
        PLATFORM_CHINA: "HERE Platform China",
    }

    def __init__(self, conn_info=None):
        self._is_protected = False
        if conn_info is None:
            self.obj = dict()
        else:
            self.obj = dict(conn_info.obj)

    def to_dict(self):
        return self.get_(dict)

    @classmethod
    def from_dict(cls, kw):
        obj = cls()
        obj.set_(**kw)
        return obj

    def set_(self, **kw):
        kw = {k: v.strip() if isinstance(v, str) else v for k, v in kw.items()}
        if "id" in kw:
            kw["space_id"] = kw.pop("id")
        self.obj.update(kw)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return "{0}({1})".format(
            self.__class__.__name__,
            ",".join(
                map(
                    lambda x: "{k}={v}".format(k=x, v=self.get_(x)),
                    ["server", "token", "space_id"],
                )
            ),
        )

    def get_xyz_space(self):
        return self.get_("token"), self.get_("space_id")

    def set_server(self, server):
        self.set_(server=server)

    def get_server(self):
        return self.get_("server")

    def get_token(self):
        return self.get_("token")

    def has_token(self):
        return bool(self.get_token())

    def get_(self, key, default=None):
        if key is dict:
            return dict(self.obj)
        else:
            return self.obj.get(key, default)

    def get_name(self):
        return self.get_("title") or self.get_("name")

    def get_id(self):
        return self.get_("id") or self.get_("space_id")

    def get_default_user_email(self):
        return self.PLATFORM_DEFAULT_USER_LOGIN

    def to_project_dict(self):
        d = self.to_dict()
        if self.get_("user_login"):
            d["user_login"] = self.get_default_user_email()
            d["token"] = ""
        for ex in self.EXCLUDE_PROJECT_KEYS:
            d.pop(ex, "")
        return d

    def to_platform_dict(self):
        return {k: self.get_(k) for k in self.PLATFORM_KEYS}

    @classmethod
    def platform_server_name(cls, server):
        return cls.PLATFORM_SERVER_NAMES.get(
            server,
            "HERE Platform {suffix}".format(suffix=server.replace("PLATFORM_", "").capitalize()),
        )

    def get_platform_server_name(self):
        self.platform_server_name(self.get_server())

    def is_livemap(self):
        packages = self.get_("packages", list())
        check_pkg = any(p for p in packages if self.LIVEMAP in p)
        check_cid = self.get_("cid") == self.LIVEMAP_CID
        return check_pkg or check_cid

    def is_platform_server(self):
        return (self.get_("server") or "").strip().upper() in self.PLATFORM_SERVERS

    def is_platform_sit(self):
        return (self.get_("server") or "").strip().upper() == self.PLATFORM_SIT

    def is_user_login(self):
        return bool(self.get_("user_login"))

    def get_user_email(self):
        return self.get_("user_login")

    def get_realm(self):
        return self.get_("realm")

    def get_platform_auth(self):
        return {k: self.get_(k) for k in self.PLATFORM_AUTH_KEYS}

    def is_valid(self):
        server = self.get_("server")
        token = self.get_("token")
        here_credentials = self.get_("here_credentials")
        user_login = self.get_("user_login")
        return bool(server and (token or here_credentials or user_login))

    def _load_here_credentials(self):
        credentials_file = self.get_("here_credentials")
        here_credentials = None
        if credentials_file and not self.is_user_login():
            here_credentials = HereCredentials.from_file(credentials_file)
        return here_credentials

    def load_here_credentials(self):
        here_credentials = self._load_here_credentials()
        self.set_(
            here_client_key=here_credentials.key,
            here_client_secret=here_credentials.secret,
            here_endpoint=here_credentials.endpoint,
        )
        return here_credentials

    def has_valid_here_credentials(self):
        return bool(self._load_here_credentials())

    def mark_protected(self):
        self._is_protected = True

    def is_protected(self):
        """Returns True if the connection auth should not be overriden by default connected auth"""
        return self._is_protected
