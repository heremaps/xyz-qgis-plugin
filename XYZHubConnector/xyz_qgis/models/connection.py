# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


def parse_copyright(v):
    if not isinstance(v, list): return v
    lst = [
        ". ".join(el[j] for j in ["label","alt"] if j in el)
        for el in v
    ]
    return lst

class SpaceConnectionInfo(object):
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
        kw = {k:v.strip() if isinstance(v, str) else v for k, v in kw.items()}
        if "id" in kw:
            kw["space_id"] = kw.pop("id")
        self.obj.update(kw)
    def __repr__(self):
        return "{0}({1})".format(
            self.__class__.__name__,
            ",".join(map(
                lambda x: "{k}={v}".format(k=x, v=self.get_(x)),
                ["server","token","space_id"]
            ))
        )
    def get_xyz_space(self):
        return self.get_("token"), self.get_("space_id")
    def get_(self, key, default=None):
        if key is dict: return self.obj
        else: return self.obj.get(key, default)
    def set_server(self, server):
        self.set_(server=server)
        # sv = server.strip().upper()
        # self.server = sv
