# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


from qgis.PyQt.QtWidgets import QMessageBox
class ConfirmDialog(QMessageBox):
    def __init__(self, msg, title="Confirm"):
        super().__init__(QMessageBox.NoIcon, title, msg, QMessageBox.Ok | QMessageBox.Cancel)
        

def exec_warning_dialog(title, msg, body=None):
    box = QMessageBox(QMessageBox.Warning, title, msg, QMessageBox.Close)
    if not body is None:
        box.setDetailedText(body)

    return box.exec_()
