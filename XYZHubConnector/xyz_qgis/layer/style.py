# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################
from .parser import QGS_XYZ_ID

template_layer_qml="""
<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.4.4-Madeira" styleCategories="AllStyleCategories">
  <editable>
    <!-- <field name="{xyz_id}" editable="0"/> -->
    <field name="fid" editable="0"/>
  </editable>
  <constraints>
    <constraint constraints="3" field="{xyz_id}" notnull_strength="2" unique_strength="1" exp_strength="0"/>
  </constraints>
</qgis>
"""
LAYER_QML = template_layer_qml.format(xyz_id=QGS_XYZ_ID)
