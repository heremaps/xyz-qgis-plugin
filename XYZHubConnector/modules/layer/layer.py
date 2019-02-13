# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
#
###############################################################################

from qgis.core import QgsVectorLayer, QgsProject, QgsFeatureRequest
from . import render
from . import parser

#init_shp_layer
from ...utils import make_unique_full_path 
from qgis.core import  QgsVectorFileWriter, QgsCoordinateReferenceSystem
from qgis.PyQt.QtCore import pyqtSignal, QObject

from ...models.space_model import parse_copyright

from ..common.signal import make_print_qgis
print_qgis = make_print_qgis("layer")

class XYZLayer(object):
    """ XYZ Layer is created in 2 scenarios:
    + loading a new layer from xyz
    + uploading a qgis layer to xyz, add conn_info, meta, vlayer
    """
    def __init__(self, conn_info, meta, ext="gpkg"):
        super().__init__()
        self.conn_info = conn_info
        self.meta = meta
        self.ext = ext

        self.map_vlayer = dict()
        self._map_vlayer = dict()
        self.map_fields = dict()


        crs = QgsCoordinateReferenceSystem('EPSG:4326').toWkt()
        for geom in ["MultiPoint","MultiLineString","MultiPolygon",None]:
            self._init_ext_layer(geom, crs)

    def _save_meta(self, vlayer, space_info):
        vlayer.setCustomProperty("xyz-hub", space_info)
        lic = space_info.get("license")
        cr = space_info.get("copyright")
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
    def _layer_name(self, meta, geom_str):
        return "{title} - {id} - {geom}".format(geom=geom_str,**meta)
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

        QgsProject.instance().addMapLayer(vlayer)
        return vlayer
    def _init_ext_layer(self, geom_str, crs):
        """ given non map of feat, init a qgis layer
        :map_feat: {geom_string: list_of_feat}
        """
        ext=self.ext
        driver_name = ext.upper() # might not needed for 
        meta = self.meta

        layer_name = self._layer_name(meta, geom_str)
        
        fname = make_unique_full_path(ext=ext)
        
        vlayer = QgsVectorLayer(
            "{geom}?crs={crs}&index=yes".format(geom=geom_str,crs=crs), 
            layer_name,"memory") # this should be done in main thread
        QgsVectorFileWriter.writeAsVectorFormat(vlayer, fname, "UTF-8", vlayer.sourceCrs(), driver_name)
    
        
        vlayer = QgsVectorLayer(fname, layer_name, "ogr")
        self._map_vlayer[geom_str] = vlayer
        self._save_meta(vlayer, meta)

        self.map_fields[geom_str] = vlayer.fields()
        # QgsProject.instance().addMapLayer(vlayer)
        
        return vlayer
#DEPRECATED
"""
    def init_mem_layer(self, txt, *a, **kw):
        # fname = make_unique_full_path(ext="json")
        # with open(fname,"w") as f:
        #     f.write(txt)
        meta = self.meta
        txt1,_ = parser.split_feature_collection_txt(txt)
        geom, crs, feat_cnt = render.geojson_to_meta_str(txt1)
        if feat_cnt == 0:
            return

        layer_name = self._layer_name(meta)
        vlayer = QgsVectorLayer("{geom}?crs={crs}&index=yes".format(geom=geom,crs=crs), layer_name,"memory") # this should be done in main thread
        self.map_vlayer = vlayer
        self._save_meta(meta)
        
        feat, fields = parser.xyz_json_to_feature(txt)
        pr = vlayer.dataProvider()
        pr.addAttributes( fields)
        pr.addFeatures( feat)
        vlayer.updateFields()
        vlayer.updateExtents()

        # print_qgis("pr.fields", pr.fields().count(), "names", pr.fields().names())
        # print_qgis("layer.fields", vlayer.fields().count(), "names", vlayer.fields().names())

        QgsProject.instance().addMapLayer(vlayer) # this should be done in main thread
        return vlayer
    # no longer conform
    def init_ext_layer(self, txt, *a, **kw):
        fname = make_unique_full_path(ext=self.ext)
        driver_name = self.ext.upper() # might not needed for 

        meta = self.meta
        txt1,_ = parser.split_feature_collection_txt(txt)
        geom, crs, feat_cnt = render.geojson_to_meta_str(txt1)
        if feat_cnt == 0:
            return

        layer_name = self._layer_name(meta)
        vlayer = QgsVectorLayer("{geom}?crs={crs}&index=yes".format(geom=geom,crs=crs), layer_name,"memory") # this should be done in main thread
        QgsVectorFileWriter.writeAsVectorFormat(vlayer, fname, "UTF-8", vlayer.sourceCrs(), driver_name)
        

        # vlayer = QgsVectorLayer(txt, "tmp", "ogr")
        # feat_cnt = vlayer.featureCount()
        # if feat_cnt == 0:
        #     return
        # print(fname)
        # # QgsVectorFileWriter.writeAsVectorFormat(vlayer, fname, "UTF-8", vlayer.sourceCrs(), "ESRI Shapefile")
        # QgsVectorFileWriter.writeAsVectorFormat(vlayer, fname, "UTF-8", vlayer.sourceCrs(), driver_name)
        # # avoid recode

        vlayer = QgsVectorLayer(fname, layer_name, "ogr")
        self.map_vlayer = vlayer
        self._save_meta(meta)

        fields = vlayer.fields()

        # vlayer, feat, fields = render.parse_feature(txt1, vlayer, fields)
        feat, fields = parser.xyz_json_to_feature(txt1, fields)

        # # for i,ft in enumerate(feat):
        # #     ft.setId(i)

        pr = vlayer.dataProvider()
        
        print_qgis([(f.name(),f.typeName(),f.type()) for f in pr.fields()])
        print_qgis([(f.name(),f.typeName(),f.type()) for f in vlayer.fields()])
        print_qgis([(f.name(),f.typeName(),f.type()) for f in fields])

        pr.addAttributes(fields)
        vlayer.updateFields()

        pr.addFeatures(feat)
        vlayer.updateExtents()

        print_qgis([(f.name(),f.typeName(),f.type()) for f in pr.fields()])
        print_qgis([(f.name(),f.typeName(),f.type()) for f in vlayer.fields()])
        print_qgis([(f.name(),f.typeName(),f.type()) for f in fields])

        QgsProject.instance().addMapLayer(vlayer)
        return vlayer
"""


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
