# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2021 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.PyQt.QtCore import QThreadPool

from ...common.error import parse_exception_obj
from ...network import net_handler
from ...iml.network import IMLNetworkManager
from ...loader.layer_loader import AsyncFun

from ...controller import ChainController, NetworkFun, WorkerFun, ChainInterrupt

from ...common.signal import make_print_qgis, make_qt_args

print_qgis = make_print_qgis("iml_auth_loader")


class AuthenticationError(Exception):
    _msg = "Authentication failed"

    def __init__(self, conn_info):
        super().__init__(self._msg)
        self.conn_info = conn_info

    def get_conn_info(self):
        return self.conn_info


class HomeProjectNotFound(AuthenticationError):
    _msg = "No home project linked to catalog"


class IMLAuthLoader(ChainController):
    def __init__(self, network):
        super().__init__()
        self.pool = QThreadPool()  # .globalInstance() will crash afterward
        self._config(network)

    def start(self, conn_info):
        super().start(conn_info)

    def _config(self, network: IMLNetworkManager):
        self.config_fun(
            [
                NetworkFun(network.auth),
                WorkerFun(network.on_received, self.pool),
                AsyncFun(self._update_auth),
            ]
        )

    def _update_auth(self, conn_info, obj):
        token = obj.get("accessToken")
        if token:
            conn_info.set_(token=token)
        scope = obj.get("scope")
        if scope:
            conn_info.set_(scope=scope)
        return conn_info


class IMLProjectScopedAuthLoader(IMLAuthLoader):
    def _config(self, network: IMLNetworkManager):
        self.config_fun(
            [
                NetworkFun(network.auth),
                WorkerFun(network.on_received, self.pool),
                AsyncFun(self._update_auth),
                NetworkFun(network.get_project),
                WorkerFun(network.on_received, self.pool),
                AsyncFun(self._update_project_hrn),
                NetworkFun(network.auth_project),
                WorkerFun(network.on_received, self.pool),
                AsyncFun(self._update_auth),
            ]
        )

    def _update_project_hrn(self, conn_info, project):
        if project:
            conn_info.set_(project_hrn=project.get("hrn"))
        else:
            raise HomeProjectNotFound(conn_info)
        return conn_info

    def _handle_error(self, err):
        chain_err = parse_exception_obj(err)
        if isinstance(chain_err, ChainInterrupt):
            e, idx = chain_err.args[0:2]
        else:
            e = chain_err
        if isinstance(e, AuthenticationError):
            self.signal.results.emit(make_qt_args(e.get_conn_info()))
            self.signal.finished.emit()
        elif isinstance(e, net_handler.NetworkError):
            response = e.get_response()
            status = response.get_status()
            reply_tag = response.get_reply_tag()
            conn_info = response.get_conn_info()
            if reply_tag == "get_project" and status in (404,):
                # if no home project found, finish safely
                # iml somehow works with no-scoped token in this case
                self.signal.results.emit(make_qt_args(conn_info))
                self.signal.finished.emit()
                return
        # otherwise emit error
        self.signal.error.emit(err)
