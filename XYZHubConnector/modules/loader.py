# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
#
###############################################################################

import json
from qgis.PyQt.QtCore import QThreadPool
from qgis.core import QgsProject

from .controller import AsyncFun, ChainController, NetworkFun, LoopController, WorkerFun, BasicSignal
from .controller import make_qt_args, parse_qt_args, parse_exception_obj, ChainInterrupt
from .layer import XYZLayer, parser, render, queue, bbox_utils
from .network import net_handler
from ..gui.util_dialog import exec_warning_dialog
from .loop_loader import BaseLoader, ParallelLoop, ParallelFun

########################
# Load
########################

class EmptyXYZSpaceError(Exception):
    pass
class ManualInterrupt(Exception):
    pass
    
class ReloadLayerController(BaseLoader):
    def __init__(self, network, n_parallel=1):
        super(ReloadLayerController, self).__init__()
        self.pool = QThreadPool() # .globalInstance() will crash afterward
        self.n_parallel = 1
        self.status = self.LOADING
        self._config(network)
    def start(self, conn_info, meta, **kw):
        self.layer = XYZLayer(conn_info, meta)
        self.kw = kw
        self.max_feat = kw.get("max_feat", None)
        self.fixed_params = dict( (k,kw[k]) for k in ["tags"] if k in kw)


        # print(super(BaseLoader,self), super()) 
        # super(BaseLoader,self): super of BaseLoader 
        super(ReloadLayerController, self).start( **kw)
    def start_args(self, args):
        a, kw = parse_qt_args(args)
        self.start( *a, **kw)
    def reload(self, **kw):
        if self.status != self.FINISHED: return
        self.reset(**kw)

    def reset(self, **kw):
        BaseLoader.reset(self, **kw)
        params = dict(
            limit=kw.get("limit") or 1,
            handle=kw.get("handle", 0),
        )
        self.params_queue = queue.ParamsQueue_deque_smart(params, buffer_size=1)

    def _config(self, network):
        self.config_fun([
            NetworkFun( network.load_features_iterate), 
            WorkerFun( net_handler.on_received, self.pool),
            AsyncFun( self._process_render), 
            WorkerFun( render.parse_feature, self.pool),
            AsyncFun( self._dispatch_render), 
            ParallelFun( self._render_single), 
            # AsyncFun( render.add_feature_render), # may crash !? -> AsyncFun
        ])
        # error
        # self.signal.error.connect(self._handle_net_error)

    def _check_status(self):
        assert self.status != self.FINISHED
        # print(self.status)
        if self.status == self.STOPPED: 
            self.signal.error.emit(ManualInterrupt())
            return False
        elif self.status == self.ALL_FEAT:
            if not self.params_queue.has_retry():
                self._try_finish()
                return False
        elif self.status == self.MAX_FEAT:
            self._try_finish()
            return False
        feat_cnt = self.get_feat_cnt()
        if self.max_feat is not None and feat_cnt >= self.max_feat:
            self.status = self.MAX_FEAT
            self._try_finish()
            return False
        return True
    def _run(self):
        conn_info = self.layer.conn_info
            
        # if not self.params_queue.has_next():
        #     self.params_queue.gen_params()
        params = self.params_queue.get_params()
        
        LoopController.start(self, conn_info, **params, **self.fixed_params)

    ##### custom fun

    def _process_render(self,txt,*a,**kw):
        # check if all feat fetched
        obj = json.loads(txt)
        feat_cnt = len(obj["features"])
        total_cnt = self.get_feat_cnt()
        if feat_cnt + total_cnt == 0:
            raise EmptyXYZSpaceError()
        # limit = kw["limit"]
        # if feat_cnt == 0 or feat_cnt < limit:
        if "handle" in obj:
            handle = int(obj["handle"])
            if not self.params_queue.has_next():
                self.params_queue.gen_params(handle=handle)
        else:
            if self.status == self.LOADING:
                self.status = self.ALL_FEAT
        map_fields = self.layer.get_map_fields()
        return make_qt_args(txt, map_fields)
    
    # non-threaded
    def _render(self, *parsed_feat):
        map_feat, map_fields = parsed_feat
        for geom in map_feat.keys():

            if not self.layer.is_valid( geom):
                vlayer=self.layer.show_ext_layer(geom)
            else:
                vlayer=self.layer.get_layer( geom)

            feat = map_feat[geom]
            fields = map_fields[geom]

            render.add_feature_render(vlayer, feat, fields)

    def get_feat_cnt(self):
        return self.layer.get_feat_cnt()

    ############ handle_error
    def _get_params_reply(self, reply):
        keys = ["limit", "handle"]
        return dict(zip(
            keys,
            net_handler.get_qt_property(reply, keys)
        ))
    def _handle_error(self, err):
        chain_err = parse_exception_obj(err)
        if isinstance(chain_err, ChainInterrupt):
            e, idx = chain_err.args[0:2]
            if isinstance(e, net_handler.NetworkError):
                reply = e.args[-1]
                params = self._get_params_reply(reply)
                self.params_queue.gen_retry_params(**params)
                # start from beginning
                return
        # otherwise emit error
        self.signal.error.emit(err)

    #threaded (parallel)
    def _dispatch_render(self, *parsed_feat):
        map_feat, map_fields = parsed_feat
        lst_args = [(
            geom,
            map_feat[geom],
            map_fields[geom]
            )
            for geom in map_feat.keys()
        ]
        return lst_args
    def _render_single(self, geom, feat, fields):
        if not self.layer.is_valid( geom):
            vlayer=self.layer.show_ext_layer(geom)
        else:
            vlayer=self.layer.get_layer( geom)

        render.add_feature_render(vlayer, feat, fields)

    # def render_dispatch(self,parsed_feat,*a,**kw):
    #     map_feat, crs = parsed_feat
    #     fn = ParallelFun(self._render, (
    #         (k,v,crs,a,kw) for k,v in map_feat.items()
    #         ))
    #     fn.dispatch_parallel(n_parallel = len(map_feat.keys()))
        
    # def _render_dispatch(self, geom, feat,crs,a, kw):
    #     if not self.layer.is_valid( geom):
    #         vlayer=self.layer.show_ext_layer(geom, crs)
    #     else:
    #         vlayer=self.layer.get_layer( geom)

    #     render.add_feature_render(vlayer, feat, *a, **kw)
