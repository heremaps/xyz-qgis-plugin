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


class IMLAuthExtension:
    def __init__(self, network, *a, **kw):
        # setup retry with reauth
        self.con_auth = IMLProjectScopedAuthLoader(network)
        self.con_auth.signal.finished.connect(self._retry_with_auth_cb)
        self.con_auth.signal.error.connect(self.signal.error.emit)

    def _handle_error(self, err):

        chain_err = parse_exception_obj(err)
        if isinstance(chain_err, ChainInterrupt):
            e, idx = chain_err.args[0:2]
        else:
            e = chain_err
        if isinstance(e, NetworkError):  # retry only when network error, not timeout
            status = e.get_response().get_status()
            reply = e.get_response().get_reply()
            if status in (401, 403):
                self._retry_with_auth(reply)
            else:
                self._retry(reply)
            return
        # otherwise emit error
        self._release()  # hot fix, no finish signal
        self.signal.error.emit(err)

    def _retry_with_auth(self, reply):
        # retried params
        self.params_queue.retry_params()
        # try to reauth, then continue run loop
        self.con_auth.start(self.get_conn_info())

    def _retry_with_auth_cb(self):
        self._run_loop()


class IMLTileLayerLoader(IMLAuthExtension, TileLayerLoader):
    def __init__(self, network, *a, **kw):
        TileLayerLoader.__init__(self, network, *a, **kw)
        IMLAuthExtension.__init__(self, network, *a, **kw)
        self.params_queue = queue.SimpleRetryQueue(key="tile_id")


class IMLLiveTileLayerLoader(IMLTileLayerLoader, LiveTileLayerLoader):
    def __init__(self, network, *a, **kw):
        LiveTileLayerLoader.__init__(self, network, *a, **kw)
        IMLTileLayerLoader.__init__(self, network, *a, **kw)


class IMLLayerLoader(IMLAuthExtension, LoadLayerController):
    def __init__(self, network, *a, **kw):
        LoadLayerController.__init__(self, network, *a, **kw)
        IMLAuthExtension.__init__(self, network, *a, **kw)

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
