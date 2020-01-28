# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import logging
import time

from qgis.core import QgsProject, QgsApplication
from qgis.core import Qgis, QgsMessageLog

from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QToolButton, QWidgetAction
from qgis.PyQt.QtWidgets import QProgressBar, QSizePolicy

from . import config
from . import utils

from .gui.space_dialog import MainDialog
from .gui.space_info_dialog import EditSpaceDialog
from .gui.util_dialog import ConfirmDialog, exec_warning_dialog

from .models import SpaceConnectionInfo, TokenModel, GroupTokenInfoModel, EditableGroupTokenInfoModel, LOADING_MODES
from .modules.controller import ChainController
from .modules.controller import AsyncFun, parse_qt_args, make_qt_args, make_fun_args, parse_exception_obj, ChainInterrupt
from .modules.loader import (LoaderManager, EmptyXYZSpaceError, InitUploadLayerController, 
    LoadLayerController, UploadLayerController, EditSyncController,
    TileLayerLoader, LiveTileLayerLoader)

from .modules.layer.edit_buffer import EditBuffer
from .modules.layer import bbox_utils
from .modules.layer.layer_utils import (is_xyz_supported_layer, get_feat_upload_from_iter,
    is_xyz_supported_node, get_customProperty_str, iter_group_node, updated_xyz_node)
    
from .modules.layer import tile_utils, XYZLayer
from .modules.layer.layer_props import QProps


from .modules.network import NetManager, net_handler

from .modules import basemap
from .modules.common.secret import Secret
from .modules.basemap.auth_manager import AuthManager

from .modules.common.error import format_traceback

PLUGIN_NAME = config.PLUGIN_NAME

LOG_TO_FILE = 1

from .modules.common.signal import (make_print_qgis, cb_log_qgis, 
    connect_global_error_signal, disconnect_global_error_signal)
print_qgis = make_print_qgis("plugin")

