# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

class QProps():
    LAYER_META = "XYZHub/meta"
    UNIQUE_ID = "XYZHub/id"
    CONN_INFO = "XYZHub/conn"
    TAGS = "XYZHub/tags" # included in params
    LOADER_PARAMS = "XYZHub/loader"
    EDIT_FLAG = "XYZHub/edit"
    PLUGIN_VERSION = "XYZHub/version"

    v0 = {
        LAYER_META : "xyz-hub",
        UNIQUE_ID : "xyz-hub-id",
        CONN_INFO : "xyz-hub-conn",
        TAGS : "xyz-hub-tags",
        LOADER_PARAMS : "xyz-hub-loader",
        EDIT_FLAG : "xyz-hub-edit"
    }
    
    @staticmethod
    def getProperty(qnode,key):
        val = qnode.customProperty(key)
        return val
        
    @classmethod
    def updatePropsVersion(cls,qnode):
        cls._removeProperty(qnode, cls.EDIT_FLAG) # deprecated props
        for key in cls.v0.keys():
            cls._getOldProperty(qnode, key)

    @classmethod
    def _getOldProperty(cls,qnode,key):
        val = None
        for version, backward_mapping in reversed(list(enumerate([
            cls.v0, # v1, v2
        ]))):
            oldKey = backward_mapping[key]
            oldValue = qnode.customProperty(oldKey)
            if oldValue is None: continue

            if val is None:
                val = cls.translateValue(oldValue, version)
                qnode.setCustomProperty(key, val)
            qnode.removeCustomProperty(oldKey)

        return val

    @classmethod
    def translateValue(cls, oldValue, version):
        return oldValue

    @classmethod
    def _removeProperty(cls,qnode,key):
        qnode.removeCustomProperty(key)
        for version, mapping in reversed(list(enumerate([
            cls.v0, # v1, v2
        ]))):
            oldKey = mapping[key]
            qnode.removeCustomProperty(oldKey)
