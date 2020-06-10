# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.core import QgsVectorLayer
from qgis.PyQt.QtCore import Qt

from . import parser
from .layer_props import QProps
from .layer_utils import (get_feat_upload_from_iter, is_layer_committed,
                          is_xyz_supported_layer, make_xyz_id_map_from_src,
                          update_feat_non_null, get_conn_info_from_layer,
                          get_layer)

from ..common.signal import make_print_qgis
print_qgis = make_print_qgis("edit_buffer")


def make_cb_fun(fun, *a0, **kw0):
    def _fun(*a,**kw):
        a = list(a0) + list(a)
        kw.update(kw0)
        fun(*a,**kw)
    return _fun


class RollbackTracker(object):
    def __init__(self, undo_stack):
        self.is_rollback = False
        self.idx = 0
        self.idx0 = 0
        self.lst_delayed_fun = list()
        self.undo_stack = undo_stack
        self.cmd = None
        self.set_current_idx()
    def make_delayed_cb(self, fun, *a0, **kw0):
        # delayed exec required because stack index changed after command exec
        # but we required to get stack index before
        def _cache_fun(*a,**kw):
            a = list(a0) + list(a)
            kw.update(kw0)
            self.lst_delayed_fun.append([fun, a, kw])
        return _cache_fun
    def exec_delayed_fun(self):
        idx = self.undo_stack.index()
        self.is_rollback = (
            not self.is_new_cmd(idx) and
            self.is_relative_rollback(idx))
        self.idx = idx
        old_a = list()
        new_a = list()
        for i, (fun, a, kw) in enumerate(self.lst_delayed_fun):
            fun(*a,**kw)
            if i%2 == 0:
                old_a.append(a)
            else:
                new_a.append(a)
        self.lst_delayed_fun.clear()
        return old_a, new_a
    def is_rollback_mode(self):
        return self.is_rollback
    def is_new_cmd(self, idx):
        is_new = (idx == self.undo_stack.count() and self.cmd != self.undo_stack.command(idx-1))
        print_qgis("is_new", is_new)
        if is_new: 
            self.cache_top_cmd()
        return is_new
    def is_relative_rollback(self, i):
        idx0 = self.idx0
        old_idx, idx = self._get_idx(i)
        same_dir = (idx - old_idx) * (idx0 - old_idx) > 0
        return same_dir
    def _get_idx(self, idx):
        # invoked after command executed
        old_idx = self.idx
        # idx = self.get_layer(layer_id).undoStack().index() # same
        idx0 = self.idx0
        print_qgis("idx", old_idx, idx, idx0)
        return old_idx, idx
    def cache_top_cmd(self):
        self.cmd = self.undo_stack.command(self.undo_stack.count()-1)
    def set_current_idx(self):
        idx = self.undo_stack.index()
        self.idx0 = idx
        self.idx = idx
        self.cache_top_cmd()

class SyncProgress(object):
    def __init__(self):
        self.lst_added_obj = list()
        self.lst_removed_obj = list()

        self.added_ids = list()
        self.lst_removed_ids = list()
        self.lst_added_feat = list()
    def reset(self):
        self.__init__()
    def start(self, added_ids, lst_added_feat, lst_removed_ids):
        self.added_ids = added_ids
        self.lst_added_feat = lst_added_feat
        self.lst_removed_ids = lst_removed_ids
    def update(self, obj):
        if not "features" in obj: 
            self.lst_removed_obj.append(None)
        else:
            self.lst_added_obj.append(obj)
        # lst_id.append([ft.get(parser.XYZ_ID,None) for ft in obj["features"]])
    def is_valid_response(self):
        ok = (
            len(self.lst_added_feat) == len(self.lst_added_obj) and
            len(self.lst_removed_obj) == min(1, len(self.lst_removed_ids))
        )
        list(map(print_qgis,[
            "len(self.lst_added_feat) == len(self.lst_added_obj), %s == %s"%
            (len(self.lst_added_feat), len(self.lst_added_obj)),
            # self.lst_added_feat, self.lst_added_obj,
            "len(self.lst_removed_obj) == min(1, len(self.removed_ids)), %s == %s"%
            (len(self.lst_removed_obj), min(1, len(self.lst_removed_ids))),
            # self.removed_ids, self.lst_removed_obj,
        ]))
        return ok

    def iter_fid_ft(self):
        if not self.is_valid_response(): return
        fid_iter = iter(self.added_ids)
        # print_qgis(self.lst_added_feat, self.lst_added_obj)
        for o1, o2 in zip(self.lst_added_feat, self.lst_added_obj):
            if not (o2 is not None and "features" in o2): continue
            for ft in o2["features"]:
                fid = next(fid_iter, None)
                yield fid, ft

