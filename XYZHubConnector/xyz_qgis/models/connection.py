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
    PLATFORM_SERVERS = [PLATFORM_PRD, PLATFORM_SIT]

    def __init__(self, conn_info=None):
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

    def get_(self, key, default=None):
        if key is dict:
            return dict(self.obj)
        else:
            return self.obj.get(key, default)

    def get_name(self):
        return self.get_("title") or self.get_("name")

    def get_id(self):
        return self.get_("id") or self.get_("space_id")

    def set_server(self, server):
        self.set_(server=server)
        # sv = server.strip().upper()
        # self.server = sv

    def to_project_dict(self):
        d = self.to_dict()
        for ex in self.EXCLUDE_PROJECT_KEYS:
            d.pop(ex, "")
        return d

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
        # "hrn:here:data::realm:layer_id"
        hrn = self.get_("hrn", "")
        if hrn:
            lst = hrn.split(":")
            realm = lst[4] if len(lst) >= 4 else self.get_("realm")
            self.set_(realm=realm)
            return realm
        else:
            realm = self.get_("realm")
        return realm

    def is_valid(self):
        server = self.get_("server")
        token = self.get_("token")
        here_credentials = self.get_("here_credentials")
        user_login = self.get_("user_login")
        return bool(server and (token or here_credentials or user_login))

    def load_here_credentials(self):
        credentials_file = self.get_("here_credentials")
        here_credentials = None
        if credentials_file and not self.is_user_login():
            here_credentials = HereCredentials.from_file(credentials_file)
            self.set_(
                here_client_key=here_credentials.key,
                here_client_secret=here_credentials.secret,
                here_endpoint=here_credentials.endpoint,
            )
        return here_credentials
