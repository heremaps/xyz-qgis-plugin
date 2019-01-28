# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
#
###############################################################################

import traceback

#unused
class ExceptionContainer(Exception):
    pass
    
def parse_exception_obj(obj):
    return obj
def make_exception_obj(e):
    # sys.exc_info()
    # type, exception, traceback
    # alternatively get e.__traceback__
    return e
    # return ExceptionContainer(e, sys.exc_info())
def _print_traceback(e):
    exc_info = (type(e), e, e.__traceback__)
    traceback.print_exception(*exc_info)
def _format_traceback(e):
    exc_info = (type(e), e, e.__traceback__)
    return traceback.format_exception(*exc_info)
def format_traceback(e):
    lst = list()
    while isinstance(e, Exception):
        lst.extend(_format_traceback(e))
        e = e.args[0] if len(e.args) > 0 else None
    return "\n".join(lst)
def pretty_print_error(e):
    while isinstance(e, Exception):
        _print_traceback(e)
        e = e.args[0] if len(e.args) > 0 else None