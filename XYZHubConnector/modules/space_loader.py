# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.PyQt.QtCore import QThreadPool
from .controller import ChainController, NetworkFun, WorkerFun
from .network import net_handler

class LoadSpaceController(ChainController):
    """ load space metadata (list space)
    Args:
        conn_info: token
    """
    # Feature
    def __init__(self, network):
        super().__init__()
        self.pool = QThreadPool() # .globalInstance() will crash afterward
        self._config(network)
    def start(self, conn_info):
        super().start(conn_info)
    def _config(self, network):
        self.config_fun([
            NetworkFun( network.list_spaces), 
            WorkerFun( net_handler.on_received, self.pool),
        ])

class StatSpaceController(ChainController):
    """ get statistics of given space (count, byteSize, bbox)
    Args:
        conn_info: token
    """
    # Feature
    def __init__(self, network):
        super().__init__()
        self.pool = QThreadPool() # .globalInstance() will crash afterward
        self._config(network)
    def start(self, conn_info):
        super().start(conn_info)
    def _config(self, network):
        self.config_fun([
            # NetworkFun( network.get_statistics), 
            NetworkFun( network.get_count), 
            WorkerFun( net_handler.on_received, self.pool),
        ])

class DeleteSpaceController(ChainController):
    """ Delete space
    Args:
        conn_info: token + space_id
    """
    # Feature
    def __init__(self, network):
        super().__init__()
        self.pool = QThreadPool() # .globalInstance() will crash afterward
        self._config(network)
    def start(self, conn_info):
        super().start(conn_info)
    def _config(self, network):
        self.config_fun([
            NetworkFun( network.del_space), 
            WorkerFun( net_handler.on_received, self.pool),
        ])

class EditSpaceController(ChainController):
    """ Edit space metadata
    Args:
        conn_info: token + space_id
        meta: new metadata/space_info (title, description)
    """
    # Feature
    def __init__(self, network):
        super().__init__()
        self.pool = QThreadPool() # .globalInstance() will crash afterward
        self._config(network)
    def start(self, conn_info, meta):
        super().start(conn_info, meta)
    def _config(self, network):
        self.config_fun([
            NetworkFun( network.edit_space), 
            WorkerFun( net_handler.on_received, self.pool),
        ])

#UNUSED: CreateSpace is done implicilty in UploadLayer
class CreateSpaceController(ChainController):
    """ Create new space
    Args:
        conn_info: token + space_id
        meta: new metadata/space_info (title, description)
    """
    def __init__(self, network):
        super().__init__()
        self.pool = QThreadPool() # .globalInstance() will crash afterward
        self._config(network)
    def start(self, conn_info, meta):
        super().start(conn_info, meta)
    def _config(self, network):
        self.config_fun([
            NetworkFun( network.add_space), 
            WorkerFun( net_handler.on_received, self.pool),
        ])
