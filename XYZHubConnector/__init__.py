# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

__author__ = "Minh Nguyen"
__copyright__ = "Copyright 2019, HERE Europe B.V."

__license__ = "MIT"
__version__ = "1.6.2"
__maintainer__ = "Minh Nguyen"
__email__ = "huyminh.nguyen@here.com"
__status__ = "Development"

def classFactory(iface):
    """invoke plugin"""
    from .plugin import XYZHubConnector
    return XYZHubConnector(iface)
