# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2021 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


from .iml_auth_loader import IMLAuthLoader
from ...common.signal import make_fun_args

from ...loader.space_loader import LoadSpaceController, StatSpaceController, DeleteSpaceController, EditSpaceController, \
    CreateSpaceController

from ...common.signal import make_print_qgis

print_qgis = make_print_qgis("iml_space_loader")


class IMLSpaceController(LoadSpaceController):

    def _config(self, network):
        super()._config(network)
        self.con_auth = IMLAuthLoader(network)
        self.con_auth.signal.results.connect(make_fun_args(super().start))
        self.con_auth.signal.error.connect(self.signal.error.emit)

    def start(self, conn_info):
        self.con_auth.start(conn_info)

class IMLStatSpaceController(StatSpaceController):

    def _config(self, network):
        super()._config(network)
        self.con_auth = IMLAuthLoader(network)
        self.con_auth.signal.results.connect(make_fun_args(super().start))
        self.con_auth.signal.error.connect(self.signal.error.emit)

    def start(self, conn_info):
        self.con_auth.start(conn_info)

class IMLDeleteSpaceController(DeleteSpaceController):

    def _config(self, network):
        super()._config(network)
        self.con_auth = IMLAuthLoader(network)
        self.con_auth.signal.results.connect(make_fun_args(super().start))
        self.con_auth.signal.error.connect(self.signal.error.emit)

    def start(self, conn_info):
        self.con_auth.start(conn_info)

class IMLEditSpaceController(EditSpaceController):

    def _config(self, network):
        super()._config(network)
        self.con_auth = IMLAuthLoader(network)
        self.con_auth.signal.results.connect(make_fun_args(super().start))
        self.con_auth.signal.error.connect(self.signal.error.emit)

    def start(self, conn_info):
        self.con_auth.start(conn_info)

class IMLCreateSpaceController(CreateSpaceController):

    def _config(self, network):
        super()._config(network)
        self.con_auth = IMLAuthLoader(network)
        self.con_auth.signal.results.connect(make_fun_args(super().start))
        self.con_auth.signal.error.connect(self.signal.error.emit)

    def start(self, conn_info):
        self.con_auth.start(conn_info)
