# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


from qgis.PyQt.QtCore import pyqtSignal
from .util_dialog import ConfirmDialog
from ..modules.controller import make_qt_args

class TokenUX(object):
    signal_use_token = pyqtSignal(object)
    def __init__(self):
        # these are like abstract variables
        self.comboBox_token = None
        self.btn_use = None
        self.conn_info = None
        self.ui_valid_token = lambda *a: a
        self.ui_valid_input = lambda *a: a
        #
        self.used_token_idx = 0
    def config(self, token_model):
        self.used_token_idx = 0

        self.comboBox_token.setModel( token_model)
        self.comboBox_token.setInsertPolicy(self.comboBox_token.NoInsert)
        self.comboBox_token.setDuplicatesEnabled(False)

        self.comboBox_token.currentIndexChanged[int].connect(self.cb_comboxBox_token_selected)
        self.comboBox_token.currentIndexChanged[int].connect(self.ui_valid_input)
        self.comboBox_token.editTextChanged.connect(self.ui_valid_input)

        self.btn_use.clicked.connect(self.cb_token_used)
        self.btn_clear_token.clicked.connect(self.cb_clear_token)
        self.btn_clear_token.clicked.connect(self.ui_valid_input)

        self.comboBox_server.currentIndexChanged[str].connect(token_model.cb_set_server)
        self.comboBox_server.currentIndexChanged[str].connect(self.cb_set_server)
        self.comboBox_server.currentIndexChanged[str].connect(self.ui_valid_input)

        token_model.cb_set_server(self.comboBox_server.currentText())
        self.conn_info.set_server(self.comboBox_server.currentText())

        self.comboBox_token.setCurrentIndex(0)
        self.ui_valid_input() # valid_input initially (explicit)
    def cb_set_server(self,server):
        self.conn_info.set_server(server)
        self.used_token_idx = 0
    def cb_clear_token(self):
        dialog = ConfirmDialog(self, "Do you want to Remove token?")
        ret = dialog.exec_()
        if ret != dialog.Ok: return

        idx = self.comboBox_token.currentIndex()
        if idx > 0:
            self.comboBox_token.removeItem(idx)
        else:
            self.comboBox_token.clearEditText()

        if self.used_token_idx == idx:
            self._get_space_model().reset()
            self.used_token_idx = 0
            self.comboBox_token.setCurrentIndex(0)
            
    def get_input_token(self):
        return self.comboBox_token.currentText().strip()
        
    def insert_new_valid_token(self):

        ### find duplicate
        # print("current token index: %s"% self.comboBox_token.currentIndex())
        # if self.comboBox_token.currentIndex() > 0: return
        # https://github.com/radekp/qt/blob/master/src/gui/widgets/qcombobox.cpp#L1151
        
        token, space_id = self.conn_info.get_xyz_space()

        idx = self.comboBox_token.findText(token)
        if idx == -1: # no duplicate
            # idx=1; self.comboBox_token.insertItem(idx,token)
            self.comboBox_token.addItem(token)
            idx = self.comboBox_token.count() - 1
            # self.append_to_file( token)
        self.comboBox_token.setCurrentIndex(idx)
        
        # explicit + forced ui_valid_input (in case idx already = currentIndex)
        self.used_token_idx = self.comboBox_token.currentIndex()
        self.ui_valid_input() # valid_input initially
    def cb_enable_token_ui(self,flag=True):
        txt_clicked = "Checking.."
        txt0 = "Use"
        if not flag:
            self.btn_use.setText(txt_clicked)
        elif self.btn_use.text() == txt_clicked:
            self.btn_use.setText(txt0)
        self.btn_use.setEnabled(flag)
        self.comboBox_server.setEnabled(flag)
        self.comboBox_token.setEnabled(flag)
    def cb_token_used(self):
        token = self.get_input_token()
        if len(token) == 0: 
            return
        # disable button
        self.cb_enable_token_ui(False)
        # gui -> pending token
        self.used_token_idx = self.comboBox_token.currentIndex()
        self.conn_info.set_(token=token)
        self.signal_use_token.emit( make_qt_args(self.conn_info) )
        

    def cb_comboxBox_token_selected(self, index):
        flag_edit = True if index == 0 else False
        self.comboBox_token.setEditable(flag_edit)


    def ui_valid_token(self, *a):
        flag_token = len(self.get_input_token()) > 0
        self.btn_use.setEnabled(flag_token)

        flag = self.comboBox_token.currentIndex() > 0 and self.used_token_idx == self.comboBox_token.currentIndex()
        txt = "Ok!" if flag else "Use"
        self.btn_use.setText(txt)
        return flag