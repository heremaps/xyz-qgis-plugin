# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2021 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from .iml_auth_loader import IMLAuthLoader, IMLProjectScopedSemiAuthLoader
from ..network import IMLNetworkManager
from ...common.signal import make_fun_args, make_qt_args
from ...controller import NetworkFun, WorkerFun, AsyncFun, ChainController, DelayedIdentityFun

from ...loader.space_loader import (
    LoadSpaceController,
    StatSpaceController,
    DeleteSpaceController,
    EditSpaceController,
    CreateSpaceController,
)

from ...common.signal import make_print_qgis

print_qgis = make_print_qgis("iml_space_loader")


class IMLSpaceController(LoadSpaceController):
    def __init__(self, network):
        super().__init__(network)
        self.con_auth = IMLAuthLoader(network)
        self.con_auth.signal.results.connect(make_fun_args(super().start))
        self.con_auth.signal.error.connect(self.signal.error.emit)

    def start(self, conn_info):
        self.con_auth.start(conn_info)


class IMLStatSpaceController(StatSpaceController):
    def __init__(self, network):
        super().__init__(network)
        self.con_auth = IMLProjectScopedSemiAuthLoader(network)
        self.con_auth.signal.results.connect(make_fun_args(super().start))
        self.con_auth.signal.error.connect(self.signal.error.emit)

    def start(self, conn_info):
        self.con_auth.start(conn_info)

    def reset_fun(self):
        self.con_auth.reset_fun()
        super().reset_fun()


class IMLDeleteSpaceController(DeleteSpaceController):
    def __init__(self, network):
        super().__init__(network)
        self.con_auth = IMLProjectScopedSemiAuthLoader(network)
        self.con_auth.signal.results.connect(make_fun_args(self._start_after_auth))
        self.con_auth.signal.error.connect(self.signal.error.emit)

    def start(self, conn_info):
        if conn_info.get_("project_hrn") and conn_info.get_("token"):
            self._start_after_auth(conn_info)
        else:
            self.con_auth.start(conn_info)

    def _start_after_auth(self, conn_info):
        ChainController.start(self, conn_info)

    def _config(self, network: IMLNetworkManager):
        self.config_fun(
            [
                NetworkFun(network.del_layer),
                WorkerFun(network.on_received, self.pool),
                DelayedIdentityFun(1000),
            ]
        )


class IMLEditSpaceController(EditSpaceController):
    def __init__(self, network):
        super().__init__(network)
        self.con_auth = IMLProjectScopedSemiAuthLoader(network)
        self.con_auth.signal.results.connect(make_fun_args(self._start_after_auth))
        self.con_auth.signal.error.connect(self.signal.error.emit)

    def start(self, conn_info, layer_info):
        self.layer_info = layer_info
        if conn_info.get_("project_hrn") and conn_info.get_("token"):
            self._start_after_auth(conn_info)
        else:
            self.con_auth.start(conn_info)

    def _start_after_auth(self, conn_info):
        ChainController.start(self, conn_info, self.layer_info)

    def _config(self, network: IMLNetworkManager):
        self.config_fun(
            [
                NetworkFun(network.edit_layer),
                WorkerFun(network.on_received, self.pool),
                DelayedIdentityFun(1000),
            ]
        )


class IMLCreateSpaceController(CreateSpaceController):
    def __init__(self, network):
        super().__init__(network)
        self.con_auth = IMLProjectScopedSemiAuthLoader(network)
        self.con_auth.signal.results.connect(make_fun_args(self._start_after_auth))
        self.con_auth.signal.error.connect(self.signal.error.emit)
        self.layer_info = dict()

    def start(self, conn_info, layer_info):
        self.layer_info = layer_info
        if conn_info.get_("project_hrn") and conn_info.get_("token"):
            self._start_after_auth(conn_info)
        else:
            self.con_auth.start(conn_info)

    def _start_after_auth(self, conn_info):
        ChainController.start(self, conn_info)

    def _config(self, network: IMLNetworkManager):
        self.config_fun(
            [
                NetworkFun(network.get_catalog),
                WorkerFun(network.on_received, self.pool),
                AsyncFun(self._prepare_layer_catalog),
                NetworkFun(network.add_layer),
                WorkerFun(network.on_received, self.pool),
                DelayedIdentityFun(2000),
            ]
        )

    def _prepare_layer_catalog(self, conn_info, obj):
        return make_qt_args(conn_info, self.layer_info, catalog_info=obj)
