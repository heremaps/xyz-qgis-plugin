# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from ..controller import parse_qt_args, make_qt_args


class LayerManager(object):
    def __init__(self):
        self.layer_map = dict()
    def add_args(self, args):
        a, kw = parse_qt_args(args)
        layer = a[0]
        self.add(layer)
    def get(self, layer_id):
        return self.layer_map.get(layer_id)
    def add(self, layer):
        if layer is None: return
        vlayer = layer.get_layer()
        if vlayer is None: return
        layer_id = layer.get_layer().id()
        self.layer_map[layer_id] = layer

    def remove(self, layer_ids):
        for i in layer_ids:
            layer = self.layer_map.pop(i, None)
            print("del", layer)
            # this will not remove layer in controller
            # layer.unload()
            del layer

