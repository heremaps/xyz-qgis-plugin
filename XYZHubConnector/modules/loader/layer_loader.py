# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import copy
import json
from typing import Any, Callable, Dict, List, Union

from qgis.core import QgsProject, QgsVectorLayer, QgsRectangle
from qgis.PyQt.QtCore import QThreadPool
from qgis.PyQt.QtNetwork import QNetworkReply

from ..controller import (AsyncFun, BasicSignal, ChainController,
                          ChainInterrupt, LoopController, NetworkFun,
                          WorkerFun, make_qt_args, parse_exception_obj,
                          parse_qt_args)
from ..layer import XYZLayer, bbox_utils, layer_utils, parser, queue, render, tile_utils
from ..layer.edit_buffer import LayeredEditBuffer
from ..network import NetManager, net_handler
from .loop_loader import BaseLoader, BaseLoop, ParallelFun
from ...models import SpaceConnectionInfo


from ..common.signal import make_print_qgis
print_qgis = make_print_qgis("layer_loader")

Meta = Dict[str,str]
Geojson = Dict

########################
# Load
########################

class EmptyXYZSpaceError(Exception):
    pass
class InvalidQgsLayerError(Exception):
    pass
class InvalidXYZLayerError(Exception):
    pass
class ManualInterrupt(Exception):
    pass
    
