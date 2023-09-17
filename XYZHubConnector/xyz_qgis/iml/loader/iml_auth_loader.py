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

from ...controller import (
    ChainController,
    NetworkFun,
    WorkerFun,
    ChainInterrupt,
    AsyncFun,
    parse_exception_obj,
    make_qt_args,
)

from ...network.net_handler import NetworkError
from ...iml.network.network import IMLNetworkManager

from ...common.signal import make_print_qgis

print_qgis = make_print_qgis("iml_auth_loader")


class AuthenticationError(Exception):
    _msg = "Authentication failed"

    def __init__(self, error=None, conn_info=None):
        super().__init__(self._msg)
        self.error = error
        self.conn_info = conn_info

    def get_conn_info(self):
        return (
            self.error.get_response().get_conn_info()
            if isinstance(self.error, NetworkError)
            else self.conn_info
        )

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        if not self.error:
            return super().__repr__()
        if isinstance(self.error, NetworkError):
            response = self.error.get_response()
            url = response.get_url()
            status = response.get_status()
            reason = response.get_reason()
            err = response.get_error()
            err_str = response.get_error_string()
            reply_tag = response.get_reply_tag()
            pair = (status, reason) if status else (err, err_str)
            status_msg = "{0!s}: {1!s}".format(*pair)
            return "{0}({1})".format(
                self.__class__.__name__,
                "{}. {}. {}. Request: {}".format(self._msg, reply_tag, status_msg, url),
            )
        else:
            return "{0}({1})".format(self.__class__.__name__, repr(self.error))


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

    def _sorted_key_from_project_item_response(self, project):
        if project["relation"] == "home":
            order = 0
        elif "writeResource" in project.get("allowedActions", []):
            order = 1
        elif "readResource" in project.get("allowedActions", []):
            order = 2
        else:
            order = 3
        return "{order}{id}".format(order=order, id=project["id"])

    def _update_project_hrn(self, conn_info, projects):
        if projects["total"] > 0:
            sorted_projects = list(
                sorted(projects["items"], key=self._sorted_key_from_project_item_response)
            )
            project = sorted_projects[0]
            conn_info.set_(project_hrn=project.get("hrn"))
            conn_info.set_(project_item=project)
        else:
            raise HomeProjectNotFound(conn_info=conn_info)
        return conn_info

    def _handle_error(self, err):
        chain_err = parse_exception_obj(err)
        if isinstance(chain_err, ChainInterrupt):
            e, idx = chain_err.args[0:2]
        else:
            e = chain_err
        if isinstance(e, HomeProjectNotFound):
            self.signal.results.emit(make_qt_args(e.get_conn_info()))
            self.signal.finished.emit()
            return
        elif isinstance(e, NetworkError):
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


class IMLProjectScopedSemiAuthLoader(IMLProjectScopedAuthLoader):
    def _config(self, network: IMLNetworkManager):
        self.config_fun(
            [
                NetworkFun(network.get_project),
                WorkerFun(network.on_received, self.pool),
                AsyncFun(self._update_project_hrn),
                NetworkFun(network.auth_project),
                WorkerFun(network.on_received, self.pool),
                AsyncFun(self._update_auth),
            ]
        )
