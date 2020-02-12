# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2020 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

class InvalidLoadingMode(Exception):
    pass

class LoadingMode(list):
    LIVE = "live"
    INCREMENTAL = "incremental"
    STATIC = "static"
    def __init__(self):
        super().__init__([self.LIVE, self.INCREMENTAL, self.STATIC])

LOADING_MODES = LoadingMode() # live, incremental, single