class LayeredEditBuffer(object):
    def __init__(self, layer_id, cb_enable_ui):
        self.rollback_tracker = RollbackTracker(get_layer(layer_id).undoStack())
        self.progress = SyncProgress()
        
        self.layer_id = layer_id
        self.added_ids = set()
        self.edit_ids = set()
        self.removed_ids = set()
        self.xyz_id_cache = dict()
        self.pre_commit = list()

        self._cb_enable_ui = cb_enable_ui

        self.make_delayed_cb = self.rollback_tracker.make_delayed_cb
    def get_conn_info(self):
        return get_conn_info_from_layer(self.layer_id)

    def cache_xyz_id(self):
        lst_fid = [fid for lst in self.get_ids() for fid in lst]
        return self.get_xyz_id_(lst_fid)

    def get_xyz_id_(self, lst_fid):
        def _get_cache_miss(cache_hit, lst):
            return list(set(lst).difference(cache_hit.keys()))
        def _get_cache_hit(cache, lst):
            return dict((k, cache[k]) for k in lst if k in cache)
        cache = dict()
        lst = lst_fid
        for fn in [
            lambda lst: _get_cache_hit(self.xyz_id_cache, lst),
            lambda lst: make_xyz_id_map_from_src(get_layer(self.layer_id), lst),
            lambda lst: make_xyz_id_map_from_src(get_layer(self.layer_id).dataProvider(), lst)
        ]:
            if len(lst) == 0: break
            cache_hit = fn(lst)
            lst = _get_cache_miss(cache_hit, lst)
            cache.update(cache_hit)
        self.xyz_id_cache.update(cache)
        print_qgis("xyz_id", len(lst_fid), len(cache))
        print_qgis(lst_fid, cache)
        return cache

    def get_layer_id(self):
        return self.layer_id
    def get_sync_feat(self):
        added_ids, removed_ids = self.get_ids()

        m = self.get_xyz_id_(added_ids)
        added_xyz_ids = list(map(m.get, added_ids))
        
        m = self.get_xyz_id_(removed_ids)
        removed_xyz_ids = [v for v in m.values() if v is not None]
        
        print_qgis("sync", len(added_ids), len(removed_ids))
        print_qgis(added_ids, removed_ids)

        vlayer = get_layer(self.layer_id)
        it = vlayer.getFeatures(added_ids)
        lst_added_feat, added_ids = get_feat_upload_from_iter(it, vlayer, lst_fid=added_ids, lst_xyz_id=added_xyz_ids)
        lst_removed_ids = parser.make_lst_removed_ids(removed_xyz_ids)

        self.progress.start(added_ids, lst_added_feat, lst_removed_ids)

        return lst_added_feat, lst_removed_ids
    def get_ids(self):
        # add must comes before edit (API response json)
        edit_ids = list(self.edit_ids - self.added_ids)
        added_ids = list(self.added_ids) + edit_ids
        removed_ids = list(self.removed_ids)
        return added_ids, removed_ids
    def is_empty(self):
        it1, it2 = self.get_ids()
        print_qgis("is_empty", len(it1) + len(it2))
        print_qgis(it1, it2)
        return not (len(it1) > 0 or len(it2) > 0)

    def reset(self):
        self.added_ids.clear()
        self.edit_ids.clear()
        self.removed_ids.clear()
        self.rollback_tracker.set_current_idx()
        self.progress.reset()
    def clear_xyz_id_cache(self):
        """ clear xyz_id_cache  

        xyz_id_cache enable user to implicit delete synced feature
        xyz_id_cache shall be kept even if commit
        
        xyz_id_cache reset iff changes are sync + commit right next each other
        e.g. sync, commit. or commit, sync
        """
        self.xyz_id_cache.clear()
        print_qgis("clear_xyz_id_cache")
        
    def cache_xyz_id_from_feat(self, fid, feat):
        xyz_id = feat.get(parser.XYZ_ID, None)
        print_qgis("sync update", fid, xyz_id)
        self.xyz_id_cache[fid] = xyz_id 
        # allow cache None to prevent trying to getFeature
        
    def update_synced_feat(self, fid, feat):
        vlayer = get_layer(self.layer_id)
        fields = vlayer.fields()
        ft = parser.xyz_json_to_feat(feat, fields)
        ft.setId(fid)
        update_feat_non_null(vlayer, ft)

    def _cache_added_id(self, feat_id):
        self._uncache_removed_id(feat_id)
        self.added_ids.add(feat_id)
    def _cache_removed_id(self, feat_id):
        self._uncache_added_id(feat_id)
        self._uncache_edit_id(feat_id)
        self.removed_ids.add(feat_id)
    def _cache_edit_id(self, feat_id):
        self._uncache_removed_id(feat_id)
        self.edit_ids.add(feat_id)
    def _uncache_edit_id(self, feat_id):
        ok = feat_id in self.edit_ids
        self.edit_ids.discard(feat_id)
        return ok
    def _uncache_removed_id(self, feat_id):
        ok = feat_id in self.removed_ids
        self.removed_ids.discard(feat_id)
        return ok
    def _uncache_added_id(self, feat_id):
        ok = feat_id in self.added_ids
        self.added_ids.discard(feat_id)
        return ok

    ### CALLBACK
    def cb_feat_added(self, feat_id, *a):
        if self.rollback_tracker.is_rollback_mode():
            print_qgis("add rollback", feat_id)
            self._uncache_removed_id(feat_id)
        else:
            print_qgis("add", feat_id)
            self._cache_added_id(feat_id)
        # self.enable_ui()
    def cb_feat_removed(self, feat_id, *a):
        if self.rollback_tracker.is_rollback_mode():
            print_qgis("rem rollback", feat_id)
            self._uncache_added_id(feat_id)
        else:
            print_qgis("rem", feat_id)
            self._cache_removed_id(feat_id)
        # self.enable_ui()
    def cb_attr_changed(self, feat_id, *a):
        if self.rollback_tracker.is_rollback_mode():
            print_qgis("edit rollback", feat_id)
            self._uncache_edit_id(feat_id)
        else:
            print_qgis("edit", feat_id)
            self._cache_edit_id(feat_id)
        # self.enable_ui()

    def cb_idx_changed(self, *a):
        old_a, new_a = self.rollback_tracker.exec_delayed_fun()
        self.cache_xyz_id()
        self.enable_ui()

        if len(self.pre_commit) == 0: return
        # handle idx changed caused by commit
        # map_a maps fid of precommit vlayer to fid of commited data provider.
        map_a = dict((a1[0],a2[0]) for a1, a2 in zip(old_a, new_a))
        print_qgis("old:new", map_a)
        lst_cache_id = self.pre_commit.pop()
        # print_qgis(added_ids, removed_ids)
        for a1, a2 in map_a.items():
            # if a1 in self.xyz_id_cache:
            #     self.xyz_id_cache[a2] = self.xyz_id_cache.pop(a1)
            for cache in lst_cache_id:
                if a1 in cache:
                    cache.remove(a1)
                    cache.add(a2)
        # print_qgis(added_ids, removed_ids)
        self.added_ids, self.edit_ids, self.removed_ids = lst_cache_id

        # condition: sync, commit
        if sum(map(len,lst_cache_id)) == 0:
            self.clear_xyz_id_cache()
            
        self.enable_ui()

    def update_xyz_id_added_from_cache(self):
        added_ids, _ = self.get_ids()
        added_xyz_ids = dict((k, self.xyz_id_cache[k]) for k in added_ids if k in self.xyz_id_cache)
        print_qgis("update precommit", added_xyz_ids.keys())
        for fid, xyz_id in added_xyz_ids.items():
            feat = {"type":"Feature", parser.XYZ_ID:xyz_id}
            self.update_synced_feat(fid, feat)
        # disable rollback_tracker
            
    def cb_pre_commit(self):
        self.update_xyz_id_added_from_cache()
        
        print_qgis("pre_commit should happen before idx")
        self.pre_commit.append([
            set(self.added_ids),
            set(self.edit_ids),
            set(self.removed_ids),
            ])
            
    def enable_ui(self):
        flag = not self.is_empty()
        return self._cb_enable_ui(flag)
        
    def sync_complete(self):
        try:
            vlayer=get_layer(self.layer_id)
            lst_fid_ft = list(self.progress.iter_fid_ft())
            if len(lst_fid_ft) > 0 and not is_layer_committed(vlayer):
                vlayer.beginEditCommand("Changes pushed to XYZ Hub")
                for fid, ft in lst_fid_ft:
                    self.cache_xyz_id_from_feat(fid, ft)
                    self.update_synced_feat(fid, ft)
                vlayer.endEditCommand()
            else: 
                for fid, ft in lst_fid_ft:
                    self.cache_xyz_id_from_feat(fid, ft)
                    self.update_synced_feat(fid, ft)
            
            if is_layer_committed(vlayer):
                self.clear_xyz_id_cache()
        finally:
            self.reset()
            self.enable_ui()

    def update_progress(self, obj):
        self.progress.update(obj)

    ### Signal
    def config_connection(self, callback_pairs):
        self.callback_pairs = callback_pairs
        for signal, callback in self.callback_pairs:
            signal.connect(callback) #Qt.QueuedConnection # error connect failed between geometryChanged and unislot 
        
    def unload_connection(self):
        for signal, callback in self.callback_pairs:
            signal.disconnect(callback)

