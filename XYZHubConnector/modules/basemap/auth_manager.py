# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import configparser

class AuthManager(object):
    ROOT = "auth"
    APP_ID = "app_id"
    APP_CODE = "app_code"
    def __init__(self, ini):
        self.ini = ini
        cp = configparser.ConfigParser()
        cp.optionxform = str
        cp.add_section(self.ROOT)
        
        with open(ini, "a+") as f:
            f.seek(0)
            cp.read_file(f)
        self.cp = cp

    def save(self,app_id,app_code):
        self.cp.set(self.ROOT, self.APP_ID, app_id )
        self.cp.set(self.ROOT, self.APP_CODE, app_code )

        with open(self.ini, "w") as f:
            self.cp.write(f)
    def get_auth(self):
        return dict(self.cp.items(self.ROOT))