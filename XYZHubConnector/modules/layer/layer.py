# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os
import sqlite3

from qgis.core import (QgsCoordinateReferenceSystem, QgsFeatureRequest,
                       QgsProject, QgsVectorFileWriter, QgsVectorLayer, QgsCoordinateTransform)
from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.PyQt.QtXml import QDomDocument

from . import parser, render
from ...models.space_model import parse_copyright
from ...utils import make_unique_full_path
from .style import LAYER_QML

from ..common.signal import make_print_qgis
print_qgis = make_print_qgis("layer")



class XYZLayer(object):
    """ XYZ Layer is created in 2 scenarios:
    + loading a new layer from xyz
    + uploading a qgis layer to xyz, add conn_info, meta, vlayer
    """
    def __init__(self, conn_info, meta, tags="", ext="gpkg"):
        super().__init__()
        self.conn_info = conn_info
        self.meta = meta
        self.tags = tags
        self.ext = ext

        self.map_vlayer = dict()
        self._map_vlayer = dict()
        self.map_fields = dict()


        crs = QgsCoordinateReferenceSystem('EPSG:4326').toWkt()
        for geom in ["MultiPoint","MultiLineString","MultiPolygon",None]:
            self._init_ext_layer(geom, crs)

    def _save_meta(self, vlayer):
        meta = self.meta
        vlayer.setCustomProperty("xyz-hub", meta)
        vlayer.setCustomProperty("xyz-hub-tags", self.tags)
        lic = meta.get("license")
        cr = meta.get("copyright")

        meta = vlayer.metadata()
        if lic is not None:
            meta.setLicenses([lic])
        if isinstance(cr, list):
            lst_txt = parse_copyright(cr)
            meta.setRights(lst_txt)
        vlayer.setMetadata(meta)

    def is_valid(self, geom_str):
        return geom_str in self.map_vlayer
    def get_layer(self, geom_str):
        return self.map_vlayer.get(geom_str)
    def get_name(self):
        tags = " (%s)" %(self.tags) if len(self.tags) else ""
        return "{title} - {id}{tags}".format(tags=tags,**self.meta)
    def _layer_name(self, geom_str):
        tags = " (%s)" %(self.tags) if len(self.tags) else ""
        return "{title} - {id} - {geom}{tags}".format(geom=geom_str,tags=tags,**self.meta)
    def get_xyz_feat_id(self, geom_str):
        vlayer = self.get_layer(geom_str)
        key = parser.QGS_XYZ_ID
        req = QgsFeatureRequest().setFilterExpression(key+" is not null").setSubsetOfAttributes([key], vlayer.fields())
        return set([ft.attribute(key) for ft in vlayer.getFeatures(req)])
    def get_map_fields(self):
        return self.map_fields
    def get_feat_cnt(self):
        cnt = 0
        for vlayer in self.map_vlayer.values():
            cnt += vlayer.featureCount()
        return cnt
    def show_ext_layer(self, geom_str):
        vlayer = self._map_vlayer[geom_str]
        self.map_vlayer[geom_str] = vlayer

        dom = QDomDocument()
        dom.setContent(LAYER_QML, True) # xyz_id non editable
        vlayer.importNamedStyle(dom)

        QgsProject.instance().addMapLayer(vlayer)
        return vlayer
    def _init_ext_layer(self, geom_str, crs):
        """ given non map of feat, init a qgis layer
        :map_feat: {geom_string: list_of_feat}
        """
        ext=self.ext
        driver_name = ext.upper() # might not needed for 

        layer_name = self._layer_name(geom_str)
        
        fname = make_unique_full_path(ext=ext)
        
        vlayer = QgsVectorLayer(
            "{geom}?crs={crs}&index=yes".format(geom=geom_str,crs=crs), 
            layer_name,"memory") # this should be done in main thread

        # QgsVectorFileWriter.writeAsVectorFormat(vlayer, fname, "UTF-8", vlayer.sourceCrs(), driver_name)

        db_layer_name = "test" # vlayer.id()
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.fileEncoding = "UTF-8"
        options.driverName = driver_name
        options.ct = QgsCoordinateTransform(vlayer.sourceCrs(), vlayer.sourceCrs(), QgsProject.instance())
        options.layerName = db_layer_name
        QgsVectorFileWriter.writeAsVectorFormat(vlayer, fname, options)

        sql_constraint = f'"{parser.QGS_XYZ_ID}" TEXT UNIQUE ON CONFLICT REPLACE' # replace older duplicate
        sql_constraint = f'"{parser.QGS_XYZ_ID}" TEXT UNIQUE ON CONFLICT IGNORE' # discard newer duplicate
        self._init_constraint(fname, sql_constraint)

        uri = f"{fname}|layername={db_layer_name}"
        vlayer = QgsVectorLayer(uri, layer_name, "ogr")
        self._map_vlayer[geom_str] = vlayer
        self._save_meta(vlayer)

        self.map_fields[geom_str] = vlayer.fields()
        # QgsProject.instance().addMapLayer(vlayer)
        
        return vlayer

    def _init_constraint(self, fname, sql_constraint):
        # https://sqlite.org/lang_altertable.html

        # old_name = os.path.basename(fname).split(".")[0] # table name
        tmp_name = "XYZLayer"

        conn = sqlite3.connect(fname)
        cur = conn.cursor()

        sql = 'SELECT table_name, data_type, srs_id FROM "gpkg_contents"'
        cur.execute(sql)
        meta = cur.fetchall()[0]
        old_name = meta[0]

        sql = f'SELECT type, sql FROM sqlite_master WHERE tbl_name="{old_name}"'
        cur.execute(sql)
        lst = cur.fetchall()
        lst_old_sql = [p[1] for p in lst]
        # print(lst)

        sql_create = lst_old_sql.pop(0)
        sql_create = sql_create.replace(old_name, tmp_name)
        parts = sql_create.partition(")")
        sql_create = "".join([
            parts[0], 
            ", %s"%(sql_constraint), 
            parts[1], parts[2]
        ])
        # empty table, so insert is skipped
        lst_sql = [
            "PRAGMA foreign_keys = '0'",
            "BEGIN TRANSACTION",
            sql_create,
            "PRAGMA defer_foreign_keys = '1'",
            f'DROP TABLE "{old_name}"',
            f'ALTER TABLE "{tmp_name}" RENAME TO "{old_name}"',
            "PRAGMA defer_foreign_keys = '0'"
        ] + lst_old_sql + [
            # 'PRAGMA "main".foreign_key_check', # does not return anything -> unused
            "COMMIT",
            "PRAGMA foreign_keys = '1'"
        ]
        for s in lst_sql:
            cur.execute(s)

        conn.commit()
        conn.close()
        
""" Available vector format for QgsVectorFileWriter
[i.driverName for i in QgsVectorFileWriter.ogrDriverList()]
['GPKG', 'ESRI Shapefile', 'BNA',
'CSV', 'DGN', 'DXF', 'GML',
'GPX', 'GeoJSON', 'GeoRSS',
'Geoconcept', 'Interlis 1', 'Interlis 2',
'KML', 'MapInfo File', 'MapInfo MIF',
'ODS', 'S57', 'SQLite', 'SpatiaLite', 'XLSX']

[i.longName for i in QgsVectorFileWriter.ogrDriverList()]
['GeoPackage', 'ESRI Shapefile', 'Atlas BNA',
'Comma Separated Value [CSV]', 'Microstation DGN',
'AutoCAD DXF', 'Geography Markup Language [GML]',
'GPS eXchange Format [GPX]', 'GeoJSON', 'GeoRSS',
'Geoconcept', 'INTERLIS 1', 'INTERLIS 2',
'Keyhole Markup Language [KML]', 'Mapinfo TAB',
'Mapinfo MIF', 'Open Document Spreadsheet',
'S-57 Base file', 'SQLite', 'SpatiaLite',
'MS Office Open XML spreadsheet']
"""
