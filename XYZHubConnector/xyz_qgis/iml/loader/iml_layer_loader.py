# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2021 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from .iml_auth_loader import IMLProjectScopedAuthLoader, AuthenticationError
from ...layer import queue
from ...loader.layer_loader import (
    TileLayerLoader,
    parse_exception_obj,
    ChainInterrupt,
    InitUploadLayerController,
    UploadLayerController,
    LiveTileLayerLoader,
    LoadLayerController,
    EditSyncController,
)
from ...network.net_handler import NetworkResponse, NetworkError
from ...common.signal import make_fun_args


class IMLAuthExtension:
    MAX_RETRY_COUNT = 2

    def __init__(self, network, *a, **kw):
        # setup retry with reauth
        self._reset_retry_cnt()
        self.con_auth = IMLProjectScopedAuthLoader(network)
        self.con_auth.signal.results.connect(make_fun_args(self._after_retry_with_auth))
        self.con_auth.signal.error.connect(self._handle_auth_error)

    def _handle_auth_error(self, err):
        chain_err = parse_exception_obj(err)
        if isinstance(chain_err, ChainInterrupt):
            e, idx = chain_err.args[0:2]
        else:
            e = chain_err
        self._release()  # release active dispatch
        self.signal.error.emit(AuthenticationError(e))

    def _handle_error(self, err):

        chain_err = parse_exception_obj(err)
        if isinstance(chain_err, ChainInterrupt):
            e, idx = chain_err.args[0:2]
        else:
            e = chain_err
        if isinstance(e, NetworkError):  # retry only when network error, not timeout
            # print(e, self._retry_cnt)
            response = e.get_response()
            status = response.get_status()
            reply = response.get_reply()
            if status in (401, 403):
                if self._retry_cnt < self.MAX_RETRY_COUNT:
                    self._retry_with_auth(reply)
                    return
            else:
                self._retry(reply)
                return
        # otherwise emit error
        self._release()  # release active dispatch
        self.signal.error.emit(err)

    def _reset_retry_cnt(self):
        self._retry_cnt = 0

    def _retry_with_auth(self, reply):
        self._retry_cnt += 1
        # retried params
        self.params_queue.retry_params()
        # try to reauth, then continue run loop
        self.con_auth.start(self.get_conn_info())

    def _after_retry_with_auth(self, conn_info=None):
        self._run_loop()

    def _refresh_loader(self, network, loader: LoadLayerController):
        self._reset_retry_cnt()
        conn_info = network.apply_connected_conn_info(loader.get_conn_info())

    def _save_conn_info_to_layer(self, loader: LoadLayerController):
        loader.layer.update_conn_info(loader.get_conn_info())


class IMLTileLayerLoader(IMLAuthExtension, TileLayerLoader):
    def __init__(self, network, *a, **kw):
        TileLayerLoader.__init__(self, network, *a, **kw)
        IMLAuthExtension.__init__(self, network, *a, **kw)
        self.params_queue = queue.SimpleRetryQueue(key="tile_id")
        self.network = network

    def _start(self, **kw):
        self._refresh_loader(self.network, self)
        super()._start(**kw)

    def _post_render(self):
        super()._post_render()
        self._save_conn_info_to_layer(self)


class IMLLiveTileLayerLoader(IMLTileLayerLoader, LiveTileLayerLoader):
    def __init__(self, network, *a, **kw):
        # LiveTileLayerLoader init is same as TileLayerLoader, thus redundant here
        IMLTileLayerLoader.__init__(self, network, *a, **kw)


class IMLLayerLoader(IMLAuthExtension, LoadLayerController):
    def __init__(self, network, *a, **kw):
        LoadLayerController.__init__(self, network, *a, **kw)
        IMLAuthExtension.__init__(self, network, *a, **kw)
        self.network = network

    def _start(self, **kw):
        self._refresh_loader(self.network, self)
        super()._start(**kw)

    def _post_render(self):
        super()._post_render()
        self._save_conn_info_to_layer(self)

    def _retry_with_auth(self, reply):
        # retried params
        keys = ["limit", "handle"]
        params = dict(zip(keys, NetworkResponse(reply).get_qt_property(keys)))
        self.params_queue.gen_retry_params(**params)
        # try to reauth, then continue run loop
        self.con_auth.start(self.get_conn_info())


class IMLInitUploadLayerController(InitUploadLayerController):
    CLS_PARAMS_QUEUE = queue.SimpleRetryQueue


class IMLUploadLayerController(IMLAuthExtension, UploadLayerController):
    def __init__(self, network, *a, **kw):
        UploadLayerController.__init__(self, network, *a, **kw)
        IMLAuthExtension.__init__(self, network, *a, **kw)

    def _retry_with_auth(self, reply):
        # retried params
        self.lst_added_feat.retry_params()
        # try to reauth, then continue run loop
        self.con_auth.start(self.get_conn_info())


class IMLEditSyncController(IMLAuthExtension, EditSyncController):
    CLS_PARAMS_QUEUE = queue.SimpleRetryQueue

    def __init__(self, network, *a, **kw):
        EditSyncController.__init__(self, network, *a, **kw)
        IMLAuthExtension.__init__(self, network, *a, **kw)

    def _retry_with_auth(self, reply):
        # retried params
        self.lst_added_feat.retry_params()
        self.removed_feat.retry_params()
        # try to reauth, then continue run loop
        self.con_auth.start(self.get_conn_info())
