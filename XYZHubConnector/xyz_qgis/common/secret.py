# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

class Secret():
    SECRET = "WXpKV2FtTnRWakE9"
    def __init__(self, ini):
        self.ini = ini
        with open(self.ini,"a+") as f:
            f.seek(0)
            s = f.read().strip()
        if len(s) == 0:
            self.deactivate()
        self.flag = (s == self.SECRET)
    def activate(self):
        self.flag = 1
        with open(self.ini,"w") as f:
            f.write(self.SECRET)
    def deactivate(self):
        self.flag = 0
        with open(self.ini,"w") as f:
            f.write("here.xyz")
    def activated(self):
        return bool(self.flag)