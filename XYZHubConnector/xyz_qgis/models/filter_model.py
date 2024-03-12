# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2020 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################


from .token_model import EditableItemModel


class FilterModel(EditableItemModel):
    INFO_KEYS = ["name", "operator", "values"]
    TOKEN_KEY = "name"

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        # UsedToken.__init__(self)
        self._refresh_model()

    def set_filters(self, filters):
        self.cfg = list(filters)

    def get_filters(self):
        return list(self.cfg)

    # functions for lineedit

    def get_display_str(self):
        return "&".join(
            "".join(d[k] for k in ["name", "operator", "values"]) for d in self.get_filters()
        )