class LoadLayerController(BaseLoader):
    """ Load XYZ space into several qgis layer separated by Geometry type.
    If space is empty, no layer shall be created.
    Stateful controller
    """
    def __init__(self, network: NetManager, layer: XYZLayer=None, n_parallel=1):
        BaseLoader.__init__(self)

        self.pool = QThreadPool() # .globalInstance() will crash afterward
        self.n_parallel = 1
        self.status = self.LOADING

        self.fixed_keys = ["tags"]
        self.layer = layer
        self.max_feat: int = None
        self.kw: dict = None
        self.fixed_params = dict()
        self.params_queue: queue.ParamsQueue = None

        self._cb_network_load = network.load_features_iterate
        self._config()

        if layer:
            self._config_layer_callback(layer)

    def post_render(self,*a,**kw):
        for v in self.layer.iter_layer():
            v.triggerRepaint()
            
    def _config_layer_callback(self, layer):
        layer.config_callback(
            stop_loading=self.stop_loading
            )

    def start(self, conn_info: SpaceConnectionInfo, meta: Meta, **kw):
        tags = kw.get("tags","")
        self.layer = XYZLayer(conn_info, meta, tags=tags, loader_params=kw)
        self.layer.add_empty_group()
        self._config_layer_callback(self.layer)
        return self._start(**kw)

    def _start(self, **kw):
        # # super(BaseLoader,self): super of BaseLoader 
        # # includes check status and reset
        BaseLoader.start(self, **kw)
        return self.layer
    def restart(self, *a, **kw):
        # if self.status != self.FINISHED: return
        # self.reset(**kw)
        # includes reset
        if self.layer is None: 
            raise InvalidXYZLayerError()
        self.stop_loading()
        params = self.layer.get_loader_params()
        params.update(kw)
        return self._start(**params)
        

    def reset(self, **kw):
        """
        generate params_queue from kw given in start()
        """
        BaseLoader.reset(self, **kw)

        self.kw = kw
        self.max_feat = kw.get("max_feat", None)
        self.fixed_params.update( 
            (k,kw[k]) for k in self.fixed_keys if k in kw)

        params = dict(
            limit=kw.get("limit") or 1,
            handle=kw.get("handle", 0),
        )
        self.params_queue = queue.ParamsQueue_deque_smart(params, buffer_size=1)

    def _config(self):
        self.config_fun([
            NetworkFun( self._cb_network_load), 
            WorkerFun( net_handler.on_received, self.pool),
            AsyncFun( self._process_render), 
            WorkerFun( render.parse_feature, self.pool),
            AsyncFun( self._dispatch_render), 
            ParallelFun( self._render_single), 
        ])
        self.signal.finished.connect(self.post_render)

    def _check_status(self):
        if self.status == self.FINISHED:
            self._try_finish()
            return False
        elif self.status == self.STOPPED:
            self._after_loading_stopped()
            return False
        elif self.status == self.ALL_FEAT:
            if not self.params_queue.has_retry():
                if self.get_feat_cnt() == 0:
                    self._handle_error(EmptyXYZSpaceError())
                else:
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
            
        # TODO refactor methods
        if not self.params_queue.has_next():
            self.status = self.FINISHED
            self._try_finish()
            return
        params = self.params_queue.get_params()
        
        LoopController.start(self, conn_info, **params, **self.fixed_params)
    def _emit_finish(self):
        BaseLoop._emit_finish(self)
        token, space_id = self.layer.conn_info.get_xyz_space()
        name = self.layer.get_name()
        msg = (
            "%s features loaded. "%(self.get_feat_cnt()) +
            "Layer: %s. Token: %s"%(name, token)
            )
        self.signal.results.emit( make_qt_args(msg))
    ##### custom fun

    def _process_render(self,obj: Geojson,*a,**kw):
        # check if all feat fetched
        # feat_cnt = len(obj["features"])
        # total_cnt = self.get_feat_cnt()
        if "handle" in obj:
            handle = int(obj["handle"])
            if not self.params_queue.has_next():
                self.params_queue.gen_params(handle=handle)
        else:
            if self.status == self.LOADING:
                self.status = self.ALL_FEAT
        map_fields: dict = self.layer.get_map_fields()
        similarity_threshold = self.kw.get("similarity_threshold")
        return make_qt_args(obj, map_fields, similarity_threshold, **kw)
    
    # non-threaded
    def _render(self, *parsed_feat):
        map_feat, map_fields = parsed_feat
        for geom in map_feat.keys():
            for idx, (feat, fields) in enumerate(
            zip(map_feat[geom], map_fields[geom])):
                if not feat: continue
                if not self.layer.has_layer(geom, idx):
                    vlayer=self.layer.add_ext_layer(geom, idx)
                else:
                    vlayer=self.layer.get_layer(geom, idx)
                render.add_feature_render(vlayer, feat, fields)

    def get_feat_cnt(self):
        return self.layer.get_feat_cnt()

    ############ handle_error
    def _retry(self, reply: QNetworkReply):
        keys = ["limit", "handle"]
        params = dict(zip(
            keys,
            net_handler.get_qt_property(reply, keys)
        ))
            
        self.params_queue.gen_retry_params(**params)
        # retry from beginning
        self._run_loop()

    def _handle_error(self, err):
        chain_err = parse_exception_obj(err)
        if isinstance(chain_err, ChainInterrupt):
            e, idx = chain_err.args[0:2]
        else:
            e = chain_err
        if isinstance(e, net_handler.NetworkError): # retry only when network error, not timeout
            reply = e.args[-1]
            self._retry(reply)
            return
        # otherwise emit error
        self._release() # hot fix, no finish signal
        self.signal.error.emit(err)

    #threaded (parallel)
    def _dispatch_render(self, *parsed_feat):
        map_feat, map_fields, kw_params = parsed_feat
        lst_args = [(geom, idx, feat, fields, kw_params) 
            for geom in map_feat.keys()
            for idx, (feat, fields) in enumerate(zip(
                map_feat[geom], map_fields[geom]))
        ]

        return lst_args

    def _render_single(self, geom, idx, feat, fields, kw_params):
        if not feat: return
        vlayer = self._create_or_get_vlayer(geom, idx)
        render.add_feature_render(vlayer, feat, fields)

    def _create_or_get_vlayer(self, geom, idx):
        if not self.layer.has_layer(geom, idx):
            vlayer=self.layer.add_ext_layer(geom, idx)
        else:
            vlayer=self.layer.get_layer(geom, idx)
        return vlayer

    def destroy(self):
        self.stop_loading()
        self.layer.destroy()
        
    def stop_loading(self):
        """ Stop loading immediately
        """
        if self.status in [self.FINISHED, self.STOPPED]:
            return
        try:
            self.status = self.STOPPED
            self._config()
            self._after_loading_stopped()
        except Exception as err:
            self._handle_error(err)
    
    def _after_loading_stopped(self):
        msg = "Loading stopped. Layer: %s" % self.layer.get_name()
        # # self.show_info_msg(msg) # can be disabled if loading stop for different use case
        self._handle_error(ManualInterrupt(msg))
        # do not try_finish as it fail in case of vlayer deleted
        

    def show_info_msg(self, msg, dt=1):
        self.signal.info.emit(make_qt_args(
            msg, dt=dt
        ))

