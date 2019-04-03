# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

class UXDecorator(object):
    def __init__(self):
        raise NotImplementedError()
    def config(self,*a):
        raise NotImplementedError()
    def ui_valid_input(self,*a):
        raise NotImplementedError()
    