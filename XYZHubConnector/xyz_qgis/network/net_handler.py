# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from qgis.PyQt.QtCore import QByteArray
from qgis.PyQt.QtNetwork import QNetworkRequest, QNetworkReply

from qgis.core import Qgis, QgsMessageLog  # to be removed
from .net_utils import decode_byte, get_qt_property
from ..controller import make_qt_args
from ..common import config
from ..models.connection import mask_token, SpaceConnectionInfo

from ..common.signal import make_print_qgis

print_qgis = make_print_qgis("net_handler")


# reply handler
class NetworkResponse:
    def __init__(self, reply: QNetworkReply):
        self.reply = reply
        self.body_qbytearray = None
        self.body_bytes: bytes = None
        self.body_txt: str = None
        self.body_json: dict = None
        self._is_body_read = False

    def is_dummy(self):
        return not isinstance(self.reply, QNetworkReply)

    def _read_body(self):
        if not self._is_body_read:
            self.body_qbytearray = self.reply.readAll()
            self.body_bytes, self.body_txt, self.body_json = decode_byte(self.body_qbytearray)
            self._is_body_read = True

    def get_body_qbytearray(self):
        self._read_body()
        return self.body_qbytearray

    def get_body_txt(self):
        self._read_body()
        return self.body_txt

    def get_body_json(self):
        self._read_body()
        return self.body_json

    def get_body_bytes(self):
        self._read_body()
        return self.body_bytes

    def get_reply(self):
        return self.reply

    def get_status(self):
        return self.reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)

    def get_reason(self):
        return self.reply.attribute(QNetworkRequest.HttpReasonPhraseAttribute)

    def get_error(self):
        return self.reply.error()

    def get_error_string(self):
        return self.reply.errorString()

    def get_url(self):
        return self.reply.request().url().toString()

    def get_qt_property(self, keys):
        return get_qt_property(self.reply, keys)

    def get_conn_info(self) -> SpaceConnectionInfo:
        (conn_info,) = self.get_qt_property(["conn_info"])
        return conn_info

    def get_reply_tag(self) -> str:
        (reply_tag,) = self.get_qt_property(["reply_tag"])
        return reply_tag

    def get_payload(self):
        (req_payload,) = self.get_qt_property(["req_payload"])
        return req_payload

    def log_status(self):
        conn_info, reply_tag = self.get_qt_property(["conn_info", "reply_tag"])
        token, space_id = conn_info.get_xyz_space() if conn_info is not None else (None, None)

        if self.is_dummy():
            msg = "%s: %s - %s" % (
                reply_tag,
                mask_token(token),
                space_id,
            )
            QgsMessageLog.logMessage("Network dummy : %s" % msg, config.TAG_PLUGIN, Qgis.Success)
            return

        url = self.get_url()
        err = self.get_error()
        err_str = self.get_error_string()
        status = self.get_status()
        reason = self.get_reason()
        if err > 0 or not status:
            msg = "%s: %s: %s. %s. %s - %s. request: %s" % (
                reply_tag,
                status,
                reason,
                err_str,
                mask_token(token),
                space_id,
                url,
            )
            QgsMessageLog.logMessage("Network Error! : %s" % msg, config.TAG_PLUGIN, Qgis.Warning)
        else:
            msg = "%s: %s: %s. %s - %s. request: %s" % (
                reply_tag,
                status,
                reason,
                mask_token(token),
                space_id,
                url,
            )
            QgsMessageLog.logMessage("Network Ok! : %s" % msg, config.TAG_PLUGIN, Qgis.Success)

    def __del__(self):
        self.reply.deleteLater()


def on_received(reply):
    return NetworkHandler.on_received(reply)
    # return iml_on_received(reply)


# def iml_on_received(reply):
#     from ..iml.network.net_handler import IMLNetworkHandler
#     return IMLNetworkHandler.on_received(reply)


class NetworkHandler:
    @classmethod
    def handle_error(cls, response: NetworkResponse):
        err = response.get_error()
        status = response.get_status()

        if err == response.get_reply().OperationCanceledError:  # operation canceled
            raise NetworkTimeout(response)
        elif err > 0 or not status:
            raise NetworkError(response)

    @classmethod
    def on_received(cls, reply):
        response = NetworkResponse(reply)
        # print(response.get_reply().request().rawHeader("Cookie".encode("utf-8")))

        response.log_status()
        if not response.is_dummy():
            cls.handle_error(response)
        return cls.on_received_impl(response)

    @classmethod
    def on_received_impl(cls, response: NetworkResponse):
        print_qgis("Receiving")
        if response.is_dummy():
            raw = QByteArray()
            txt = ""
            obj = {}
        else:
            raw = response.get_body_qbytearray()
            txt = response.get_body_txt()
            obj = response.get_body_json()
        conn_info, reply_tag = response.get_qt_property(["conn_info", "reply_tag"])
        token, space_id = conn_info.get_xyz_space() if conn_info is not None else (None, None)
        limit, handle, meta = response.get_qt_property(["limit", "handle", "meta"])
        tile_schema, tile_id = response.get_qt_property(["tile_schema", "tile_id"])

        args = list()
        kw = dict()

        if reply_tag == "spaces":
            print_qgis(txt)
            args = [conn_info, obj]
        elif reply_tag in ("tile", "bbox", "iterate", "search"):
            print_qgis(txt[:100])
            print_qgis(txt[-10:])

            print_qgis(
                "feature count:%s" % len(obj["features"])
                if "features" in obj
                else "no features key"
            )
            print_qgis(obj.keys())

            args = [obj]
            if reply_tag == "tile":
                kw = dict(limit=limit, tile_schema=tile_schema, tile_id=tile_id)
            else:
                kw = dict(handle=handle, limit=limit)

        elif reply_tag in ("init_layer",):
            print_qgis(txt[:100])
            print_qgis(txt[-10:])
            args = [txt, raw]
        elif reply_tag in ("add_feat", "del_feat", "sync_feat"):
            # TODO: error handling, rollback layer, but already commited  !?!
            if len(txt):
                print_qgis("updated features")
            else:
                print_qgis("added/removed features")
            print_qgis(txt[:100])

            args = [obj]
        elif reply_tag in ("add_space", "edit_space", "del_space"):

            args = [conn_info, obj]
        elif reply_tag in ("statistics", "count", "space_meta"):
            print_qgis(txt[:100])
            args = [conn_info, obj]
        else:
            print_qgis(reply_tag)
            print_qgis(txt[:100])
        # response.get_reply().deleteLater() #
        # return make_qt_args(reply_tag, *args, **kw)
        return make_qt_args(*args, **kw)


# Exception


class NetworkError(Exception):
    _status_msg_format = "{status}: {reason}"

    def __init__(self, response: NetworkResponse):
        super().__init__(response)
        self.response = response

    def get_response(self):
        return self.response

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        response = self.get_response()
        status = response.get_status()
        reason = response.get_reason()
        err = response.get_error()
        err_str = response.get_error_string()
        reply_tag = response.get_reply_tag()
        kw = dict(status=status, reason=reason) if status else dict(status=err, reason=err_str)
        status_msg = self._status_msg_format.format(**kw)
        return '{classname}("{reply_tag}", "{status_msg}", "{url}")'.format(
            classname=self.__class__.__name__,
            reply_tag=reply_tag,
            status_msg=status_msg,
            url=response.get_url(),
        )


class NetworkTimeout(NetworkError):
    _status_msg_format = "Timeout"


class NetworkUnauthorized(NetworkError):
    pass
