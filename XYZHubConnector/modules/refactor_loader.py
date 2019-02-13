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
from .loop_loader import BaseLoader, ParallelLoop

class InitLayerController(ChainController):
    def __init__(self, network):
        super().__init__()
        self.pool = QThreadPool() # .globalInstance() will crash afterward
        self._config(network)
    def start(self, conn_info, meta, **kw):
        """ pass keyword like limit, handle
        """
        self.layer = XYZLayer(conn_info, meta)
        self.kw = kw
        kw_req = dict( (k, kw[k]) for k in ["tags"] if k in kw)
        ChainController.start(self, conn_info, limit=1, reply_tag="init_layer", **kw_req)
    def start_args(self, args):
        a, kw = parse_qt_args(args)
        self.start( *a, **kw)
    def _config(self, network):
        self.config_fun([
            NetworkFun( network.load_features_search), #   load_features_iterate
            WorkerFun( net_handler.on_received, self.pool),
            AsyncFun( self._init_mem_layer), # FIX
            # AsyncFun( dialog.cb_display_spaces), 
        ])
    def _init_mem_layer(self,*a,**kw):
        if self.kw.get("limit") is None:
            self.kw["limit"] = self._estimate_limit(*a)
        vlayer = self.layer.init_mem_layer(*a,**kw)
        # if vlayer is None:
        #     return None, self.kw
        return make_qt_args(self.layer, **self.kw)
    def _estimate_limit(self, *a):
        # estimate limit for request
        txt, raw = a[0:2]
        return parser.estimate_chunk_size(raw)
class InitExtLayerController(InitLayerController):
    def _init_mem_layer(self,*a,**kw):
        if self.kw.get("limit") is None:
            self.kw["limit"] = self._estimate_limit(*a)
        vlayer = self.layer.init_ext_layer(*a,**kw)
        # if vlayer is None:
        #     return None, self.kw
        return make_qt_args(self.layer, **self.kw)

class InvalidLayerError(Exception):
    pass

########################
# Load
########################

class ReloadLayerController(BaseLoader):
    def __init__(self, network, n_parallel=1):
        super(ReloadLayerController, self).__init__()
        self.pool = QThreadPool() # .globalInstance() will crash afterward
        self.n_parallel = 1
        self.status = self.LOADING
        self._config(network)
    def start(self, layer, **kw):
        ok1 = layer is not None and layer.is_valid()
        if not ok1:
            self.signal.error.emit( InvalidLayerError("XYZHub layer is None"))
            return
        self.layer = layer
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
            handle=kw.get("handle", 1),
        )
        self.params_queue = queue.ParamsQueue_deque_smart(params, buffer_size=1)

    def _config(self, network):
        self.config_fun([
            NetworkFun( network.load_features_iterate), 
            WorkerFun( net_handler.on_received, self.pool),
            AsyncFun( self._process_render), 
            WorkerFun( render.parse_feature, self.pool),
            AsyncFun( render.add_feature_render), # may crash !? -> AsyncFun
        ])
        # error
        # self.signal.error.connect(self._handle_net_error)
    def _check_valid(self):
        ok1 = self.layer is not None and hasattr(self.layer,"get_layer")
        if not ok1: return False

        vlayer = self.layer.get_layer()
        vl = QgsProject.instance().mapLayer(vlayer.id())
        if vl is None: return False
        return True
    def _check_status(self):
        assert self.status != self.FINISHED
        # print(self.status)
        if self.status == self.STOPPED: 
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

    def _process_render(self,txt,*a,**kw):
        # check if all feat fetched
        obj = json.loads(txt)
        limit = kw["limit"]
        # feat_cnt = len(obj["features"])
        # if feat_cnt == 0 or feat_cnt < limit:
        if "handle" in obj:
            handle = int(obj["handle"])
            if not self.params_queue.has_next():
                self.params_queue.gen_params(handle=handle)
        else:
            if self.status == self.LOADING:
                self.status = self.ALL_FEAT
        vlayer = self.layer.get_layer()
        fields = self.layer.get_layer().fields()
        return make_qt_args(txt, vlayer, fields)

    def get_feat_cnt(self):
        return self.layer.get_layer().featureCount()

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