class XYZHubConnector(object):

    """base plugin"""

    def __init__(self, iface):
        """init"""
        import sys
        print(sys.version)
        self.iface = iface
        self.web_menu = "&XYZ Hub Connector"
        self.hasGuiInitialized = False
        self.init_modules()
        self.obj = self

    def initGui(self):
        """startup"""

        parent = self.iface.mainWindow()

        ######## action, button

        icon = QIcon("%s/%s" % (config.PLUGIN_DIR,"images/xyz.png"))
        icon_bbox = QIcon("%s/%s" % (config.PLUGIN_DIR,"images/bbox.svg"))
        self.action_connect = QAction(icon, "XYZ Hub Connection", parent)
        self.action_connect.setWhatsThis(
            QCoreApplication.translate(PLUGIN_NAME, "WhatsThis message" ))
        self.action_connect.setStatusTip(
            QCoreApplication.translate(PLUGIN_NAME, "status tip message" ))

        self.action_sync_edit = QAction( QIcon("%s/%s" % (config.PLUGIN_DIR,"images/sync.svg")), "Push changes to XYZ Hub", parent)

        self.action_clear_cache = QAction( QIcon("%s/%s" % (config.PLUGIN_DIR,"images/delete.svg")), "Clear cache", parent)

        # self.action_sync_edit.setVisible(False) # disable magic sync
        self.edit_buffer.config_ui(self.enable_sync_btn)
        
        self.cb_layer_selected(self.iface.activeLayer())

        ######## CONNECT action, button

        self.action_connect.triggered.connect(self.open_connection_dialog)
        self.action_sync_edit.triggered.connect(self.open_sync_edit_dialog)
        self.action_clear_cache.triggered.connect( self.open_clear_cache_dialog)

        ######## Add the toolbar + button
        self.toolbar = self.iface.addToolBar(PLUGIN_NAME)
        self.toolbar.setObjectName("XYZ Hub Connector")

        self.actions_menu = [self.action_connect, self.action_sync_edit, self.action_clear_cache] 

        for a in [self.action_connect, self.action_sync_edit]:
            self.toolbar.addAction(a)

        for a in self.actions_menu:
            self.iface.addPluginToWebMenu(self.web_menu, a)

        # # uncomment to use menu button
        # tool_btn = QToolButton(self.toolbar)
        # tool_btn.setDefaultAction(self.action_connect)
        # tool_btn.setPopupMode(tool_btn.MenuButtonPopup)
        # self.xyz_widget_action = self.toolbar.addWidget(tool_btn) # uncomment to use menu button

        # self.toolbar.addAction(self.action_connect)

        self.action_help = None

        progress = QProgressBar()
        progress.setMinimum(0)
        progress.setMaximum(0)
        progress.reset()
        progress.hide()
        # progress = self.iface.statusBarIface().children()[2] # will be hidden by qgis
        self.iface.statusBarIface().addPermanentWidget(progress)
        self.pb = progress
        self.hasGuiInitialized = True

    def new_session(self):
        self.con_man.reset()
        self.edit_buffer.reset()
        
        if self.hasGuiInitialized:
            self.pb.hide()

    def init_modules(self):
        if LOG_TO_FILE:
            QgsApplication.messageLog().messageReceived.connect(cb_log_qgis) #, Qt.QueuedConnection
        connect_global_error_signal(self.log_err_traceback)

        # util.init_module()

        # parent = self.iface.mainWindow()
        parent = QgsProject.instance()

        self.secret = Secret(config.USER_PLUGIN_DIR +"/secret.ini")
        ######## Init xyz modules
        self.map_basemap_meta = basemap.load_default_xml()
        self.auth_manager = AuthManager(config.USER_PLUGIN_DIR +"/auth.ini")
        
        self.token_model = EditableGroupTokenInfoModel(parent)  #GroupTokenInfoModel

        self.network = NetManager(parent)
        
        self.con_man = LoaderManager()
        self.con_man.config(self.network)
        self.edit_buffer = EditBuffer()
        ######## data flow
        # self.conn_info = SpaceConnectionInfo()
        
        ######## token      
        self.token_model.load_ini(config.USER_PLUGIN_DIR +"/token.ini")

        ######## CALLBACK
        
        self.con_man.ld_pool.signal.progress.connect( self.cb_progress_busy) #, Qt.QueuedConnection
        self.con_man.ld_pool.signal.finished.connect( self.cb_progress_done)
        
        QgsProject.instance().cleared.connect(self.new_session)
        QgsProject.instance().layersWillBeRemoved["QStringList"].connect( self.edit_buffer.remove_layers)
        # QgsProject.instance().layersWillBeRemoved["QStringList"].connect( self.layer_man.remove_layers)

        # QgsProject.instance().layersAdded.connect( self.edit_buffer.config_connection)

        self.iface.currentLayerChanged.connect( self.cb_layer_selected) # UNCOMMENT

        canvas = self.iface.mapCanvas()
        self.lastRect = bbox_utils.extent_to_rect(bbox_utils.get_bounding_box(canvas))
        self.iface.mapCanvas().extentsChanged.connect( self.reload_tile, Qt.QueuedConnection)


        QgsProject.instance().readProject.connect( self.import_project)
        self.import_project()

    def unload_modules(self):
        # self.con_man.disconnect_ux( self.iface)
        QgsProject.instance().cleared.disconnect(self.new_session)
        QgsProject.instance().layersWillBeRemoved["QStringList"].disconnect( self.edit_buffer.remove_layers)
        # QgsProject.instance().layersWillBeRemoved["QStringList"].disconnect( self.layer_man.remove_layers)

        # QgsProject.instance().layersAdded.disconnect( self.edit_buffer.config_connection)
        self.edit_buffer.unload_connection()

        self.iface.currentLayerChanged.disconnect( self.cb_layer_selected) # UNCOMMENT

        self.iface.mapCanvas().extentsChanged.disconnect( self.reload_tile)
        
        QgsProject.instance().readProject.disconnect( self.import_project)
        
        # utils.disconnect_silent(self.iface.currentLayerChanged)

        self.secret.deactivate()
        
        disconnect_global_error_signal()
        if LOG_TO_FILE:
            QgsApplication.messageLog().messageReceived.disconnect(cb_log_qgis)
        # close_file_logger()
        pass
    def unload(self):
        """teardown"""
        self.unload_modules()
        # remove the plugin menu item and icon
        self.iface.removePluginWebMenu(self.web_menu, self.action_help)

        self.toolbar.clear() # remove action from custom toolbar (toolbar still exist)
        self.toolbar.deleteLater()

        for a in self.actions_menu:
            self.iface.removePluginWebMenu(self.web_menu, a)
        # remove progress
        self.iface.statusBarIface().removeWidget(self.pb)

    ############### 
    # Callback
    ###############
    def cb_layer_selected(self, qlayer):
        flag_xyz = True if qlayer is not None and is_xyz_supported_layer(qlayer) else False
        if flag_xyz: 
            self.edit_buffer.config_connection([qlayer])
            self.edit_buffer.enable_ui(qlayer.id())
        else:
            msg = "No XYZHub Layer selected"
            self.enable_sync_btn(False, msg)
        # disable magic sync
        # self.action_sync_edit.setEnabled(flag_xyz)
    def enable_sync_btn(self, flag, msg=""):
        msg = msg or ("No changes detected since last push" if not flag else "Push changes")
        self.action_sync_edit.setToolTip(msg)
        self.action_sync_edit.setEnabled(flag)
        
    ############### 
    # Callback of action (main function)
    ###############
    def cb_success_msg(self, title, msg="", dt=5):
        self.iface.messageBar().pushMessage(
            config.TAG_PLUGIN, ": ".join([title,msg]),
            Qgis.Success, dt
        )

    def make_cb_success(self, title, msg="", dt=5):
        def _cb_success_msg():
            self.cb_success_msg(title, msg, dt=dt)
        return _cb_success_msg
        
    def make_cb_success_args(self, title, msg="", dt=5):
        def _cb_success_msg(args):
            a, kw = parse_qt_args(args)
            txt = ". ".join(map(str,a))
            self.cb_success_msg(title, txt, dt=dt)
        return _cb_success_msg

    def cb_handle_error_msg(self, e):
        err = parse_exception_obj(e)
        if isinstance(err, ChainInterrupt):
            e0, idx = err.args[0:2]
        else:
            e0 = err
        if isinstance(e0, (net_handler.NetworkError, net_handler.NetworkTimeout)):
            ok = self.show_net_err(e0)
            if ok: return
        elif isinstance(e0, EmptyXYZSpaceError):
            ret = exec_warning_dialog("XYZ Hub","Requested query returns no features")
            return
        self.show_err_msgbar(err)

    def show_net_err(self, err):
        reply_tag, status, reason, body, err_str, url = err.args[:6]
        if reply_tag in ["count", "statistics"]: # too many error
            # msg = "Network Error: %s: %s. %s"%(status, reason, err_str)
            return 1
            
        detail = "\n". join(["Request:", url,"","Response:", body])
        msg = (
            "%s: %s\n"%(status,reason) + 
            "There was a problem connecting to the server"
        )
        if status in [401,403]:
            msg += ("\n\n" + "Please input valid token with correct permissions." + "\n" +
            "Token is generated via " +
            "<a href='https://xyz.api.here.com/token-ui/'>https://xyz.api.here.com/token-ui/</a>")
        ret = exec_warning_dialog("Network Error",msg, detail)
        return 1

    def show_err_msgbar(self, err):
        self.iface.messageBar().pushMessage(
            "Error", repr(err),
            Qgis.Warning, 3
        )
        self.log_err_traceback(err)

    def log_err_traceback(self, err):
        msg = format_traceback(err)
        QgsMessageLog.logMessage( msg, config.TAG_PLUGIN, Qgis.Warning)

    def cb_progress_busy(self, n_active):
        if n_active > 1: return
        self.flag_pb_show=True
        self.cb_progress_refresh()

    def cb_progress_done(self):
        self.flag_pb_show=False
        self.cb_progress_refresh()

    def cb_progress_refresh(self):
        if not hasattr(self,"flag_pb_show"): return

        pb = self.pb
        if self.flag_pb_show:
            pb.show()
            # print_qgis("show",pb)
        else:
            pb.hide()        
            # print_qgis("hide")
            
    ############### 
    # Action (main function)
    ###############

    # UNUSED
    def refresh_canvas(self):
        # self.iface.activeLayer().triggerRepaint()
        self.iface.mapCanvas().refresh()
    def previous_canvas_extent(self):
        self.iface.mapCanvas().zoomToPreviousExtent()
    #
    
    def new_main_dialog(self):
        parent = self.iface.mainWindow()
        dialog = MainDialog(parent)

        dialog.config(self.token_model)
        dialog.config_secret(self.secret)
        auth = self.auth_manager.get_auth()
        dialog.config_basemap(self.map_basemap_meta, auth)

        con = self.con_man.make_con("create")
        con.signal.finished.connect( dialog.btn_use.clicked.emit ) # can be optimized !!
        con.signal.error.connect( self.cb_handle_error_msg )

        con = self.con_man.make_con("list")
        con.signal.results.connect( make_fun_args(dialog.cb_display_spaces) )
        con.signal.error.connect( self.cb_handle_error_msg )
        con.signal.error.connect( lambda e: dialog.cb_enable_token_ui() )
        con.signal.finished.connect( dialog.cb_enable_token_ui )
        con.signal.finished.connect( dialog.ui_valid_token )

        con = self.con_man.make_con("edit")
        con.signal.finished.connect( dialog.btn_use.clicked.emit )
        con.signal.error.connect( self.cb_handle_error_msg )

        con = self.con_man.make_con("delete")
        con.signal.results.connect( dialog.btn_use.clicked.emit )
        con.signal.error.connect( self.cb_handle_error_msg )

        con = self.con_man.make_con("stat")
        con.signal.results.connect( make_fun_args(dialog.cb_display_space_count) )
        con.signal.error.connect( self.cb_handle_error_msg )

        ############ clear cache btn
        dialog.signal_clear_cache.connect( self.open_clear_cache_dialog)
        
        ############ add map tile btn
        dialog.signal_add_basemap.connect( self.add_basemap_layer)
        
        ############ btn: new, edit, delete space   
        dialog.signal_new_space.connect(self.start_new_space)
        dialog.signal_edit_space.connect(self.start_edit_space)
        dialog.signal_del_space.connect(self.start_delete_space)

        ############ Use Token btn        
        dialog.signal_use_token.connect( lambda a: self.con_man.finish_fast())
        dialog.signal_use_token.connect(self.start_use_token)

        ############ get count        
        dialog.signal_space_count.connect(self.start_count_feat, Qt.QueuedConnection) # queued -> non-blocking ui

        ############ connect btn        
        # dialog.signal_space_connect.connect(self.start_load_layer)
        dialog.signal_space_connect.connect(self.start_loading)
        dialog.signal_space_tile.connect(self.start_load_tile)

        ############ upload btn        
        dialog.signal_upload_space.connect(self.start_upload_space)
        
        return dialog
    def start_new_space(self, args):
        con = self.con_man.get_con("create")
        con.start_args(args)

    def start_edit_space(self, args):
        con = self.con_man.get_con("edit")
        con.start_args(args)

    def start_delete_space(self, args):
        con = self.con_man.get_con("delete")
        con.start_args(args)

    def start_use_token(self, args):
        con = self.con_man.get_con("list")
        con.start_args(args)

    def start_count_feat(self, args):
        con = self.con_man.get_con("stat")
        con.start_args(args)

    def start_upload_space(self, args):
        con_upload = UploadLayerController(self.network, n_parallel=2)
        self.con_man.add_background(con_upload)
        # con_upload.signal.finished.connect( self.make_cb_success("Uploading finish") )
        con_upload.signal.results.connect( self.make_cb_success_args("Uploading finish") )
        con_upload.signal.error.connect( self.cb_handle_error_msg )
        
        con = InitUploadLayerController(self.network)
        self.con_man.add_background(con)

        con.signal.results.connect( con_upload.start_args)
        con.signal.error.connect( self.cb_handle_error_msg )

        con.start_args(args)
    def start_load_layer(self, args):
        # create new con
        # config
        # run
        
        ############ connect btn        
        con_load = LoadLayerController(self.network, n_parallel=1)
        self.con_man.add_background(con_load)
        # con_load.signal.finished.connect( self.make_cb_success("Loading finish") )
        con_load.signal.results.connect( self.make_cb_success_args("Loading finish") )
        # con_load.signal.finished.connect( self.refresh_canvas, Qt.QueuedConnection)
        con_load.signal.error.connect( self.cb_handle_error_msg )

        con_load.start_args(args)

        # con.signal.results.connect( self.layer_man.add_args) # IMPORTANT
    def start_load_tile(self, args):
        # rect = (-180,-90,180,90)
        # level = 0
        a, kw = parse_qt_args(args)
        kw.update(self.make_tile_params())
        # kw["limit"] = 100

        ############ connect btn        
        con_load = TileLayerLoader(self.network, n_parallel=1)
        self.con_man.add_layer(con_load)
        # con_load.signal.finished.connect( self.make_cb_success("Tiles loaded") )
        con_load.signal.results.connect( self.make_cb_success_args("Tiles loaded", dt=2) )
        # con_load.signal.finished.connect( self.refresh_canvas, Qt.QueuedConnection)
        con_load.signal.error.connect( self.cb_handle_error_msg )

        con_load.start_args( make_qt_args(*a, **kw))

    def make_tile_params(self, rect=None, level=None):
        if not rect:
            canvas = self.iface.mapCanvas()
            rect = bbox_utils.extent_to_rect(
                bbox_utils.get_bounding_box(canvas))
            level = tile_utils.get_zoom_for_current_map_scale(canvas)
        kw = dict()
        kw["tile_schema"] = "here"
        kw["tile_ids"] = tile_utils.bboxToListColRow(*rect,level)
        return kw

    def start_loading(self, args):
        a, kw = parse_qt_args(args)
        loading_mode = kw.get("loading_mode")
        try:
            con_load = self.make_loader_from_mode(loading_mode)
        except Exception as e:
            self.show_err_msgbar(e)
            return

        if loading_mode == LOADING_MODES.SINGLE:
            con_load.start_args(args)
        else:
            kw.update(self.make_tile_params())
            con_load.start_args( make_qt_args(*a, **kw))


    def iter_checked_xyz_subnode(self):
        """ iterate through visible xyz nodes (vector layer and group node),
        excluding layer in edit mode
        """
        root = QgsProject.instance().layerTreeRoot()
        for vl in root.checkedLayers():
            if is_xyz_supported_layer(vl):
                if vl.isEditable(): continue
                yield vl
        for g in iter_group_node(root):
            if (len(g.findLayers()) == 0 
                and g.isVisible()
                and is_xyz_supported_node(g)):
                yield g

    def iter_all_xyz_node(self):
        """ iterate through xyz group nodes
        """
        for qnode in self._iter_all_xyz_node():
            yield qnode

    def iter_update_all_xyz_node(self):
        """ iterate through xyz group nodes, with meta version check and updated.
        """
        for qnode in self._iter_all_xyz_node(fn_node=updated_xyz_node):
            yield qnode

    def _iter_all_xyz_node(self, fn_node=lambda a: None):
        """ iterate through xyz group nodes, with custom function fn_node applied to every node
        """
        root = QgsProject.instance().layerTreeRoot()
        for g in iter_group_node(root):
            fn_node(g)
            if is_xyz_supported_node(g):
                yield g
    
    def extent_action(self, rect0, rect1):
        diff = [r0 - r1 for r0,r1 in zip(rect0,rect1)]
        x_sign = diff[0] * diff[2]
        y_sign = diff[1] * diff[3]
        if x_sign >= 0 and y_sign >= 0: # same direction
            return "pan"
        elif x_sign < 0 and y_sign < 0:
            return "zoom"
        elif x_sign * y_sign == 0 and x_sign + y_sign < 0:
            return "resize"
        else:
            return "unknown"

    def reload_tile(self):
        canvas = self.iface.mapCanvas()
        rect = bbox_utils.extent_to_rect(bbox_utils.get_bounding_box(canvas))
        ext_action = self.extent_action(rect,self.lastRect)
        print_qgis("Extent action: ", ext_action,rect)
        self.lastRect = rect
        if ext_action not in ["pan", "zoom"]: 
            return
        level = tile_utils.get_zoom_for_current_map_scale(canvas)
        kw = self.make_tile_params(rect, level)
        # kw["limit"] = 100

        unique_con = set()
        lst_con = list()
        for qnode in self.iter_checked_xyz_subnode():
            xlayer_id = get_customProperty_str(qnode, QProps.UNIQUE_ID)
            con = self.con_man.get_from_xyz_layer(xlayer_id)
            if con is None: continue
            if con in unique_con: continue
            lst_con.append(con)
            unique_con.add(con)
        # print_qgis(lst_con)
        # print_qgis(self.con_man._layer_ptr)
                
        for con in lst_con:
            print_qgis(con.status)
            print_qgis("loading tile", level, rect)
            con.restart(**kw)

    def add_basemap_layer(self, args):
        a, kw = parse_qt_args(args)
        meta, app_id, app_code = a
        self.auth_manager.save(app_id, app_code)
        basemap.add_basemap_layer( meta, app_id, app_code)

    ############### 
    # import project function
    ###############

    def import_project(self):
        self.init_all_tile_loader()

    def make_loader_from_mode(self, loading_mode, layer=None):
        if not loading_mode:
            raise Exception("Invalid loading mode: %s"%str(loading_mode))
        option = dict(zip(LOADING_MODES, [
            (LiveTileLayerLoader, self.con_man.add_layer, self.make_cb_success_args("Tiles loaded", dt=2)),
            (TileLayerLoader, self.con_man.add_layer, self.make_cb_success_args("Tiles loaded", dt=2)),
            (LoadLayerController, self.con_man.add_background, self.make_cb_success_args("Loading finish"))
            ])).get(loading_mode)
        if not option:
            return

        loader_class, fn_register, cb_success_args = option
        con_load = loader_class(self.network, n_parallel=1, layer=layer)
        con_load.signal.results.connect( cb_success_args)
        con_load.signal.error.connect( self.cb_handle_error_msg )

        ptr = fn_register(con_load)
        return con_load


    def init_tile_loader(self, qnode):
        layer = XYZLayer.load_from_qnode(qnode)
        loading_mode = layer.loader_params.get("loading_mode")
        # backward-compatibility, import project
        if not loading_mode: 
            self.cb_success_msg("Import XYZ Layer", 
                "Undefined loading mode: %s, " % loading_mode +  
                "default to live loading (layer: %s)" % layer.get_name())
            loading_mode = LOADING_MODES.LIVE
        return self.make_loader_from_mode(loading_mode, layer=layer)

    def init_all_tile_loader(self):
        cnt = 0
        for qnode in self.iter_update_all_xyz_node():
            xlayer_id = get_customProperty_str(qnode, QProps.UNIQUE_ID)
            con = self.con_man.get_from_xyz_layer(xlayer_id)
            if con: continue
            try: 
                con = self.init_tile_loader(qnode)
                cnt += 1
            except Exception as e:
                self.show_err_msgbar(e)
                

        # print_qgis(self.con_man._layer_ptr)
        self.cb_success_msg("Import XYZ Layer", "%s XYZ Layer imported"%cnt, dt=2)

    ############### 
    # Open dialog
    ###############
    def open_clear_cache_dialog(self):
        dialog = ConfirmDialog("Delete cache will make loaded layer unusable !!")
        ret = dialog.exec_()
        if ret != dialog.Ok: return
        
        utils.clear_cache()

    def open_connection_dialog(self):
        dialog = self.new_main_dialog()
        
        vlayer = self.iface.activeLayer()
        dialog.set_layer( vlayer)
        
        dialog.exec_()
        self.con_man.finish_fast()
        # self.startTime = time.time()
    def open_sync_edit_dialog(self):
        vlayer = self.iface.activeLayer()
        layer_buffer = self.edit_buffer.get_layer_buffer(vlayer.id())

        lst_added_feat, removed_ids = layer_buffer.get_sync_feat()
        conn_info = layer_buffer.get_conn_info()

        # print_qgis("lst_added_feat: ",lst_added_feat)
        # print_qgis("removed_feat: ", removed_ids)

        con = EditSyncController(self.network)
        self.con_man.add_background(con)
        con.signal.finished.connect( layer_buffer.sync_complete)
        con.signal.results.connect( self.make_cb_success_args("Sync edit finish") )
        con.signal.error.connect( self.cb_handle_error_msg )

        con.start(conn_info, layer_buffer, lst_added_feat, removed_ids)

        # self.edit_buffer.reset(vlayer.id())
    