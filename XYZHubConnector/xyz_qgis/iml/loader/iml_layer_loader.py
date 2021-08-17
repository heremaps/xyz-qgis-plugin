# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2021 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from .iml_auth_loader import IMLProjectScopedAuthLoader
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


class AuthenticationError(Exception):
    pass


class IMLAuthExtension:
    MAX_RETRY_COUNT = 1

    def __init__(self, network, *a, **kw):
        # setup retry with reauth
        self._reset_retry_cnt()
        self.con_auth = IMLProjectScopedAuthLoader(network)
        self.con_auth.signal.finished.connect(self._retry_with_auth_cb)
        self.con_auth.signal.error.connect(self._handle_error)

    def _handle_error(self, err):

        chain_err = parse_exception_obj(err)
        if isinstance(chain_err, ChainInterrupt):
            e, idx = chain_err.args[0:2]
        else:
            e = chain_err
        if isinstance(e, NetworkError):  # retry only when network error, not timeout
            response = e.get_response()
            status = response.get_status()
            reply = response.get_reply()
            if status in (401, 403):
                if self._retry_cnt < self.MAX_RETRY_COUNT:
                    self._retry_with_auth(reply)
                else:
                    self.signal.error.emit(AuthenticationError("Authentication failed"))
            else:
                self._retry(reply)
            return
        # otherwise emit error
        self._release()  # hot fix, no finish signal
        self.signal.error.emit(err)

    def _reset_retry_cnt(self):
        self._retry_cnt = 0

    def _retry_with_auth(self, reply):
        self._retry_cnt += 1
        # retried params
        self.params_queue.retry_params()
        # try to reauth, then continue run loop
        self.con_auth.start(self.get_conn_info())

    def _retry_with_auth_cb(self):
        self._save_conn_info_to_layer()
        self._run_loop()

    def _save_conn_info_to_layer(self):
        layer = self.layer
        if layer:
            layer.update_conn_info()


class IMLTileLayerLoader(IMLAuthExtension, TileLayerLoader):
    def __init__(self, network, *a, **kw):
        TileLayerLoader.__init__(self, network, *a, **kw)
        IMLAuthExtension.__init__(self, network, *a, **kw)
        self.params_queue = queue.SimpleRetryQueue(key="tile_id")

    def _start(self, **kw):
        self._reset_retry_cnt()
        super()._start(**kw)


class IMLLiveTileLayerLoader(IMLTileLayerLoader, LiveTileLayerLoader):
    def __init__(self, network, *a, **kw):
        LiveTileLayerLoader.__init__(self, network, *a, **kw)
        IMLTileLayerLoader.__init__(self, network, *a, **kw)

    def _start(self, **kw):
        self._reset_retry_cnt()
        super()._start(**kw)


class IMLLayerLoader(IMLAuthExtension, LoadLayerController):
    def __init__(self, network, *a, **kw):
        LoadLayerController.__init__(self, network, *a, **kw)
        IMLAuthExtension.__init__(self, network, *a, **kw)

    def _start(self, **kw):
        self._reset_retry_cnt()
        super()._start(**kw)

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