class ReloadLayerController_bbox(ReloadLayerController):
    def reset(self, **kw):
        super(ReloadLayerController, self).reset( **kw) # not tested
        
        bbox = kw.get("bbox") or self.kw.get("bbox") or bbox_utils.rect_to_bbox(-180,-90,180,90) 
        self.bbox = bbox
        params = dict(
            bbox=bbox,
            limit=kw.get("limit") or self.kw.get("limit") or 1,
            nx=3,
            ny=3,
        )
        self.params_queue = queue.ParamsQueue_deque_bbox(params)
        
    def _config(self, network):
        self.config_fun([
            NetworkFun( network.load_features_bbox), 
            WorkerFun( net_handler.on_received, self.pool),
            AsyncFun( self._process_render), 
            WorkerFun( render.merge_feature, self.pool),
            AsyncFun( render.add_feature_render), # may crash !? -> AsyncFun
        ])
        # error
        # self.signal.error.connect(self._handle_net_error)

    def _process_render(self,txt,*a,**kw):
        vlayer = self.layer.get_layer()
        fields = self.layer.get_layer().fields()
        exist_feat_id = self.layer.get_xyz_feat_id()
        return make_qt_args(txt, vlayer, fields, exist_feat_id)
        
    def _check_status(self):
        assert self.status != self.FINISHED
        # print(self.status)
        if self.status == self.STOPPED: 
            return False
        elif not self.params_queue.has_next():
            self._try_finish()
            return False
        # ignore max_feat check
        return True
    def _run(self):
        conn_info = self.layer.conn_info
        params = self.params_queue.get_params()
            
        LoopController.start(self, conn_info, **params, **self.fixed_params)
    def _get_params_reply(self, reply):
        keys = ["bbox","limit"]
        return dict(zip(
            keys,
            net_handler.get_qt_property(reply, keys)
        ))


########################
# Upload
########################

from .layer import layer_utils
import copy
class InitUploadLayerController(ChainController):
    def __init__(self, network):
        super(InitUploadLayerController, self).__init__()
        self.pool = QThreadPool() # .globalInstance() will crash afterward
        self._config(network)
        
    def start(self, conn_info, meta, vlayer, **kw):
        # assumed start() is called once
        self.conn_info = copy.deepcopy(conn_info) # upload
        self.meta = meta # upload
        self.kw = kw        
        if vlayer is None:
            return
        super(InitUploadLayerController, self).start( vlayer)
    def start_args(self, args):
        a, kw = parse_qt_args(args)
        self.start(*a, **kw)

    def _config(self, network):
        self.config_fun([
            AsyncFun( layer_utils.get_feat_iter),
            WorkerFun( layer_utils.get_feat_upload_from_iter, self.pool),
            AsyncFun( self._setup_queue), 
            NetworkFun( network.add_space), 
            WorkerFun( net_handler.on_received, self.pool),
            AsyncFun( self._setup_conn), 
        ])

    def _setup_queue(self, lst_added_feat, removed_feat):
        if len(lst_added_feat) == 0:
            self.signal.finished.emit()
        self.lst_added_feat = queue.SimpleQueue(lst_added_feat)
        return self.get_conn_info(), self.get_meta()
    def _setup_conn(self, conn_info, obj):
        conn_info = self.get_conn_info()
        token, _ = conn_info.get_xyz_space()
        space_id = obj.get("id")
        conn_info.set_(space_id=space_id)
        return make_qt_args(conn_info, self.lst_added_feat, **self.kw)
    def get_conn_info(self):
        return self.conn_info
    def get_meta(self):
        return self.meta
        
class UploadLayerController(ParallelLoop):
    
    def __init__(self, network, n_parallel=1):
        super(UploadLayerController, self).__init__()
        self.n_parallel = n_parallel
        self.pool = QThreadPool() # .globalInstance() will crash afterward
        self._config(network)
        self.feat_cnt = 0
    def _config(self, network):
        self.config_fun([
            NetworkFun( network.add_features), 
            WorkerFun( net_handler.on_received, self.pool),
            AsyncFun( self._process),
        ])
    def _process(self, obj, *a):
        self.feat_cnt += len(obj["features"])
    def get_feat_cnt(self):
        return self.feat_cnt
    def start(self, conn_info, lst_added_feat, **kw):
        self.conn_info = conn_info
        self.lst_added_feat = lst_added_feat

        self.fixed_params = dict(addTags=kw["tags"]) if "tags" in kw else dict()

        if self.count_active() == 0:
            super(UploadLayerController, self).reset()
        self.dispatch_parallel(n_parallel=self.n_parallel)
    def start_args(self, args):
        a, kw = parse_qt_args(args)
        self.start( *a, **kw)
    def _run_loop(self):
        if not self.lst_added_feat.has_next():
            self._try_finish()
            return
            
        conn_info = self.get_conn_info()
        feat = self.lst_added_feat.get_params()
        LoopController.start(self, conn_info, feat, **self.fixed_params)
    def get_conn_info(self):
        return self.conn_info


    def _handle_error(self, err):
        self.signal.error.emit(err)