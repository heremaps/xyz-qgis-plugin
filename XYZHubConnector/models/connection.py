# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


class SpaceConnectionInfo(object):
    PRD = "PRD"
    CIT = "CIT"
    SIT = "SIT"
    def __init__(self, conn_info=None):
        if conn_info is None:
            self.obj = dict()
            self.server = self.PRD
        else:
            self.obj = dict(conn_info.obj)
            self.server = conn_info.server
    def to_dict(self):
        return self.get_(dict)
    @classmethod
    def from_dict(cls, kw):
        obj = cls()
        obj.set_(**kw)
        return obj
    def set_(self, **kw):
        if "id" in kw:
            kw["space_id"] = kw.pop("id")
        self.obj.update(kw)
    def __repr__(self):
        return str(self.get_xyz_space())
    def get_xyz_space(self):
        return self.get_("token"), self.get_("space_id")
    def get_(self, key):
        if key is dict: return self.obj
        else: return self.obj.get(key)
    def is_PRD(self):
        return self.server == self.PRD
    def set_server(self, server):
        sv = server.strip().upper()
        if sv in (self.PRD, self.CIT, self.SIT):
            self.server = sv
