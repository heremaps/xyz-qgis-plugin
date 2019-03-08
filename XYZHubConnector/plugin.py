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

from .gui.space_dialog import ConnectManageSpaceDialog, ManageSpaceDialog
from .gui.space_info_dialog import EditSpaceDialog, UploadNewSpaceDialog
from .gui.util_dialog import ConfirmDialog
from .gui.basemap_dialog import BaseMapDialog

from .models import SpaceConnectionInfo, TokenModel, GroupTokenModel
from .modules.controller import ChainController
from .modules.controller import AsyncFun, parse_qt_args, make_qt_args, make_fun_args
from .modules.controller.manager import ControllerManager

from .modules import loader
from .modules.space_loader import *
from .modules.refactor_loader import *

from .modules.layer.manager import LayerManager
from .modules.layer import bbox_utils

from .modules.network import NetManager

from .modules import basemap
from .modules.basemap.auth_manager import AuthManager

from .modules.common.error import format_traceback


PLUGIN_NAME = config.PLUGIN_NAME
TAG_PLUGIN = "XYZ Hub"

DEBUG = 1

from .modules.common.signal import make_print_qgis, close_print_qgis
print_qgis = make_print_qgis(TAG_PLUGIN,debug=True)


class XYZHubConnector(object):

    """base plugin"""

    def __init__(self, iface):
        """init"""
        import sys
        print(sys.version)
        self.iface = iface
        self.web_menu = "&XYZ Hub Connector"
        self.init_modules()
        self.obj = self

    def initGui(self):
        """startup"""

        parent = self.iface.mainWindow()

        ######## action, button

        icon = QIcon("%s/%s" % (config.PLUGIN_DIR,"images/xyz.png"))
        icon_bbox = QIcon("%s/%s" % (config.PLUGIN_DIR,"images/bbox.svg"))
        self.action_connect = QAction(icon, "New XYZ Hub Connection", parent)
        self.action_connect.setWhatsThis(
            QCoreApplication.translate(PLUGIN_NAME, "WhatsThis message" ))
        self.action_connect.setStatusTip(
            QCoreApplication.translate(PLUGIN_NAME, "status tip message" ))

        self.action_clear_cache = QAction("Clear cache", parent)
        self.action_upload = QAction("Upload to New XYZ Geospace", parent)
        self.action_basemap = QAction("Add HERE Map Tile", parent)


        self.action_magic_sync = QAction("Magic Sync (EXPERIMENTAL)", parent)
        self.action_manage = QAction("Manage XYZ Geospace (EXPERIMENTAL)", parent)
        self.action_edit = QAction("Edit/Delete XYZ Geospace (EXPERIMENTAL)", parent)

        if self.iface.activeLayer() is None:
            # self.action_upload.setEnabled(False)
            self.action_edit.setEnabled(False)
            self.action_magic_sync.setEnabled(False)

        # self.action_magic_sync.setVisible(False) # disable magic sync

        ######## CONNECT action, button

        self.action_connect.triggered.connect(self.open_connection_dialog)
        self.action_manage.triggered.connect(self.open_manage_dialog)
        self.action_edit.triggered.connect(self.open_edit_dialog)
        self.action_upload.triggered.connect(self.open_upload_dialog)
        self.action_magic_sync.triggered.connect(self.open_magic_sync_dialog)
        self.action_clear_cache.triggered.connect(self.open_clear_cache_dialog)
        self.action_basemap.triggered.connect(self.open_basemap_dialog)

        ######## Add the toolbar + button
        self.toolbar = self.iface.addToolBar(PLUGIN_NAME)
        self.toolbar.setObjectName("XYZ Hub Connector")

        tool_btn = QToolButton(self.toolbar)

        self.actions = [self.action_connect, self.action_upload, self.action_basemap, self.action_clear_cache] # , self.action_magic_sync, self.action_manage, self.action_edit
        for a in self.actions:
            tool_btn.addAction(a)
            self.iface.addPluginToWebMenu(self.web_menu, a)

        tool_btn.setDefaultAction(self.action_connect)
        tool_btn.setPopupMode(tool_btn.MenuButtonPopup)

        self.xyz_widget_action = self.toolbar.addWidget(tool_btn)

        self.action_help = None
        
        self.action_reload = QAction(icon_bbox, "Reload BBox", parent)
        self.action_reload.triggered.connect(self.layer_reload_bbox)
        self.action_reload.setVisible(False) # disable
        self.toolbar.addAction(self.action_reload)

        progress = QProgressBar()
        progress.setMinimum(0)
        progress.setMaximum(0)
        progress.reset()
        progress.hide()
        # progress = self.iface.statusBarIface().children()[2] # will be hidden by qgis
        self.iface.statusBarIface().addPermanentWidget(progress)
        self.pb = progress

    def init_modules(self):
        # util.init_module()

        # parent = self.iface.mainWindow()
        parent = QgsProject.instance()

        ######## Init xyz modules
        self.map_basemap_meta = basemap.load_default_xml()
        self.auth_manager = AuthManager(config.PLUGIN_DIR +"/auth.ini")
        
        self.token_model = GroupTokenModel(parent)
        # self.layer = LayerManager(parent, self.iface)

        self.network = NetManager(parent)
        
        self.con_man = ControllerManager()
        self.layer_man = LayerManager()

        ######## data flow
        self.conn_info = SpaceConnectionInfo()
        
        ######## token      
        print(config.PLUGIN_DIR)
        self.token_model.load_ini(config.PLUGIN_DIR +"/token.ini")

        ######## CALLBACK
        # self.iface.mapCanvas().extentsChanged.connect( self.debug_reload)
        # self.con_man.connect_ux( self.iface) # canvas ux
        # self.con_man.signal.canvas_span.connect( self.loader_reload_bbox)
        
        self.con_man.ld_pool.signal.progress.connect( self.cb_progress_busy) #, Qt.QueuedConnection
        self.con_man.ld_pool.signal.finished.connect( self.cb_progress_done)
        
        QgsProject.instance().layersWillBeRemoved["QStringList"].connect( self.layer_man.remove)
        QgsProject.instance().layersWillBeRemoved["QStringList"].connect( self.con_man.remove)

        # self.iface.currentLayerChanged.connect( self.cb_layer_selected) # UNCOMMENT

        if DEBUG:
            QgsApplication.messageLog().messageReceived.connect(print_qgis)

    def unload_modules(self):
        # self.con_man.disconnect_ux( self.iface)
        QgsProject.instance().layersWillBeRemoved["QStringList"].disconnect( self.layer_man.remove)
        QgsProject.instance().layersWillBeRemoved["QStringList"].disconnect( self.con_man.remove)

        # utils.disconnect_silent(self.iface.currentLayerChanged)

        # self.con_man.unload()
        # del self.con_man

        # self.iface.mapCanvas().extentsChanged.disconnect( self.debug_reload)

        close_print_qgis()
        pass
    def unload(self):
        """teardown"""
        self.unload_modules()
        # remove the plugin menu item and icon
        self.iface.removePluginWebMenu(self.web_menu, self.action_help)

        self.toolbar.clear() # remove action from custom toolbar (toolbar still exist)
        self.toolbar.deleteLater()

        for a in self.actions:
            self.iface.removePluginWebMenu(self.web_menu, a)


    ############### 
    # Callback
    ###############
    def cb_layer_selected(self, qlayer):
        flag_xyz = True if qlayer is not None and self.layer.is_xyz_supported_layer(qlayer) else False
        # disable magic sync
        # self.action_magic_sync.setEnabled(flag_xyz)
        flag_layer = True
        self.action_upload.setEnabled(flag_layer)
        self.action_edit.setEnabled(flag_layer)
        
    ############### 
    # Callback of action (main function)
    ###############
    def cb_success_msg(self, msg, info=""):
        self.iface.messageBar().pushMessage(
            msg, info,  
            Qgis.Success, 1
        )

    def make_cb_success(self, msg, info=""):
        def _cb_success_msg():
            txt = info
            self.cb_success_msg(msg, txt)
        return _cb_success_msg

    def cb_handle_error_msg(self, e):
        err = parse_exception_obj(e)
        if isinstance(err, ChainInterrupt):
            e0, idx = err.args[0:2]
            if isinstance(e0, net_handler.NetworkError):
                ok = self.show_net_err_dialog(e0)
                if ok: return
            elif isinstance(e0, loader.EmptyXYZSpaceError):
                ret = exec_warning_dialog("Warning","Requested query returns no features")
        self.show_err_msgbar(err)

    def show_net_err_dialog(self, err):
        assert isinstance(err, net_handler.NetworkError)
        reply_tag, status, reason, body = err.args[:4]
        if reply_tag in ["count"]: # too many error
            return 0
            
        msg = (
            "%s: %s\n"%(status,reason) + 
            "There was a problem connecting to the server"
        )
        if status == 403:
            msg += "\n\n" + "Please make sure that the token has WRITE permission"
        ret = exec_warning_dialog("Network Error",msg, body)
        return 1

    def show_err_msgbar(self, err):
        self.iface.messageBar().pushMessage(
            TAG_PLUGIN, repr(err),  
            Qgis.Warning, 5
        )
        msg = format_traceback(err)
        QgsMessageLog.logMessage( msg, TAG_PLUGIN, Qgis.Warning)

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
            print_qgis("show",pb)
        else:
            pb.hide()        
            print_qgis("hide")
            
    ############### 
    # Action (main function)
    ###############
    def load_bbox(self, con, args):
        bbox = bbox_utils.extend_to_bbox(bbox_utils.get_bounding_box(self.iface))
        a, kw = parse_qt_args(args)
        kw["bbox"] = bbox
        kw["limit"] = 1000
        con.start(*a, **kw)
    def layer_reload_bbox(self):
        con_bbox_reload = ReloadLayerController_bbox(self.network)
        self.con_man.add(con_bbox_reload)
        # con_bbox_reload.signal.finished.connect( self.refresh_canvas, Qt.QueuedConnection)
        con_bbox_reload.signal.finished.connect( self.make_cb_success("Bounding box loading finish") )
        con_bbox_reload.signal.error.connect( self.cb_handle_error_msg )

        # TODO: set/get params from vlayer
        layer_id = self.iface.activeLayer().id()
        layer = self.layer_man.get(layer_id)
        self.load_bbox(con_bbox_reload, make_qt_args(layer))

    # UNUSED
    def debug_reload(self):
        print("debug_reload")

    def refresh_canvas(self):
        self.iface.mapCanvas().refresh()
        # assert False # debug unload module

    def previous_canvas_extent(self):
        self.iface.mapCanvas().zoomToPreviousExtent()

    def open_clear_cache_dialog(self):
        parent = self.iface.mainWindow()
        dialog = ConfirmDialog(parent, "Delete cache will make loaded layer unusable !!")
        ret = dialog.exec_()
        if ret != dialog.Ok: return
        
        utils.clear_cache()

    def open_connection_dialog(self):
        parent = self.iface.mainWindow()
        dialog = ConnectManageSpaceDialog(parent)
        dialog.config(self.token_model, self.conn_info)

        ############ edit btn   

        con = EditSpaceController(self.network)
        self.con_man.add(con)
        con.signal.finished.connect( dialog.btn_use.clicked.emit )
        con.signal.error.connect( self.cb_handle_error_msg )
        dialog.signal_edit_space.connect( con.start_args)

        ############ delete btn        

        con = DeleteSpaceController(self.network)
        self.con_man.add(con)
        con.signal.results.connect( dialog.btn_use.clicked.emit )
        con.signal.error.connect( self.cb_handle_error_msg )
        dialog.signal_del_space.connect( con.start_args)

        ############ Use Token btn        
        
        con = LoadSpaceController(self.network)
        self.con_man.add(con)
        con.signal.results.connect( make_fun_args(dialog.cb_display_spaces) )
        con.signal.error.connect( self.cb_handle_error_msg )
        con.signal.error.connect( lambda e: dialog.cb_enable_token_ui() )
        con.signal.finished.connect( dialog.cb_enable_token_ui )
        dialog.signal_use_token.connect( con.start_args)

        ############ get statisitics        
        con = StatSpaceController(self.network)
        self.con_man.add(con)
        con.signal.results.connect( make_fun_args(dialog.cb_display_space_count) )
        con.signal.error.connect( self.cb_handle_error_msg )
        dialog.signal_space_count.connect( con.start_args)
        
        ############ TODO: bbox btn        

        ############ connect btn        
        con_load = loader.ReloadLayerController(self.network, n_parallel=2)
        self.con_man.add(con_load)
        # con_load.signal.finished.connect( self.refresh_canvas, Qt.QueuedConnection)
        con_load.signal.finished.connect( self.make_cb_success("Loading finish") )
        con_load.signal.error.connect( self.cb_handle_error_msg )

        dialog.signal_space_connect.connect( con_load.start_args)

        # con.signal.results.connect( self.layer_man.add_args) # IMPORTANT


        dialog.exec_()
        # self.startTime = time.time()

    def open_manage_dialog(self):
        pass

    def open_edit_dialog(self):
        pass

    def open_upload_dialog(self):
        vlayer = self.iface.activeLayer()
        parent = self.iface.mainWindow()
        dialog = UploadNewSpaceDialog(parent)
        dialog.config(self.token_model, self.network, vlayer)

        ############ Use Token btn
        con = LoadSpaceController(self.network)
        self.con_man.add(con)
        con.signal.results.connect( make_fun_args(dialog.cb_set_valid_token) ) # finished signal !?
        con.signal.error.connect( self.cb_handle_error_msg )
        con.signal.finished.connect( dialog.cb_enable_token_ui )
        dialog.signal_use_token.connect( con.start_args)


        con_upload = UploadLayerController(self.network, n_parallel=2)
        self.con_man.add(con_upload)
        con_upload.signal.finished.connect( self.make_cb_success("Uploading finish") )
        con_upload.signal.error.connect( self.cb_handle_error_msg )

        con = InitUploadLayerController(self.network)
        self.con_man.add(con)

        dialog.signal_upload_new_space.connect( con.start_args)
        con.signal.results.connect( con_upload.start_args)
        con.signal.error.connect( self.cb_handle_error_msg )

        dialog.exec_()

    def open_magic_sync_dialog(self):
        pass

    def open_basemap_dialog(self):
        parent = self.iface.mainWindow()
        auth = self.auth_manager.get_auth()
        dialog = BaseMapDialog(parent)
        dialog.config(self.map_basemap_meta, auth)
        dialog.signal_add_basemap.connect( self.add_basemap_layer)

        dialog.exec_()
    def add_basemap_layer(self, args):
        a, kw = parse_qt_args(args)
        meta, app_id, app_code = a
        self.auth_manager.save(app_id, app_code)
        basemap.add_basemap_layer( meta, app_id, app_code)