class TileLayerLoader(LoadLayerController):
    def __init__(self, network: NetManager, *a, layer: XYZLayer=None, **kw):
        super().__init__(network, *a, **kw)
        self.fixed_keys = ["tags", "limit", "tile_schema"]
        self.params_queue = queue.SimpleQueue(key="tile_id") # dont have retry logic
        self.layer = layer
        self.total_params = 0
        self.cnt_params = 0
        self.feat_cnt = 0
        self._cb_network_load = network.load_features_tile
        self._config()

        if layer:
            self._config_layer_callback(layer)

    def _config(self):
        self.config_fun([
            NetworkFun( self._cb_network_load), 
            WorkerFun( net_handler.on_received, self.pool),
            AsyncFun( self._process_render), 
            WorkerFun( render.parse_feature, self.pool),
            AsyncFun( self._dispatch_render), 
            ParallelFun( self._render_single), 
            AsyncFun( self.post_render), 
        ])

    def _check_status(self):
        if not self.params_queue.has_next():
            if self.status == self.LOADING:
                self.status = self.ALL_FEAT
            # self._try_finish()
            # return False
        ok = super()._check_status()
        print_qgis("check", self.status, self.count_active())
        return ok

    def _process_render(self, obj: Geojson,*a,**kw):
        # check if all feat fetched (optional)
        if not self.params_queue.has_next():
            if self.status == self.LOADING:
                self.status = self.ALL_FEAT
        
        self.cnt_params += 1
        if "features" in obj:
            self.feat_cnt += len(obj["features"])

        map_fields: dict = self.layer.get_map_fields()
        similarity_threshold = self.kw.get("similarity_threshold")
        return make_qt_args(obj, map_fields, similarity_threshold, **kw)

    def reset(self, **kw):
        """
        generate params_queue from kw given in start()
        """
        print_qgis("reset", self.status)
        BaseLoader.reset(self, **kw)

        self.kw = kw
        self.fixed_params.update( 
            (k, kw[k]) for k in self.fixed_keys if k in kw)

        lst: list = kw.pop("tile_ids")
        params = [dict(tile_id=i) for i in lst]
        
        self.params_queue.set_params(params) # dont have retry logic
        self.total_params = len(params)
        self.cnt_params = 0
        self.feat_cnt = 0

        # print_qgis("cache", self.params_queue._cache)
        # print_qgis("queue", self.params_queue._queue)

    def _handle_error(self, err):
        chain_err = parse_exception_obj(err)
        if isinstance(chain_err, ChainInterrupt):
            e, idx = chain_err.args[0:2]
        else:
            e = chain_err
        if isinstance(e, EmptyXYZSpaceError):
            return
        super()._handle_error(e)
        
    def _retry(self, reply: QNetworkReply):
        # ignore error, continue run loop
        self._run_loop()
        
    def _emit_finish(self):
        BaseLoop._emit_finish(self)
        if self.count_active() > 0:
            return
        token, space_id = self.layer.conn_info.get_xyz_space()
        name = self.layer.get_name()
        cnt = min(self.cnt_params, self.total_params)
        total = self.total_params
        msg = (
            "%s/%s tiles loaded. "%(cnt, total) +
            "%s features loaded. "%(self.feat_cnt) +
            "Layer: %s. Token: %s"%(name, token)
            )
        self.signal.results.emit( make_qt_args(msg))

    def _config_layer_callback(self, layer):
        layer.config_callback(
            start_editing=self._start_editing,
            end_editing=self._continue_loop,
            stop_loading=self.stop_loading,
            )

    def _start_editing(self):
        self.stop_loading()
        self.show_info_msg(" ".join([
            "Enter editing mode will disable interactive loading.", 
            "To re-enable loading, please exit editing mode and push changes to XYZ Hub.",
            "Layer: %s" % self.layer.get_name()
        ]))

    def _continue_loop(self):
        if self.count_active() == 0:
            BaseLoader.reset(self)
            self.dispatch_parallel(n_parallel=self.n_parallel)

