from qgis.PyQt.QtCore import pyqtSignal

from ...modules.controller import make_qt_args
from ..util_dialog import ConfirmDialog


class UploadUX(object):
    title="XYZ Hub Connection"
    signal_upload_space = pyqtSignal(object)
    
    def __init__(self, *a):
        # these are like abstract variables
        self.btn_upload = None
        self.lineEdit_tags = None

        self.conn_info = None

        self._get_current_index = lambda *a: a
        self._get_space_model = lambda *a: a
        self.get_input_token = lambda *a: a

        raise NotImplementedError()
    def config(self, *a):
        # super().config(*a)
        self.vlayer = None
        self.btn_upload.clicked.connect(self.start_upload)
    def set_layer(self,vlayer):
        self.vlayer = vlayer
    def start_upload(self):
        index = self._get_current_index()
        meta = self._get_space_model().get_(dict, index)
        self.conn_info.set_(**meta, token=self.get_input_token())

        tags = self.lineEdit_tags.text().strip()
        kw = dict(tags=tags) if len(tags) else dict()

        dialog = ConfirmDialog("\n".join([
            "From Layer:\t%s",
            "To Space:\t%s",
            "Tags:\t\t%s",
            ]) % (self.vlayer.name(), meta["title"], tags),
            title="Confirm Upload"
        )
        ret = dialog.exec_()
        if ret != dialog.Ok: return

        self.signal_upload_space.emit(make_qt_args(self.conn_info, self.vlayer, **kw))
        self.close()
    def ui_enable_ok_button(self, flag):
        # super().ui_enable_ok_button(flag)
        flag = flag and self.vlayer is not None
        self.btn_upload.setEnabled(flag)
        self.btn_upload.clearFocus()
