from qgis.PyQt.QtCore import pyqtSignal

# from ...xyz_qgis.controller import make_qt_args
from .ux import UXDecorator


class SettingUX(UXDecorator):

    signal_clear_cache = pyqtSignal()
    signal_clear_cookies = pyqtSignal()

    def __init__(self, *a):
        # these are like abstract variables
        self.btn_clear_cache = None
        self.btn_clear_cookies = None

    def config(self, *a):
        # super().config(*a)
        self.btn_clear_cache.clicked.connect(self.signal_clear_cache)
        self.btn_clear_cookies.clicked.connect(self.signal_clear_cookies)
