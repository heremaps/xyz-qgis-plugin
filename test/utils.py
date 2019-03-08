# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.PyQt.QtCore import QEventLoop, QThreadPool
from qgis.testing import unittest, start_app

from XYZHubConnector.modules.controller import AsyncFun, WorkerFun
from XYZHubConnector.modules.common.error import pretty_print_error
from XYZHubConnector.modules.network import NetManager, net_handler

import time
import sys
import os

def get_env(scope, keys):
    """ usage: get_env(locals(), ["APP_ID", "APP_CODE"]) #globals()
    """
    scope.update([ (k, os.environ[k]) for k in keys] )
def env_to_dict(keys):
    return dict( (k, os.environ[k]) for k in keys)
    

# /tests/src/python/test_db_manager_gpkg.py
class BaseTestAsync(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = start_app()
    @classmethod
    def tearDownClass(cls):
        pass
        # cls.app.quit() # useless
        # stop_app() # NameError: name 'QGISAPP' is not defined
        # cls.app.exitQgis() # crash when run unittest (all module)
        # del cls.app 
    def setUp(self):
        if isinstance(super(), BaseTestAsync) and hasattr(super(), self._testMethodName):
            self.skipTest("duplicated test")
            
        # self.loop = self.app
        self.loop = QEventLoop()
        self._output = list()
        self._idx = 0
        self.flag_error = False
        self.startTime = time.time()
    def tearDown(self):
        self._stop_async() # useless ?
        self._log_debug("Test ended. ################### \n")
        self._log_info("%s: %.3fs" % (self.id(), time.time() - self.startTime))
        
    def _add_output(self, output):
        self._output.append(output)
    def output(self, idx=None):
        if idx is None:
            idx = self._idx
            self._idx += 1
        return self._output[idx] if idx < len(self._output) else None

    def _stop_async(self):
        self.loop.quit()
        self._log_debug("Stop Async. ################### \n")

    def _handle_error(self, e):
        pretty_print_error(e)
        self._stop_async()
        self.flag_error = True
        
    def _wait_async(self):
        t0=time.time()
        self.loop.exec_()

        self._log_info("%s: wait_async end: %.3fs" % (self.id(), time.time() - t0))
        self.assertFalse(self.flag_error, "error")
        
    def _make_async_fun(self, fun):
        return AsyncFun(fun)
        
    def _log_info(self, *a,**kw):
        print(*a, file = sys.stderr, **kw)
    def _log_debug(self, *a,**kw):
        log_debug(str(self.id()),*a, **kw)
    #unused        
    def assertPairEqual(self, *a):
        pairs = [a[i:i+2] for i in range(0,len(a),2)]
        return self.assertEqual( *zip(*pairs ))

class BaseTestWorkerAsync(BaseTestAsync):
    
    def setUp(self):
        super().setUp()
        self.pool = QThreadPool() # .globalInstance() will crash afterward
        
    def tearDown(self):
        self.pool.deleteLater()
        super().tearDown()
        
    def _stop_async(self):
        super()._stop_async()
        self.pool.waitForDone(1)
        self.pool.clear()
    def _wait_async(self):
        super()._wait_async()
        self.pool.clear()
    def _make_async_fun(self, fun):
        return WorkerFun( fun, self.pool) 

    # def _log_debug(self, *a,**kw):
    #     print("active thread count", self.pool.activeThreadCount())
    #     super()._log_debug(*a, **kw)
    

def log_debug(*a,**kw):
    # return
    # print(*a,**kw)
    s = " ".join(str(i)[:200] for i in a)
    print(s,**kw)


def add_test_fn_params(cls,fn_name,*a,**kw):
    """ Create new test function from function with params (similar to TestCase.subTest() ).
    Test function name: "test_" + new_fn_name + k1_v1_k2_v2. 

    Example:
        if fn_name = "_test_fun", kw=dict(a=2) 
        -> "test_fun_a_2
        if fn_name = "_do_fun", kw=dict(a=2) 
        -> "test_do_fun_a_2
        if fn_name = "do_fun", kw=dict(a=2) 
        -> "test_do_fun_a_2
    """
    def _fn(self):
        fun = getattr(self, fn_name)
        return fun(*a,**kw)
    s = "_".join("%s_%s"%(k,v) for k,v in kw.items())
    new_name = ("%s_%s"%(fn_name, s)).strip("_")
    if not new_name.startswith("test"):
        new_name = "test_" + new_name
    setattr(cls, new_name, _fn)
######################################
# io.py
#####################################

import os
import json
from XYZHubConnector import config
def use_local_tmp_dir():
    TMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp")
    os.makedirs(TMP_DIR,exist_ok=True)
    config.TMP_DIR = TMP_DIR

use_local_tmp_dir()
def make_abs_path(*a):
    path,_ = os.path.split(__file__)
    
    return os.path.abspath(os.path.join(path, *a))
class LoadInput(object):
    def __init__(self, file, fn_name):
        path, fname = os.path.split(file)
        self.folder = os.path.join(path, "input", fname, fn_name)
        os.makedirs(self.folder,exist_ok=True)
    def fullpath(self, fname):
        return os.path.join(self.folder, fname)
    def load(self, fname):
        infile = os.path.join(self.folder, fname)
        with open(infile,encoding="utf-8") as f:
            txt = f.read()
        return txt
    def save(self, fname, txt):
        outfile = os.path.join(self.folder, fname)
        with open(outfile,"w",encoding="utf-8") as f:
            f.write(txt)

def json_output( out):
    return json.loads(json.dumps(out))

class SaveOutput(object):
    def __init__(self, file, fn_name):
        path, fname = os.path.split(file)
        self.folder = os.path.join(path, "output", fname, fn_name)
        os.makedirs(self.folder,exist_ok=True)
    def save(self, fname, output):
        txt = json.dumps(output)

        outfile = os.path.join(self.folder, fname)
        with open(outfile,"w",encoding="utf-8") as f:
            f.write(txt)
        return txt
class CorrectOutput(object):
    def __init__(self, file, fn_name):
        path, fname = os.path.split(file)
        self.folder = os.path.join(path, "output", fname, fn_name)
        
    def load(self, fname):
        infile = os.path.join(self.folder, fname)
        with open(infile, encoding="utf-8") as f:
            txt = f.read()
        output = json.loads(txt)
        return output