class LiveTileLayerLoader(TileLayerLoader):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.params_queue = queue.SimpleQueue(key="tile_id") # dont have retry logic

    def _render_single(self, geom, idx, feat, fields, kw_params):
        vlayer = self._create_or_get_vlayer(geom, idx)
        tile_id = kw_params.get("tile_id")
        tile_schema = kw_params.get("tile_schema")
        lrc = tile_utils.parse_tile_id(tile_id, schema=tile_schema)
        rcl = [lrc[k] for k in ["row","col","level"]]
        extent = tile_utils.extent_from_row_col(*rcl, schema=tile_schema)
        render.clear_features_in_extent(vlayer, QgsRectangle(*extent))
        if not feat: return
        render.add_feature_render(vlayer, feat, fields)

########################
# Upload
########################

class InitUploadLayerController(ChainController):
    """ Prepare list of features of the input layer to be upload (added and removed)
    Stateful controller
    """
    def __init__(self, *a):
        ChainController.__init__(self)
        self.pool = QThreadPool() # .globalInstance() will crash afterward

        self.lst_added_feat: queue.ParamsQueue = None
        self.kw: dict = None
        self._config()
        
    def start(self, conn_info: SpaceConnectionInfo, vlayer: QgsVectorLayer, **kw):
        # assumed start() is called once # TODO: check if it is running
        if vlayer is None:
            raise InvalidQgsLayerError()
        self.conn_info = copy.deepcopy(conn_info) # upload
        self.kw = kw        
        ChainController.start(self, vlayer)
    def _config(self):
        self.config_fun([
            AsyncFun( layer_utils.get_feat_iter),
            WorkerFun( layer_utils.get_feat_upload_from_iter_args, self.pool),
            AsyncFun( self._setup_queue), 
        ])
    def _setup_queue(self, lst_added_feat: list, *a):
        if len(lst_added_feat) == 0:
            self.signal.finished.emit()
        self.lst_added_feat = queue.SimpleQueue(lst_added_feat)
        return make_qt_args(self.get_conn_info(), self.lst_added_feat, **self.kw)
    def get_conn_info(self):
        return self.conn_info
        
class UploadLayerController(BaseLoop):
    """ Upload the list of features of the input layer (added and removed) to the destination space (conn_info)
    Stateful controller
    """
    def __init__(self, network: NetManager, n_parallel=1):
        BaseLoop.__init__(self)
        self.n_parallel = n_parallel
        self.pool = QThreadPool() # .globalInstance() will crash afterward
        self.feat_cnt = 0

        self.fixed_params: dict = None
        self.lst_added_feat: queue.ParamsQueue = None
        self._config(network)
    def _config(self, network: NetManager):
        self.config_fun([
            NetworkFun( network.add_features), 
            WorkerFun( net_handler.on_received, self.pool),
            AsyncFun( self._process),
        ])
    def _process(self, obj: Geojson, *a):
        self.feat_cnt += len(obj["features"])
    def get_feat_cnt(self):
        return self.feat_cnt
    def start(self, conn_info: SpaceConnectionInfo, lst_added_feat: queue.ParamsQueue, **kw):
        self.conn_info = conn_info
        self.lst_added_feat = lst_added_feat

        self.fixed_params = dict(addTags=kw["tags"]) if "tags" in kw else dict()

        if self.count_active() == 0:
            BaseLoop.reset(self)
        self.dispatch_parallel(n_parallel=self.n_parallel)
    def _run_loop(self):
        if self.status == self.STOPPED: 
            self._handle_error(ManualInterrupt())
            return 
        if not self.lst_added_feat.has_next():
            self._try_finish()
            return
            
        conn_info: dict = self.get_conn_info()
        feat: list = self.lst_added_feat.get_params()
        LoopController.start(self, conn_info, feat, **self.fixed_params)
    def get_conn_info(self):
        return self.conn_info
    def _emit_finish(self):
        BaseLoop._emit_finish(self)
        
        token, space_id = self.conn_info.get_xyz_space()
        title = self.conn_info.get_("title")
        tags = self.fixed_params.get("addTags","")
        msg = "Space: %s - %s. Tags: %s. Token: %s"%(title, space_id, tags, token)
        self.signal.results.emit( make_qt_args(msg))

    def _handle_error(self, err):
        self.signal.error.emit(err)

