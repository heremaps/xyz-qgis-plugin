# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import sqlite3
import time
import json
import re
from typing import List

REGEX_LOADING_MODE = re.compile(r"\(\w+\)$")

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeatureRequest,
    QgsProject,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsCoordinateTransform,
    QgsWkbTypes,
    QgsFields,
)

from qgis.utils import iface
from qgis.PyQt.QtXml import QDomDocument

from . import parser
from .layer_props import QProps
from .layer_utils import (
    get_feat_cnt_from_src,
    get_customProperty_str,
    load_json_default,
    is_xyz_supported_layer,
)
from ..models import SpaceConnectionInfo, parse_copyright
from ..common import config
from ..common.utils import make_unique_full_path, make_fixed_full_path
from .style import LAYER_QML

from ..common.signal import make_print_qgis

print_qgis = make_print_qgis("layer")


class XYZLayer(object):
    """XYZ Layer is created in 2 scenarios:
    + loading a new layer from xyz
    + uploading a qgis layer to xyz, add conn_info, meta, vlayer
    """

    NO_GEOM = "No geometry"
    GEOM_ORDER = dict(
        (k, i) for i, k in enumerate(["Point", "Line", "Polygon", "Unknown geometry", NO_GEOM])
    )
    # https://qgis.org/api/qgswkbtypes_8cpp_source.html#l00129

    def __init__(
        self,
        conn_info,
        meta,
        tags="",
        unique: str = None,
        loader_params: dict = None,
        group_name="XYZ Layer",
        ext="gpkg",
    ):
        super().__init__()
        self.ext = ext
        self.conn_info = conn_info
        self.meta = meta
        self.tags = tags
        self.unique = str(unique or int(time.time() * 10))
        self.loader_params = loader_params or dict()

        self._base_group_name = group_name
        self._group_name = group_name

        self.map_vlayer = dict()
        self.map_fields = dict()
        self.qgroups = dict()
        self.callbacks = dict()

    ##############
    # qgis custom property

    @classmethod
    def load_from_qnode(cls, qnode):
        meta = get_customProperty_str(qnode, QProps.LAYER_META)
        conn_info = get_customProperty_str(qnode, QProps.CONN_INFO)
        tags = get_customProperty_str(qnode, QProps.TAGS)
        unique = get_customProperty_str(qnode, QProps.UNIQUE_ID)
        loader_params = get_customProperty_str(qnode, QProps.LOADER_PARAMS)
        meta = load_json_default(meta, default=dict())
        conn_info = load_json_default(conn_info, default=dict())
        conn_info = SpaceConnectionInfo.from_dict(conn_info)
        loader_params = load_json_default(loader_params, default=dict())

        name = qnode.name()
        obj = cls(
            conn_info, meta, tags=tags, unique=unique, loader_params=loader_params, group_name=name
        )
        obj.qgroups["main"] = qnode
        obj._update_group_name(qnode)

        # obj._save_meta_node(qnode)

        for q in qnode.findLayers():
            vlayer = q.layer()
            if not (
                isinstance(vlayer, QgsVectorLayer)
                and vlayer.dataProvider().name() != "virtual"
                and is_xyz_supported_layer(vlayer)
            ):
                continue

            if not vlayer.isValid():
                obj._fix_invalid_vlayer(vlayer)

            # assign vlayer, fields into map according to geom_str and idx
            geom_str, idx = obj.geom_str_idx_from_vlayer(vlayer)

            lst_vlayer = obj.map_vlayer.setdefault(geom_str, list())
            lst_fields = obj.map_fields.setdefault(geom_str, list())
            while len(lst_vlayer) < idx + 1:
                lst_vlayer.append(None)
                lst_fields.append(parser.new_fields_gpkg())

            # favor vlayer uri without subset (|subset=)
            if lst_vlayer[idx] is None or not obj._has_uri_subset(vlayer):
                lst_vlayer[idx] = vlayer
                lst_fields[idx] = vlayer.dataProvider().fields()

            obj.update_constraint_trigger(geom_str, idx)
            vlayer_geom_str = QgsWkbTypes.displayString(vlayer.wkbType())
            if vlayer_geom_str and not vlayer_geom_str.endswith("Z"):
                obj.update_z_geom(geom_str, idx, vlayer)
            vlayer.reload()
        return obj

    def _fix_invalid_vlayer(self, vlayer):
        geom_str, idx = self.geom_str_idx_from_vlayer(vlayer)
        crs = QgsCoordinateReferenceSystem("EPSG:4326").toWkt()
        vlayer_new = self._init_ext_layer(geom_str, idx, crs)

        vlayer.setDataSource(
            vlayer.source().replace(
                self._base_uri_from_vlayer(vlayer), self._base_uri_from_vlayer(vlayer_new)
            ),
            vlayer.name(),
            vlayer.providerType(),
        )

    def _save_params_to_node(self, qnode):
        qnode.setCustomProperty(
            QProps.LOADER_PARAMS, json.dumps(self.get_loader_params(), ensure_ascii=False)
        )
        qnode.setCustomProperty(QProps.TAGS, self.tags)
        qnode.setCustomProperty(QProps.PLUGIN_VERSION, config.PLUGIN_VERSION)

    def _save_meta_node(self, qnode):
        qnode.setCustomProperty(QProps.LAYER_META, json.dumps(self.meta, ensure_ascii=False))
        qnode.setCustomProperty(
            QProps.CONN_INFO, json.dumps(self.conn_info.to_project_dict(), ensure_ascii=False)
        )
        qnode.setCustomProperty(QProps.UNIQUE_ID, self.get_id())
        self._save_params_to_node(qnode)

    def _save_meta_vlayer(self, vlayer):
        self._save_meta_node(vlayer)

        lic = self.meta.get("license")
        cr = self.meta.get("copyright")

        meta = vlayer.metadata()
        if lic is not None:
            meta.setLicenses([lic])
        if isinstance(cr, list):
            lst_txt = parse_copyright(cr)
            meta.setRights(lst_txt)
        vlayer.setMetadata(meta)

    def _refresh_meta_vlayer(self, vlayer: QgsVectorLayer, style_category=None):
        if style_category not in (vlayer.CustomProperties, vlayer.AllStyleCategories, None):
            return
        self._save_meta_vlayer(vlayer)

    def update_conn_info(self, conn_info: SpaceConnectionInfo = None):
        if not conn_info:
            return
        self.conn_info = conn_info
        qnode = self.qgroups["main"]
        self._save_meta_node(qnode)
        for vlayer in self.iter_layer():
            self._save_meta_vlayer(vlayer)

    # unused
    def _propagate_meta_vlayer(self, vlayer: QgsVectorLayer, style_category=None):
        if style_category not in (vlayer.CustomProperties, vlayer.AllStyleCategories, None):
            return
        qnode = self.qgroups.get("main")
        if not qnode:
            return
        for k in qnode.customProperties():
            v = get_customProperty_str(qnode, k)
            vlayer.setCustomProperty(k, v)

    ##############

    def config_callback(self, **callbacks):
        self.callbacks = callbacks

        qnode = self.qgroups.get("main")
        if not qnode:
            return

        for geom_str, lst_vlayer in self.map_vlayer.items():
            for idx, vlayer in enumerate(lst_vlayer):
                self._connect_cb_vlayer(vlayer, geom_str, idx)

    def _cb_delete_vlayer(self, vlayer, geom_str, idx):
        self._remove_layer(geom_str, idx)
        try:
            self._disconnect_cb_vlayer(vlayer)  # deleted anyway
        except RuntimeError:
            pass

    def destroy(self):
        self.qgroups.pop("main", None)

        # Delete vlayer in case a it is moved out of the group
        # thus will not be implicitly deleted
        for geom_str, lst_vlayer in self.map_vlayer.items():
            for idx, vlayer in enumerate(lst_vlayer):
                if vlayer is None:
                    continue
                self._cb_delete_vlayer(vlayer, geom_str, idx)

    def _make_cb_args(self, fn, *args):
        def cb(*a):
            fn(*(args + a))

        return cb

    def _connect_cb_vlayer(self, vlayer, geom_str, idx):
        if vlayer is None:
            return
        cb_delete_vlayer = self.callbacks.setdefault(
            vlayer.id(), self._make_cb_args(self._cb_delete_vlayer, vlayer, geom_str, idx)
        )
        vlayer.willBeDeleted.connect(cb_delete_vlayer)

        for signal, name in zip(
            [vlayer.beforeEditingStarted, vlayer.willBeDeleted], ["start_editing", "stop_loading"]
        ):
            if name not in self.callbacks:
                continue
            signal.connect(self.callbacks[name])
        # vlayer.editingStopped.connect(self.callbacks["end_editing"])

        cb_style_loaded = self.callbacks.setdefault("style_loaded", dict()).setdefault(
            vlayer.id(), self._make_cb_args(self._refresh_meta_vlayer, vlayer)
        )
        vlayer.styleLoaded.connect(cb_style_loaded)

    def _disconnect_cb_vlayer(self, vlayer):
        cb_delete_vlayer = self.callbacks.pop(vlayer.id(), None)
        if cb_delete_vlayer:
            vlayer.willBeDeleted.disconnect(cb_delete_vlayer)

        for signal, name in zip(
            [vlayer.beforeEditingStarted, vlayer.willBeDeleted], ["start_editing", "stop_loading"]
        ):
            if name not in self.callbacks:
                continue
            signal.disconnect(self.callbacks[name])
        # vlayer.editingStopped.disconnect(self.callbacks["end_editing"])

        cb_style_loaded = self.callbacks.get("style_loaded", dict()).pop(vlayer.id(), None)
        if cb_style_loaded:
            vlayer.styleLoaded.disconnect(cb_style_loaded)

    def iter_layer(self):
        for lst in self.map_vlayer.values():
            for vlayer in lst:
                if not vlayer:
                    continue
                yield vlayer

    def has_layer(self, geom_str, idx):
        """Check if there is already a vlayer with given geometry and index
        (corresponding to that of map_fields)
        """
        return (
            geom_str in self.map_vlayer
            and idx < len(self.map_vlayer[geom_str])
            and bool(self.map_vlayer[geom_str][idx])
        )

    def get_loader_params(self) -> dict:
        return dict(self.loader_params) or dict()

    def get_layer(self, geom_str, idx):
        return self.map_vlayer[geom_str][idx]

    def get_name(self):
        return self._group_name

    def _make_group_name(self, idx=None):
        """
        returns main layer group name
        """
        tags = "-(%s)" % (self.tags) if len(self.tags) else ""
        temp = "{title}-{id}{tags}" if idx is None else "{title}-{id}{tags}-{idx}"
        name = temp.format(
            id=self.meta.get("id", ""),
            title=self.meta.get("title", ""),
            tags=tags,
            idx=idx,
        )
        return name

    def _group_geom_name(self, geom_str):
        geom = (
            QgsWkbTypes.geometryDisplayString(
                QgsWkbTypes.geometryType(QgsWkbTypes.parseType(geom_str))
            )
            if geom_str
            else self.NO_GEOM
        )
        return geom

    def _layer_name(self, geom_str, idx):
        """
        returns vlayer name shown in qgis
        """
        name = "{group_name}-{geom}-{idx}".format(
            group_name=self._base_group_name,
            geom=geom_str,
            idx=idx,
        )
        return name

    def _db_layer_name(self, geom_str, idx):
        """
        returns name of the table corresponds to vlayer in gpkg/sqlite db
        """
        return "{geom}_{idx}".format(geom=geom_str, idx=idx)

    def _parse_db_layer_name(self, db_layer_name):
        """
        returns geom_str, idx from table name in gpkg/sqlite db
        """
        geom_str, idx = db_layer_name.split("_", 1)
        return geom_str, int(idx)

    def geom_str_idx_from_vlayer(self, vlayer):
        """
        returns geom_str, idx from vlayer
        """
        uri = vlayer.source()
        uri_parts = uri.split("|")
        db_layer_name = ""
        key = "layername="
        for p in uri_parts:
            if key in p:
                db_layer_name = p.replace(key, "")
                break
        if not db_layer_name:
            return QgsWkbTypes.displayString(QgsWkbTypes.NoGeometry), 0
        return self._parse_db_layer_name(db_layer_name)

    def _base_uri_from_vlayer(self, vlayer):
        uri = vlayer.source()
        return uri.split("|")[0]

    def _has_uri_subset(self, vlayer):
        uri = vlayer.source()
        for p in uri.split("|"):
            # c:\file.gpg|layername=Linestring_0|subset=
            if "subset=" in p:
                return True
        return False

    def _layer_fname(self):
        """
        returns file name of the sqlite db corresponds to xyz layer
        """
        tags = self.tags.replace(",", "_") if len(self.tags) else ""
        return "{id}_{tags}_{unique}".format(
            id=self.meta.get("id", ""),
            tags=tags,
            unique=self.unique,
        )

    def get_id(self):
        return self.unique

    def get_map_fields(self):
        """returns reference to existing mutable map_fields"""
        return self.map_fields

    def get_conn_info(self):
        return self.conn_info

    def get_feat_cnt(self):
        cnt = 0
        for vlayer in self.iter_layer():
            cnt += get_feat_cnt_from_src(vlayer)
        return cnt

    def update_loader_params(self, **loader_params):
        self.loader_params.update(loader_params)
        qnode = self.qgroups["main"]
        self._update_group_name(qnode)
        self._save_meta_node(qnode)

        # # update name of vlayer might break things
        # for idx, vlayer in enumerate(i.layer()
        #     for g in qnode.findGroups()
        #     for i in g.findLayers()
        #     ):
        #     geom_str = QgsWkbTypes.displayString(vlayer.wkbType())
        #     self._update_vlayer_name(vlayer, geom_str, idx)

    def _update_unique_group_name(self, group):
        name = self._make_unique_group_name()
        name = self._detailed_group_name(name)
        self._group_name = name
        group.setName(name)

    def _get_base_group_name(self, name):
        match = REGEX_LOADING_MODE.search(name)
        if match:
            name = name[: match.start()]
        return name.strip()

    def _update_group_name(self, group):
        name = group.name()
        name = self._get_base_group_name(name)
        self._base_group_name = name
        name = self._detailed_group_name(name)
        self._group_name = name
        group.setName(name)

    def _update_vlayer_name(self, vlayer, geom_str, idx):
        vlayer.setName(self._layer_name(geom_str, idx))

    def _detailed_group_name(self, name):
        loading_mode: str = self.loader_params.get("loading_mode")
        if loading_mode:
            name = "%s (%s)" % (name, loading_mode)
        return name

    def _make_unique_group_name(self):
        tree_root = QgsProject.instance().layerTreeRoot()
        name = self._make_group_name()
        all_names = sorted(self._get_base_group_name(g.name()) for g in tree_root.findGroups())
        dupe_names = [x for x in all_names if x.startswith(name)]
        idx = 0
        while name in dupe_names:
            idx += 1
            name = self._make_group_name(idx)
        self._base_group_name = name
        return name

    def add_empty_group(self):
        tree_root = QgsProject.instance().layerTreeRoot()
        group = self.qgroups.get("main")
        if not group:
            name = self._make_unique_group_name()
            name = self._detailed_group_name(name)
            self._group_name = name
            group = tree_root.insertGroup(0, name)
            self.qgroups["main"] = group
            self._save_meta_node(group)
        return group

    def _get_geom_order(self, geom: str, lst_geom: List[str]):
        """Get order of new geometry group name `geom`
        in existing list of geometry group names `lst_geom` for insertion
        """
        if geom not in self.GEOM_ORDER:
            return len(lst_geom)
        lst_geom = list(lst_geom) + [geom]
        lst_geom.sort(key=lambda g: self.GEOM_ORDER.get(g, len(self.GEOM_ORDER)))
        return lst_geom.index(geom)

    def add_ext_layer(self, geom_str, idx):
        """Add layer group structure
        qgroups: dict["main"] = group
            dict[geom] = list([vlayer1, vlayer2,...])
        map_vlayer: dict[geom_str] = list([vlayer1, vlayer2,...])
            vlayer order in list shall always be fixed, deleted vlayer hall be set to None
        map_fields: dict[geom_str] = list([fields1, fields2,...])
            fields order in list shall always be fixed and not be deleted
        geom_str: QgsWkbTypes.displayString (detailed geometry, e.g. Multi-)
        geom: QgsWkbTypes.geometryDisplayString (generic geometry,)
        """
        group = self.add_empty_group()

        geom = self._group_geom_name(geom_str)
        lst_geom = [g.name() for g in group.findGroups()]
        if geom in lst_geom:
            group_geom = group.findGroup(geom)
        else:
            order = self._get_geom_order(geom, lst_geom)
            group_geom = group.insertGroup(
                order, geom
            )  # if order < len(lst_geom) else group.addGroup(geom)

        crs = QgsCoordinateReferenceSystem("EPSG:4326").toWkt()

        vlayer = self._init_ext_layer(geom_str, idx, crs)
        self._add_layer(geom_str, vlayer, idx)
        self._connect_cb_vlayer(vlayer, geom_str, idx)

        dom = QDomDocument()
        dom.setContent(LAYER_QML, True)  # xyz_id non editable
        vlayer.importNamedStyle(dom)
        QgsProject.instance().addMapLayer(vlayer, False)

        group_geom.addLayer(vlayer)

        if iface:
            iface.setActiveLayer(vlayer)
        return vlayer

    def _add_layer(self, geom_str, vlayer, idx):
        """Add vlayer to correct position (geometry and index) in the internal map"""
        lst = self.map_vlayer.setdefault(geom_str, list())
        # assert idx == len(lst), "vlayer count mismatch"
        if idx == len(lst):
            lst.append(vlayer)
        else:
            lst[idx] = vlayer

    def _remove_layer(self, geom_str, idx):
        """Remove vlayer from the internal map without messing the index"""
        self.map_vlayer[geom_str][idx] = None
        self.map_fields[geom_str][idx] = parser.new_fields_gpkg()

    def refresh_map_fields(self):
        for geom_str in self.map_vlayer:
            for idx, vlayer in enumerate(self.map_vlayer.get(geom_str, list())):
                if vlayer is None:
                    continue
                self.map_fields[geom_str][idx] = vlayer.dataProvider().fields()

    def _init_ext_layer(self, geom_str, idx, crs):
        """given non map of feat, init a qgis layer
        :map_feat: {geom_string: list_of_feat}
        """
        ext = self.ext
        driver_name = ext.upper()  # might not needed for

        layer_name = self._layer_name(geom_str, idx)

        # sqlite max connection 64
        # if xyz space -> more than 64 vlayer,
        # then create new fname

        # fname = make_unique_full_path(ext=ext)
        fname = make_fixed_full_path(self._layer_fname(), ext=ext)
        if geom_str:
            geomz = geom_str if geom_str.endswith("Z") else "{}Z".format(geom_str)
        else:
            geomz = "NoGeometry"
        vlayer = QgsVectorLayer(
            "{geom}?crs={crs}&index=yes".format(geom=geomz, crs=crs), layer_name, "memory"
        )  # this should be done in main thread

        # QgsVectorFileWriter.writeAsVectorFormat(vlayer, fname, "UTF-8", vlayer.sourceCrs(),
        # driver_name)

        db_layer_name = self._db_layer_name(geom_str, idx)

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.fileEncoding = "UTF-8"
        options.driverName = driver_name
        options.ct = QgsCoordinateTransform(
            vlayer.sourceCrs(), vlayer.sourceCrs(), QgsProject.instance()
        )
        options.layerName = db_layer_name
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer  # update mode
        if hasattr(QgsVectorFileWriter, "writeAsVectorFormatV2"):
            err = QgsVectorFileWriter.writeAsVectorFormatV2(
                vlayer, fname, vlayer.transformContext(), options
            )
        else:
            err = QgsVectorFileWriter.writeAsVectorFormat(vlayer, fname, options)
        if err[0] == QgsVectorFileWriter.ErrCreateDataSource:
            options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
            if hasattr(QgsVectorFileWriter, "writeAsVectorFormatV2"):
                err = QgsVectorFileWriter.writeAsVectorFormatV2(
                    vlayer, fname, vlayer.transformContext(), options
                )
            else:
                err = QgsVectorFileWriter.writeAsVectorFormat(vlayer, fname, options)
        if err[0] != QgsVectorFileWriter.NoError:
            raise Exception("%s: %s" % err)

        self._update_constraint_trigger(fname, db_layer_name)

        uri = "%s|layername=%s" % (fname, db_layer_name)
        vlayer = QgsVectorLayer(uri, layer_name, "ogr")
        self._save_meta_vlayer(vlayer)

        return vlayer

    def update_constraint_trigger(self, geom_str, idx):
        fname = make_fixed_full_path(self._layer_fname(), ext=self.ext)
        db_layer_name = self._db_layer_name(geom_str, idx)
        self._update_constraint_trigger(fname, db_layer_name)

    def _update_constraint_trigger(self, fname, layer_name):
        sql_trigger = """
        CREATE TRIGGER IF NOT EXISTS "trigger_{layer_name}_{id_column}_insert"
        BEFORE INSERT ON "{layer_name}" BEGIN DELETE FROM "{layer_name}"
        WHERE "{id_column}" = NEW."{id_column}"; END;

        CREATE UNIQUE INDEX IF NOT EXISTS "idx_{layer_name}_{id_column}"
        ON "{layer_name}" ("{id_column}");
        VACUUM;
        """.format(
            layer_name=layer_name, id_column=parser.QGS_XYZ_ID
        )
        conn = sqlite3.connect(fname)
        cur = conn.cursor()
        cur.executescript(sql_trigger)
        conn.commit()
        conn.close()

    def update_z_geom(self, geom_str, idx, vlayer):
        db_layer_name = self._db_layer_name(geom_str, idx)
        fname = make_fixed_full_path(self._layer_fname(), ext=self.ext)
        sql = """
        UPDATE "gpkg_geometry_columns" SET "z"=1 WHERE "table_name" = "{layer_name}";
        """.format(
            layer_name=db_layer_name
        )
        conn = sqlite3.connect(fname)
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        conn.close()
        # set to the same data source to apply changes
        vlayer.setDataSource(vlayer.source(), vlayer.sourceName(), "ogr")


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
