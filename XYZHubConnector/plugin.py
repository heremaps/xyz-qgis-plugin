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

from .models import SpaceConnectionInfo, TokenModel, GroupTokenModel
from .modules.controller import ChainController
from .modules.controller import AsyncFun, parse_qt_args, make_qt_args, make_fun_args, parse_exception_obj, ChainInterrupt
from .modules.loader import LoaderManager, EmptyXYZSpaceError, InitUploadLayerController, LoadLayerController, UploadLayerController

from .modules.layer.manager import LayerManager
from .modules.layer import bbox_utils

from .modules.network import NetManager, net_handler

from .modules import basemap
from .modules.common.secret import Secret
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
        self.action_connect = QAction(icon, "XYZ Hub Connection", parent)
        self.action_connect.setWhatsThis(
            QCoreApplication.translate(PLUGIN_NAME, "WhatsThis message" ))
        self.action_connect.setStatusTip(
            QCoreApplication.translate(PLUGIN_NAME, "status tip message" ))

        self.action_magic_sync = QAction("Magic Sync (EXPERIMENTAL)", parent)

        if self.iface.activeLayer() is None:
            self.action_magic_sync.setEnabled(False)

        # self.action_magic_sync.setVisible(False) # disable magic sync

        ######## CONNECT action, button

        self.action_connect.triggered.connect(self.open_connection_dialog)
        self.action_magic_sync.triggered.connect(self.open_magic_sync_dialog)

        ######## Add the toolbar + button
        self.toolbar = self.iface.addToolBar(PLUGIN_NAME)
        self.toolbar.setObjectName("XYZ Hub Connector")

        self.actions = [self.action_connect] 

        for a in self.actions:
            self.iface.addPluginToWebMenu(self.web_menu, a)

        # # uncomment to use menu button
        # tool_btn = QToolButton(self.toolbar)
        # for a in self.actions:
        #     tool_btn.addAction(a)
        # tool_btn.setDefaultAction(self.action_connect)
        # tool_btn.setPopupMode(tool_btn.MenuButtonPopup)
        # self.xyz_widget_action = self.toolbar.addWidget(tool_btn) # uncomment to use menu button

        self.toolbar.addAction(self.action_connect)

        self.action_help = None

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

        self.secret = Secret(config.USER_PLUGIN_DIR +"/secret.ini")
        ######## Init xyz modules
        self.map_basemap_meta = basemap.load_default_xml()
        self.auth_manager = AuthManager(config.USER_PLUGIN_DIR +"/auth.ini")
        
        self.token_model = GroupTokenModel(parent)
        # self.layer = LayerManager(parent, self.iface)

        self.network = NetManager(parent)
        
        self.con_man = LoaderManager()
        self.con_man.config(self.network)
        self.layer_man = LayerManager()

        ######## data flow
        # self.conn_info = SpaceConnectionInfo()
        
        ######## token      
        self.token_model.load_ini(config.USER_PLUGIN_DIR +"/token.ini")

        ######## CALLBACK
        
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

        # self.iface.mapCanvas().extentsChanged.disconnect( self.debug_reload)

        self.secret.deactivate()
        
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
        
    ############### 
    # Callback of action (main function)
    ###############
    def cb_success_msg(self, msg, info=""):
        self.iface.messageBar().pushMessage(
            msg, info,  
            Qgis.Success, 5
        )

    def make_cb_success(self, msg, info=""):
        def _cb_success_msg():
            txt = info
            self.cb_success_msg(msg, txt)
        return _cb_success_msg
        
    def make_cb_success_args(self, msg, info=""):
        def _cb_success_msg(args):
            a, kw = parse_qt_args(args)
            txt = ". ".join(map(str,a))
            self.cb_success_msg(msg, txt)
        return _cb_success_msg

    def cb_handle_error_msg(self, e):
        err = parse_exception_obj(e)
        if isinstance(err, ChainInterrupt):
            e0, idx = err.args[0:2]
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
        if status == 403:
            msg += "\n\n" + "Please make sure that the token has WRITE permission"
        ret = exec_warning_dialog("Network Error",msg, detail)
        return 1

    def show_err_msgbar(self, err):
        self.iface.messageBar().pushMessage(
            TAG_PLUGIN, repr(err),  
            Qgis.Warning, 3
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
    # unused
    def load_bbox(self, con, args):
        bbox = bbox_utils.extend_to_bbox(bbox_utils.get_bounding_box(self.iface))
        a, kw = parse_qt_args(args)
        kw["bbox"] = bbox
        kw["limit"] = 1000
        con.start(*a, **kw)

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
        dialog.signal_space_connect.connect(self.start_load_layer)

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
        
    def add_basemap_layer(self, args):
        a, kw = parse_qt_args(args)
        meta, app_id, app_code = a
        self.auth_manager.save(app_id, app_code)
        basemap.add_basemap_layer( meta, app_id, app_code)

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
    # not used
    def open_magic_sync_dialog(self):
        pass
    