class EditSyncController(UploadLayerController):
    def start(self, conn_info: SpaceConnectionInfo, layer_cache: LayeredEditBuffer, lst_added_feat: list, removed_feat: list, **kw):
        self.conn_info = conn_info
        self.layer_cache = layer_cache
        self.lst_added_feat = queue.SimpleQueue(lst_added_feat)
        self.removed_feat = queue.SimpleQueue(removed_feat)
        self.fixed_params = dict(addTags=kw["tags"]) if "tags" in kw else dict()
        self.feat_cnt_del = 0
        if self.count_active() == 0:
            BaseLoop.reset(self)
        self.dispatch_parallel(n_parallel=self.n_parallel)
    def fn_sync_feature(self, network: NetManager) -> Callable:
        def sync_feature(conn_info: SpaceConnectionInfo, **kw):
            if "add" in kw:
                feat, params = kw["add"]
                return network.add_features(conn_info, feat, **params)
            elif "remove" in kw:
                feat = kw["remove"]
                return network.del_features(conn_info, feat)
        return sync_feature
    def _run_loop(self):
        if self.status == self.STOPPED: 
            self._handle_error(ManualInterrupt())
            return 
        
        conn_info = self.get_conn_info()
        if not self.lst_added_feat.has_next():
            if self.removed_feat.has_next():
                feat = self.removed_feat.get_params()
                self.feat_cnt_del += len(feat)
                LoopController.start(self, conn_info, remove=(feat))
            else:
                self._try_finish()
            return
            
        conn_info = self.get_conn_info()
        feat: list = self.lst_added_feat.get_params()
        LoopController.start(self, conn_info, add=(feat, self.fixed_params))
    def _config(self, network: NetManager):
        self.config_fun([
            NetworkFun( self.fn_sync_feature(network)), 
            WorkerFun( net_handler.on_received, self.pool),
            AsyncFun( self._process),
        ])
    def _process(self, obj: Geojson, *a):
        self.layer_cache.update_progress(obj)
        if not "features" in obj: return
        features = obj["features"]
        self.feat_cnt += len(features)
    def _emit_finish(self):
        BaseLoop._emit_finish(self)
        token, space_id = self.conn_info.get_xyz_space()
        title = self.conn_info.get_("title")
        tags = self.fixed_params.get("addTags","")
        msg = "added/modified: %s. removed: %s. "%(self.feat_cnt, self.feat_cnt_del)
        msg += "Space: %s - %s. Tags: %s. Token: %s"%(title, space_id, tags, token) 
        self.signal.results.emit( make_qt_args(msg))


##### unused

class EditAddController(UploadLayerController):
    def start(self, conn_info, lst_added_feat, removed_feat, **kw):
        self.conn_info = conn_info
        self.lst_added_feat = queue.SimpleQueue(lst_added_feat)
        self.removed_feat = removed_feat
        # self.fixed_params = dict(addTags=kw["tags"]) if "tags" in kw else dict()

        if self.count_active() == 0:
            BaseLoop.reset(self)
        self.dispatch_parallel(n_parallel=self.n_parallel)
    def _emit_finish(self):
        BaseLoop._emit_finish(self)
        
        self.signal.results.emit( make_qt_args(self.conn_info, self.removed_feat))

class EditRemoveController(ChainController):
    def __init__(self, network):
        super().__init__()
        self.pool = QThreadPool() # .globalInstance() will crash afterward
        self._config(network)
    def start(self, conn_info, removed_feat, **kw):
        if len(removed_feat) == 0:
            self.signal.finished.emit()
            self.signal.results.emit(make_qt_args())
            return
        super().start(conn_info, removed_feat)
        # fixed_params = dict(addTags=kw["tags"]) if "tags" in kw else dict()
        # super().start(conn_info, removed_feat, **fixed_params)
    def _config(self, network):
        self.config_fun([
            NetworkFun( network.del_features), 
            WorkerFun( net_handler.on_received, self.pool),
            # AsyncFun( self._process),
        ])