class EditBuffer(object):
    def __init__(self):
        self.layer_buffer=dict()
    def reset(self):
        self.layer_buffer = dict()
    def get_layer_buffer(self, layer_id) -> LayeredEditBuffer:
        return self.layer_buffer.get(layer_id, None)
    def remove_layers(self, lst_layer_id):
        for layer_id in lst_layer_id:
            self.layer_buffer.pop(layer_id, None)
    def config_ui(self, cb):
        self._cb_enable_ui = cb
    def enable_ui(self, layer_id):
        layer_buffer = self.get_layer_buffer(layer_id)
        if layer_buffer is None: return
        return layer_buffer.enable_ui()
    def config_connection(self, lst_vlayer):
        
        for vlayer in lst_vlayer:
            if not (isinstance(vlayer, QgsVectorLayer) and is_xyz_supported_layer(vlayer)): continue
            layer_id = vlayer.id()
            if layer_id in self.layer_buffer: continue

            layer_cache = LayeredEditBuffer(layer_id,
                cb_enable_ui=self._cb_enable_ui)
            self.layer_buffer[layer_id] = layer_cache
            layer_cache.config_connection(
                self.make_connection_pair(vlayer, layer_cache)
            )

    def unload_connection(self):
        for c in self.layer_buffer.values():
            c.unload_connection()
            
    def make_connection_pair(self, vlayer, layer_cache):
        cb_feat_added = layer_cache.make_delayed_cb(layer_cache.cb_feat_added)
        cb_attr_change = layer_cache.make_delayed_cb(layer_cache.cb_attr_changed)
        cb_feat_removed = layer_cache.make_delayed_cb(layer_cache.cb_feat_removed)
        # cb_rollback_start = make_cb_fun(self.map_rollback.__setitem__, True)
        # cb_rollback_end = make_cb_fun(self.map_rollback.__setitem__, False)
        cb_idx_changed = make_cb_fun(layer_cache.cb_idx_changed)
        cb_pre_commit = make_cb_fun(layer_cache.cb_pre_commit)
        return [
            ( vlayer.attributeValueChanged, cb_attr_change),
            ( vlayer.geometryChanged, cb_attr_change),
            ( vlayer.featureAdded, cb_feat_added),
            # ( vlayer.featuresDeleted, cb_feat_removed),
            ( vlayer.featureDeleted, cb_feat_removed),
            # ( vlayer.beforeRollBack, cb_rollback_start),
            # ( vlayer.afterRollBack, cb_rollback_end),
            ( vlayer.beforeCommitChanges, cb_pre_commit),
            ( vlayer.undoStack().indexChanged, cb_idx_changed), # command shall be executed stack index changed
            # ( vlayer.editCommandEnded, cb_idx_changed), # handle delete muttiple features case 
        ]
